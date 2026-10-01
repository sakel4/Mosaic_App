import json
import os
from pathlib import Path
from typing import Any, Mapping

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

from personalized_practice.bank import public_content


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class ExerciseGenerationError(Exception):
    pass


class ExerciseGenerationNotConfigured(ExerciseGenerationError):
    pass


def _describe_shape(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _describe_shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return {
            "type": "array",
            "length": len(value),
            "items": _describe_shape(value[0]) if value else None,
        }
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return "null"


def _parse_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    for start, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ExerciseGenerationError("Amazon Bedrock did not return a valid JSON object.")


def _normalize_private_scoring(generated: dict[str, Any]) -> None:
    scoring = generated["private_scoring"]
    if not isinstance(scoring, dict):
        raise ExerciseGenerationError("Generated exercise private_scoring must be an object.")

    if not scoring.get("answer_key"):
        for alias in ("answers", "correct_answers", "correct_answer"):
            if scoring.get(alias):
                scoring["answer_key"] = scoring[alias]
                break
    if not scoring.get("answer_key"):
        raise ExerciseGenerationError("Generated exercise lacks a non-empty private answer key.")

    error_types = scoring.get("error_types", [])
    if isinstance(error_types, str):
        error_types = [error_types]
    if not isinstance(error_types, list):
        raise ExerciseGenerationError("Generated exercise error_types must be a list.")
    scoring["error_types"] = error_types


class BedrockExerciseGenerator:
    def __init__(self, client=None):
        self.client = client

    def generate(
        self,
        *,
        age_group: str,
        skill: str,
        difficulty: int,
        seed: Mapping[str, Any],
        recent_exercises: tuple[Mapping[str, Any], ...],
        secondary_skill: str | None = None,
        learner_profile: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        model_id = os.getenv("BEDROCK_MODEL_ID")
        region = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")
        if not model_id:
            raise ExerciseGenerationNotConfigured(
                "Set BEDROCK_MODEL_ID in the backend environment."
            )

        prompt = {
            "goal": "Create one original practice exercise similar in structure, but not wording or answers, to the source seed.",
            "constraints": [
                "This is educational practice, never a diagnosis or clinical assessment.",
                "Use the exact age_group, target skill, and difficulty supplied by the server.",
                "Treat the server-selected target_skill as authoritative; do not select or replace it.",
                "Use secondary_skill only as a light supporting context, never as the main task.",
                "Use learner_profile confidence, metrics, and repeated errors to adapt examples without making diagnoses.",
                "These are criterion-based evidence values, not age-normalized or norm-referenced scores.",
                "Use age_group to adapt vocabulary, context, and language complexity while preserving the same underlying skill construct.",
                "Do not copy assessment wording, passages, items, or answer options from the seed.",
                "Create new content that measures only the target skill and is appropriate to the age group.",
                "Return only one JSON object. The response must start with { and end with }.",
                "Do not include markdown fences, commentary, or prose around the JSON object.",
                "Return an object with title, instructions, prompt, content_data, and private_scoring.",
                "private_scoring must contain a non-empty answer_key object mapping item IDs to correct answers, plus error_types as an array (an empty array is allowed).",
            ],
            "age_group": age_group,
            "target_skill": skill,
            "secondary_skill": secondary_skill,
            "difficulty": difficulty,
            "learner_profile": learner_profile or {},
            "response_type": seed["response_type"],
            "source_structure_only": {
                "kind": seed["kind"],
                "content_shape": _describe_shape(seed.get("content_data", {})),
            },
            "recent_exercises_to_avoid_repeating": [
                {
                    "title": item.get("title"),
                    "prompt": item.get("prompt"),
                    "content_data": public_content(item.get("content_data", {})),
                }
                for item in recent_exercises[:5]
            ],
        }
        try:
            client = self.client or boto3.client("bedrock-runtime", region_name=region)
            response = client.converse(
                modelId=model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": json.dumps(prompt, ensure_ascii=True)}],
                    }
                ],
                inferenceConfig={"maxTokens": 1400, "temperature": 0.7},
            )
            content = response["output"]["message"]["content"]
            text = next(block["text"] for block in content if "text" in block)
            generated = _parse_json_object(text)
        except (BotoCoreError, ClientError, KeyError, StopIteration) as exc:
            raise ExerciseGenerationError("Amazon Bedrock did not return a valid exercise response.") from exc

        required = {"title", "instructions", "prompt", "content_data", "private_scoring"}
        if not isinstance(generated, dict) or not required.issubset(generated):
            raise ExerciseGenerationError("Generated exercise is missing required fields.")
        if not isinstance(generated["content_data"], dict) or not isinstance(generated["private_scoring"], dict):
            raise ExerciseGenerationError("Generated exercise content or scoring has an invalid shape.")
        _normalize_private_scoring(generated)
        return generated
