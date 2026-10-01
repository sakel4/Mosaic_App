import getpass

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from personalized_practice.models import LearnerSkillBaseline, PracticeExercise
from user.models import Profile


TEST_EMAIL = "emmbamp@gmail.com"


def run() -> None:
    user_model = get_user_model()
    if user_model.objects.filter(email=TEST_EMAIL).exists():
        raise RuntimeError(f"Refusing to overwrite existing account {TEST_EMAIL}.")

    password = getpass.getpass("Enter the test account password (input hidden): ")
    if not password:
        raise ValueError("A password is required for the test account.")

    user = user_model.objects.create_user(
        email=TEST_EMAIL,
        password=password,
        first_name="Manos",
    )
    Profile.objects.create(user=user, age_years=29)
    LearnerSkillBaseline.objects.create(
        user=user,
        skill="comprehension",
        baseline_score=58,
        confidence=0.82,
        direct_evidence=True,
        trend="stable",
        error_counts={"inference_miss": 1},
    )

    client = APIClient()
    login = client.post(
        "/api/auth/login/",
        {"email": TEST_EMAIL, "password": password},
        format="json",
    )
    password = None
    if login.status_code != 200:
        raise RuntimeError(f"Test account login failed with HTTP {login.status_code}.")

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    response = client.post("/api/practice/next/", {}, format="json")
    if response.status_code != 201:
        print({"login_status": login.status_code, "practice_status": response.status_code, "detail": response.data})
        return

    exercise_id = response.data["exercise_id"]
    stored = PracticeExercise.objects.get(pk=exercise_id, user=user)
    print(
        {
            "account_email": TEST_EMAIL,
            "first_name": user.first_name,
            "age_years": user.profile.age_years,
            "age_group": response.data["age_group"],
            "practice_status": response.status_code,
            "target_skill": response.data["target_skill"],
            "difficulty": response.data["difficulty"],
            "exercise_id": exercise_id,
            "exercise_persisted": stored.pk == exercise_id,
            "answer_key_returned": "private_scoring" in response.data,
        }
    )
    login.data.clear()
    password = None
