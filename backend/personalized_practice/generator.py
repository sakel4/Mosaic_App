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
                "Do not copy assessment wording, passages, items, or answer options from the seed.",
                "Create new content that measures only the target skill and is appropriate to the age group.",
                "Return valid JSON only, with no markdown or surrounding prose.",
                "Return an object with title, instructions, prompt, content_data, and private_scoring.",
                "private_scoring must include answer_key and error_types for server-side evaluation.",
            ],
            "age_group": age_group,
            "target_skill": skill,
            "difficulty": difficulty,
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
            generated = json.loads(text)
        except (BotoCoreError, ClientError, KeyError, StopIteration, json.JSONDecodeError) as exc:
            raise ExerciseGenerationError("Amazon Bedrock did not return a valid exercise response.") from exc

        required = {"title", "instructions", "prompt", "content_data", "private_scoring"}
        if not isinstance(generated, dict) or not required.issubset(generated):
            raise ExerciseGenerationError("Generated exercise is missing required fields.")
        if not isinstance(generated["content_data"], dict) or not isinstance(generated["private_scoring"], dict):
            raise ExerciseGenerationError("Generated exercise content or scoring has an invalid shape.")
        scoring = generated["private_scoring"]
        if not scoring.get("answer_key") or not isinstance(scoring.get("error_types"), list):
            raise ExerciseGenerationError("Generated exercise lacks a private answer key or error types.")
        return generated
