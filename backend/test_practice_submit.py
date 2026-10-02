#!/usr/bin/env python
"""Test script for practice exercise submission and auto-scoring"""

import requests
import json

BASE_URL = "http://127.0.0.1:8001/api"

# Step 1: Login and get token
print("=" * 60)
print("STEP 1: Login and get token")
print("=" * 60)

login_response = requests.post(
    f"{BASE_URL}/auth/login/",
    json={"email": "emmbamp@gmail.com", "password": "password123"}
)
print(f"Status: {login_response.status_code}")
login_data = login_response.json()
print(f"Response: {json.dumps(login_data, indent=2)}")

if login_response.status_code != 200:
    print("❌ Login failed!")
    exit(1)

token = login_data.get("access")
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Token obtained: {token[:50]}...")

# Step 2: Get a practice exercise
print("\n" + "=" * 60)
print("STEP 2: Get a practice exercise")
print("=" * 60)

exercise_response = requests.post(
    f"{BASE_URL}/practice/next/",
    headers=headers
)
print(f"Status: {exercise_response.status_code}")
exercise_data = exercise_response.json()
print(f"Response: {json.dumps(exercise_data, indent=2)}")

if exercise_response.status_code not in [200, 201]:
    print("❌ Failed to get exercise!")
    exit(1)

exercise_id = exercise_data.get("exercise_id")
exercise_content = exercise_data.get("exercise", {})
print(f"✅ Exercise obtained: {exercise_id}")
print(f"   Title: {exercise_content.get('title')}")
print(f"   Skill: {exercise_data.get('target_skill')}")

# Step 3: Submit practice exercise with answers
print("\n" + "=" * 60)
print("STEP 3: Submit practice exercise with answers")
print("=" * 60)

# For testing, create sample answers
# Looking at typical exercise structure, we'll create some answers
# In a real scenario, these would come from the user's actual responses
content_data = exercise_content.get("content_data", {})
print(f"Content data: {json.dumps(content_data, indent=2)}")

# Create simple answers for testing
answers = {}
if isinstance(content_data, dict):
    # If content_data has items, create answers for each
    if "items" in content_data:
        for i, item in enumerate(content_data["items"]):
            item_id = item.get("id") or str(i)
            # For testing, just pick the first option or a default
            if "options" in item:
                answers[item_id] = item["options"][0] if item["options"] else "1"
            else:
                answers[item_id] = "1"
    elif "questions" in content_data:
        for i, question in enumerate(content_data["questions"]):
            question_id = question.get("id") or str(i)
            if "options" in question:
                answers[question_id] = question["options"][0] if question["options"] else "A"
            else:
                answers[question_id] = "A"
    else:
        # Generic fallback
        answers = {"q1": "1", "q2": "2", "q3": "1"}

submit_payload = {
    "exercise_id": exercise_id,
    "answers": answers
}

print(f"Submitting payload: {json.dumps(submit_payload, indent=2)}")

submit_response = requests.post(
    f"{BASE_URL}/practice/submit/",
    headers=headers,
    json=submit_payload
)

print(f"Status: {submit_response.status_code}")
submit_data = submit_response.json()
print(f"Response: {json.dumps(submit_data, indent=2)}")

if submit_response.status_code == 200:
    print("\n✅ SUCCESS!")
    print(f"   Score: {submit_data.get('score')}%")
    print(f"   Correct: {submit_data.get('correct')}/{submit_data.get('total')}")
    print(f"   Skill: {submit_data.get('skill')}")
    print(f"   Updated Baseline Score: {submit_data.get('updated_baseline', {}).get('baseline_score')}%")
    print(f"   Confidence: {submit_data.get('updated_baseline', {}).get('confidence')}")
else:
    print(f"\n❌ FAILED with status {submit_response.status_code}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
