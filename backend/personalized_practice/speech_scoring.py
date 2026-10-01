import asyncio
import io
import os
import re
import statistics
import wave
from typing import Any, Mapping

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from asgiref.sync import async_to_sync
from django.core import signing

from personalized_practice.bank import load_age_bank
from personalized_practice.domain import PracticeDataError


class SpeechScoringError(ValueError):
    pass


class SpeechServiceUnavailable(SpeechScoringError):
    pass


TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
RESULT_TOKEN_SALT = "personalized-practice.assessment-speech-result"
RESULT_TOKEN_MAX_AGE_SECONDS = 3600
SAMPLE_RATE_HZ = 16000
SAMPLE_WIDTH_BYTES = 2
STREAM_CHUNK_MS = 100


def _words(text: str) -> list[str]:
    normalized = text.replace("’", "'").casefold()
    return [token for token in TOKEN_RE.findall(normalized)]


def _word_items(transcription: Mapping[str, Any]) -> list[tuple[str, float | None]]:
    try:
        items = transcription["results"]["items"]
    except (KeyError, TypeError) as exc:
        raise SpeechScoringError("Transcribe returned an invalid transcript.") from exc
    if not isinstance(items, list):
        raise SpeechScoringError("Transcribe returned an invalid word list.")
    output = []
    for item in items:
        if not isinstance(item, Mapping) or item.get("type") != "pronunciation":
            continue
        alternatives = item.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives or not isinstance(alternatives[0], Mapping):
            continue
        content = alternatives[0].get("content")
        if not isinstance(content, str):
            continue
        raw_confidence = alternatives[0].get("confidence")
        try:
            confidence = float(raw_confidence) if raw_confidence is not None else None
        except (TypeError, ValueError):
            confidence = None
        for word in _words(content):
            output.append((word, confidence))
    return output


def _align(
    reference: list[str], recognized: list[tuple[str, float | None]]
) -> tuple[dict[str, Any], dict[int, tuple[int, bool]]]:
    actual = [word for word, _ in recognized]
    rows = len(reference) + 1
    columns = len(actual) + 1
    costs = [[0] * columns for _ in range(rows)]
    for row in range(rows):
        costs[row][0] = row
    for column in range(columns):
        costs[0][column] = column
    for row in range(1, rows):
        for column in range(1, columns):
            substitution = costs[row - 1][column - 1] + (reference[row - 1] != actual[column - 1])
            deletion = costs[row - 1][column] + 1
            insertion = costs[row][column - 1] + 1
            costs[row][column] = min(substitution, deletion, insertion)

    matched: dict[int, tuple[int, bool]] = {}
    row, column = len(reference), len(actual)
    while row or column:
        if row and column:
            substitution_cost = costs[row - 1][column - 1] + (reference[row - 1] != actual[column - 1])
            if costs[row][column] == substitution_cost:
                matched[row - 1] = (column - 1, reference[row - 1] == actual[column - 1])
                row -= 1
                column -= 1
                continue
        if row and costs[row][column] == costs[row - 1][column] + 1:
            row -= 1
        else:
            column -= 1

    if not matched:
        return {"correct": 0, "attempted": 0, "confidence": 0.0}, matched
    last_reference_index = max(matched)
    attempted = last_reference_index + 1
    confidence_values = [
        recognized[recognized_index][1]
        for reference_index, (recognized_index, _) in matched.items()
        if reference_index <= last_reference_index and recognized[recognized_index][1] is not None
    ]
    confidence = statistics.fmean(confidence_values) if confidence_values else 0.0
    if confidence < float(os.getenv("TRANSCRIBE_MIN_WORD_CONFIDENCE", "0.35")):
        return {"correct": 0, "attempted": 0, "confidence": confidence}, matched
    correct = sum(
        is_correct and recognized[recognized_index][1] is not None
        for reference_index, (recognized_index, is_correct) in matched.items()
        if reference_index <= last_reference_index
    )
    return {"correct": correct, "attempted": attempted, "confidence": confidence}, matched


def score_transcription(exercise: Mapping[str, Any], transcription: Mapping[str, Any]) -> dict[str, Any]:
    recognized = _word_items(transcription)
    if not recognized:
        raise SpeechScoringError("Transcribe did not recognize any speech.")

    content = exercise.get("content_data", {})
    if exercise.get("kind") == "word_reading_sample":
        sections = content.get("sections", [])
        if not isinstance(sections, list):
            raise SpeechScoringError("Assessment word-reading targets are invalid.")
        targets: list[tuple[str, int, int]] = []
        flattened = []
        for section in sections:
            if not isinstance(section, Mapping) or not isinstance(section.get("items"), list):
                raise SpeechScoringError("Assessment word-reading targets are invalid.")
            section_words = [word for item in section["items"] for word in _words(str(item))]
            start = len(flattened)
            flattened.extend(section_words)
            targets.append((str(section["id"]), start, len(flattened)))
        alignment, matched = _align(flattened, recognized)
        scores = {}
        for section, start, end in targets:
            last_attempted = min(end, alignment["attempted"])
            attempted = max(0, last_attempted - start)
            correct = sum(
                is_correct
                for index, (_, is_correct) in matched.items()
                if start <= index < last_attempted
            )
            scores[section] = {
                "correct": correct,
                "attempted": attempted,
                "confidence": alignment["confidence"],
            }
        return {"scores": scores, "confidence": alignment["confidence"]}

    passage_lines = content.get("passage_lines")
    if not isinstance(passage_lines, list):
        raise SpeechScoringError("Assessment passage targets are invalid.")
    reference = [word for line in passage_lines for word in _words(str(line))]
    score, _ = _align(reference, recognized)
    return {"scores": {"reading_fluency": score}, "confidence": score["confidence"]}


class _FinalTranscriptCollector(TranscriptResultStreamHandler):
    def __init__(self, output_stream):
        super().__init__(output_stream)
        self.items = []

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        for result in transcript_event.transcript.results:
            if result.is_partial or not result.alternatives:
                continue
            for item in result.alternatives[0].items or []:
                self.items.append({
                    "type": item.item_type,
                    "alternatives": [{
                        "content": item.content,
                        "confidence": item.confidence,
                    }],
                })


class TranscribeSpeechScorer:
    def __init__(self, streaming_client=None):
        self.region = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")
        self.language_code = os.getenv("TRANSCRIBE_LANGUAGE", "en-GB")
        self.client = streaming_client or TranscribeStreamingClient(region=self.region)

    def score_audio(
        self,
        user_id: str,
        age_group: str,
        assessment_version: str,
        exercise_id: str,
        audio,
    ) -> dict[str, Any]:
        exercise = _get_spoken_exercise(age_group, assessment_version, exercise_id)
        max_bytes = int(os.getenv("MAX_SPOKEN_AUDIO_BYTES", str(10 * 1024 * 1024)))
        body = audio.read(max_bytes + 1)
        if not body or len(body) > max_bytes:
            raise SpeechScoringError("Audio must be non-empty and no larger than the upload limit.")
        pcm = self._extract_pcm(body)
        try:
            transcript = async_to_sync(self._transcribe_pcm)(pcm)
        except Exception as exc:
            raise SpeechServiceUnavailable("Amazon Transcribe streaming failed for this recording.") from exc

        result = score_transcription(exercise, transcript)
        result_token = signing.dumps(
            {
                "user_id": str(user_id),
                "age_group": age_group,
                "assessment_version": assessment_version,
                "exercise_id": exercise_id,
                **result,
            },
            salt=RESULT_TOKEN_SALT,
            compress=True,
        )
        return {"status": "completed", "speech_result_token": result_token, **result}

    @staticmethod
    def _extract_pcm(body: bytes) -> bytes:
        try:
            with wave.open(io.BytesIO(body), "rb") as recording:
                if (
                    recording.getnchannels() != 1
                    or recording.getsampwidth() != SAMPLE_WIDTH_BYTES
                    or recording.getframerate() != SAMPLE_RATE_HZ
                    or recording.getcomptype() != "NONE"
                ):
                    raise SpeechScoringError("Audio must be uncompressed 16 kHz, 16-bit, mono WAV.")
                frame_count = recording.getnframes()
                max_seconds = int(os.getenv("MAX_SPOKEN_AUDIO_SECONDS", "60"))
                if frame_count == 0 or frame_count > SAMPLE_RATE_HZ * max_seconds:
                    raise SpeechScoringError("Audio duration is outside the allowed range.")
                return recording.readframes(frame_count)
        except (wave.Error, EOFError) as exc:
            raise SpeechScoringError("Audio must be a valid PCM WAV recording.") from exc

    async def _transcribe_pcm(self, pcm: bytes) -> dict[str, Any]:
        stream = await self.client.start_stream_transcription(
            language_code=self.language_code,
            media_sample_rate_hz=SAMPLE_RATE_HZ,
            media_encoding="pcm",
        )
        collector = _FinalTranscriptCollector(stream.output_stream)
        chunk_size = SAMPLE_RATE_HZ * SAMPLE_WIDTH_BYTES * STREAM_CHUNK_MS // 1000

        async def send_audio():
            try:
                for offset in range(0, len(pcm), chunk_size):
                    chunk = pcm[offset:offset + chunk_size]
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                    await asyncio.sleep(len(chunk) / (SAMPLE_RATE_HZ * SAMPLE_WIDTH_BYTES))
            finally:
                await stream.input_stream.end_stream()

        timeout = float(os.getenv("TRANSCRIBE_STREAM_TIMEOUT_SECONDS", "80"))
        sender = asyncio.create_task(send_audio())
        receiver = asyncio.create_task(collector.handle_events())
        try:
            await asyncio.wait_for(asyncio.gather(sender, receiver), timeout=timeout)
        except Exception:
            sender.cancel()
            receiver.cancel()
            raise
        return {"results": {"items": collector.items}}


def _get_spoken_exercise(age_group: str, assessment_version: str, exercise_id: str) -> Mapping[str, Any]:
    try:
        bank = load_age_bank(age_group)
    except PracticeDataError as exc:
        raise SpeechScoringError("Learner age group does not have a supported assessment bank.") from exc
    if bank.get("assessment_version") != assessment_version:
        raise SpeechScoringError("Assessment version does not match the learner's age group.")
    exercise = next((item for item in bank["exercises"] if item.get("id") == exercise_id), None)
    if exercise is None or exercise.get("response_type") != "spoken":
        raise SpeechScoringError("Exercise is not a supported spoken assessment.")
    return exercise


def verify_speech_result_token(
    token: str,
    *,
    user_id: str,
    age_group: str,
    assessment_version: str,
    exercise_id: str,
) -> dict[str, Any]:
    try:
        payload = signing.loads(
            token,
            salt=RESULT_TOKEN_SALT,
            max_age=RESULT_TOKEN_MAX_AGE_SECONDS,
        )
    except signing.BadSignature as exc:
        raise SpeechScoringError("Speech score token is invalid or expired.") from exc
    expected = {
        "user_id": str(user_id),
        "age_group": age_group,
        "assessment_version": assessment_version,
        "exercise_id": exercise_id,
    }
    if not isinstance(payload, Mapping) or any(payload.get(key) != value for key, value in expected.items()):
        raise SpeechScoringError("Speech score token does not match this assessment.")
    scores = payload.get("scores")
    if not isinstance(scores, Mapping):
        raise SpeechScoringError("Speech score token is malformed.")
    return {"scores": scores, "confidence": payload.get("confidence", 0.0)}