from django.urls import path
from .progress import ProgressView

from personalized_practice.views import (
    NextExerciseView,
    SubmitAssessmentView,
    SubmitPracticeExerciseView,
    UploadSpeechAssessmentView,
    SpeechStreamChunkView,
    SpeechStreamFinalizeView,
)


urlpatterns = [
    path("progress/", ProgressView.as_view(), name="learner-progress"),
    path("next/", NextExerciseView.as_view(), name="next-practice-exercise"),
    path("submit/", SubmitPracticeExerciseView.as_view(), name="submit-practice-exercise"),
    path("assessment/submit/", SubmitAssessmentView.as_view(), name="submit-assessment"),
    path("assessment/speech/", UploadSpeechAssessmentView.as_view(), name="upload-assessment-speech"),
    path("assessment/speech-stream/", SpeechStreamChunkView.as_view(), name="speech-stream-chunk"),
    path("assessment/speech-finalize/", SpeechStreamFinalizeView.as_view(), name="speech-stream-finalize"),
]
