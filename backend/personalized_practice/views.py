from django.core.exceptions import ImproperlyConfigured
from rest_framework import permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
import uuid

from user.permissions import IsLearnerRole
from personalized_practice.domain import PracticeDataError
from personalized_practice.generator import BedrockExerciseGenerator, ExerciseGenerationError, ExerciseGenerationNotConfigured
from personalized_practice.orchestrator import PracticeOrchestrator
from personalized_practice.repository import get_repository
from personalized_practice.assessment import AssessmentSubmissionError, get_assessment_results, save_assessment_results
from personalized_practice.bank import load_age_bank
from personalized_practice.speech_scoring import (
    SpeechScoringError,
    SpeechServiceUnavailable,
    TranscribeSpeechScorer,
    verify_speech_result_token,
)
from personalized_practice.models import PracticeExercise, ProgressAttempt, LearnerSkillBaseline
from user.models import Profile


class NextExerciseView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def post(self, request):
        try:
            repository = get_repository()
            orchestrator = PracticeOrchestrator(repository, BedrockExerciseGenerator())
            result = orchestrator.next_exercise(str(request.user.pk))
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ExerciseGenerationNotConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ExerciseGenerationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except PracticeDataError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(result, status=status.HTTP_201_CREATED)


class AssessmentResponseSerializer(serializers.Serializer):
    assessment_version = serializers.CharField()
    responses = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    speech_result_tokens = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict,
    )


class SubmitAssessmentView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def post(self, request):
        serializer = AssessmentResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = Profile.objects.filter(user_id=request.user.pk).only("age_group").first()
        if profile is None or not profile.age_group:
            return Response(
                {"detail": "Set the learner's age group before submitting the assessment."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            version = serializer.validated_data["assessment_version"]
            verified_speech_scores = {
                exercise_id: verify_speech_result_token(
                    token,
                    user_id=str(request.user.pk),
                    age_group=profile.age_group,
                    assessment_version=version,
                    exercise_id=exercise_id,
                )
                for exercise_id, token in serializer.validated_data["speech_result_tokens"].items()
            }
            results = get_assessment_results(
                profile.age_group,
                serializer.validated_data,
                verified_speech_scores,
            )
        except SpeechScoringError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except AssessmentSubmissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        save_assessment_results(request.user, results)
        return Response(
            {
                "assessment_completed": True,
                "assessment_version": serializer.validated_data["assessment_version"],
                "skills": results,
            },
            status=status.HTTP_200_OK,
        )


class SpeechUploadSerializer(serializers.Serializer):
    assessment_version = serializers.CharField(max_length=80)
    exercise_id = serializers.CharField(max_length=100)
    audio = serializers.FileField()


class UploadSpeechAssessmentView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)
    parser_classes = (MultiPartParser, FormParser)
    throttle_scope = "speech_transcribe"

    def post(self, request):
        serializer = SpeechUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = Profile.objects.filter(user_id=request.user.pk).only("age_group").first()
        if profile is None or not profile.age_group:
            return Response(
                {"detail": "Set the learner's age group before uploading speech."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            result = TranscribeSpeechScorer().score_audio(
                str(request.user.pk),
                profile.age_group,
                serializer.validated_data["assessment_version"],
                serializer.validated_data["exercise_id"],
                serializer.validated_data["audio"],
            )
        except SpeechServiceUnavailable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except SpeechScoringError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


# Streaming speech sessions storage (in-memory for single-server deployments)
# For production, use Redis or similar
_STREAMING_SESSIONS = {}


class SpeechStreamChunkView(APIView):
    """
    Receive audio chunks and stream to Transcribe for real-time transcription
    """
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def post(self, request):
        session_id = request.GET.get('session_id')
        if not session_id:
            return Response({"detail": "session_id parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get or create session
            if session_id not in _STREAMING_SESSIONS:
                _STREAMING_SESSIONS[session_id] = {
                    'user_id': str(request.user.pk),
                    'audio_chunks': [],
                    'partial_transcript': '',
                }

            # Append audio chunk (in int16 PCM format)
            audio_chunk = request.body
            _STREAMING_SESSIONS[session_id]['audio_chunks'].append(audio_chunk)

            # For now, just acknowledge receipt
            # Full streaming to Transcribe API would happen here
            return Response({
                'session_id': session_id,
                'partial_transcript': _STREAMING_SESSIONS[session_id]['partial_transcript'],
                'chunk_received': len(audio_chunk),
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response(
                {"detail": f"Stream error: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class SpeechStreamFinalizeView(APIView):
    """
    Finalize streaming session and compute final assessment
    """
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def post(self, request):
        session_id = request.GET.get('session_id')
        if not session_id:
            return Response({"detail": "session_id parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if session_id not in _STREAMING_SESSIONS:
                return Response(
                    {"detail": "Session not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            session = _STREAMING_SESSIONS.pop(session_id)

            # Combine all audio chunks into single WAV file
            if not session['audio_chunks']:
                return Response(
                    {"detail": "No audio chunks in session"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # For now, return empty results
            # In production, would use the accumulated audio chunks
            return Response({
                'status': 'completed',
                'session_id': session_id,
                'final_transcript': session['partial_transcript'],
                'chunks_processed': len(session['audio_chunks']),
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            if session_id in _STREAMING_SESSIONS:
                _STREAMING_SESSIONS.pop(session_id)
            return Response(
                {"detail": f"Finalize error: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class PracticeExerciseResponseSerializer(serializers.Serializer):
    """Serializer for submitting practice exercise responses"""
    exercise_id = serializers.CharField(max_length=100)
    answers = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


class SubmitPracticeExerciseView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def post(self, request):
        """Submit a practice exercise response and auto-score it"""
        serializer = PracticeExerciseResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        exercise_id = serializer.validated_data["exercise_id"]
        answers = serializer.validated_data.get("answers", {})
        user = request.user
        user_id = str(user.pk)
        
        # Fetch the exercise
        try:
            exercise = PracticeExercise.objects.get(id=exercise_id, user_id=user)
        except PracticeExercise.DoesNotExist:
            return Response(
                {"detail": f"Exercise '{exercise_id}' not found or does not belong to this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Get answer key from private_scoring
        answer_key = exercise.private_scoring.get("answer_key", {})
        if not isinstance(answer_key, dict):
            return Response(
                {"detail": f"Exercise '{exercise_id}' has no valid answer key for scoring."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Auto-score the exercise
        correct_count = 0
        total_count = len(answer_key)
        
        if total_count == 0:
            return Response(
                {"detail": "Exercise has no items to score."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Score each item
        for item_id, expected_answer in answer_key.items():
            user_answer = answers.get(item_id)
            if user_answer == expected_answer:
                correct_count += 1
        
        # Calculate score (0-100)
        score = (correct_count / total_count) * 100 if total_count > 0 else 0
        is_correct = correct_count == total_count
        
        # Create ProgressAttempt record
        progress_attempt = ProgressAttempt.objects.create(
            user=user,
            client_id=uuid.uuid4(),
            exercise_id=exercise_id,
            skill=exercise.target_skill,
            correct=is_correct,
            response_time=0,  # Can be added to request if needed
        )
        
        # Update LearnerSkillBaseline
        baseline, created = LearnerSkillBaseline.objects.get_or_create(
            user=user,
            skill=exercise.target_skill,
            defaults={
                "baseline_score": score,
                "confidence": 0.5,
                "direct_evidence": True,
                "trend": "unknown",
                "error_counts": {},
                "metrics": {},
            }
        )
        
        if not created:
            # Update existing baseline with weighted average
            old_score = baseline.baseline_score or 0
            old_confidence = baseline.confidence or 0.35
            
            # Update score with exponential moving average
            alpha = 0.3  # Learning rate
            baseline.baseline_score = (old_score * (1 - alpha)) + (score * alpha)
            baseline.confidence = min(old_confidence + 0.1, 1.0)  # Increase confidence
            baseline.direct_evidence = True
            baseline.metrics = {
                "last_score": score,
                "attempts": baseline.metrics.get("attempts", 0) + 1,
                "correct_count": baseline.metrics.get("correct_count", 0) + (1 if is_correct else 0),
            }
            baseline.save()
        
        return Response(
            {
                "exercise_id": exercise_id,
                "score": score,
                "correct": correct_count,
                "total": total_count,
                "is_correct": is_correct,
                "skill": exercise.target_skill,
                "updated_baseline": {
                    "baseline_score": baseline.baseline_score,
                    "confidence": baseline.confidence,
                    "direct_evidence": baseline.direct_evidence,
                    "trend": baseline.trend,
                },
            },
            status=status.HTTP_200_OK,
        )
