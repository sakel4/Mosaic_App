import json
import os

import boto3

from personalized_practice.bank import select_seed
from personalized_practice.generator import BedrockExerciseGenerator, ExerciseGenerationError


class _InspectingClient:
    def __init__(self, client):
        self.client = client

    def converse(self, **kwargs):
        response = self.client.converse(**kwargs)
        text = next(
            block["text"] for block in response["output"]["message"]["content"] if "text" in block
        )
        try:
            generated = json.loads(text)
        except json.JSONDecodeError:
            print({"response_format": "not_json", "response_length": len(text)})
            return response
        scoring = generated.get("private_scoring")
        print(
            {
                "top_level_fields": sorted(generated),
                "private_scoring_type": type(scoring).__name__,
                "private_scoring_fields": sorted(scoring) if isinstance(scoring, dict) else None,
                "answer_key_type": type(scoring.get("answer_key")).__name__ if isinstance(scoring, dict) else None,
                "answers_type": type(scoring.get("answers")).__name__ if isinstance(scoring, dict) else None,
                "error_types_type": type(scoring.get("error_types")).__name__ if isinstance(scoring, dict) else None,
            }
        )
        return response


def run() -> None:
    client = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_DEFAULT_REGION", "eu-west-1"),
    )
    generator = BedrockExerciseGenerator(_InspectingClient(client))
    seed = select_seed("19_plus", "comprehension", set())
    try:
        generator.generate(
            age_group="19_plus",
            skill="comprehension",
            difficulty=3,
            seed=seed,
            recent_exercises=(),
        )
        print({"validation": "accepted"})
    except ExerciseGenerationError as exc:
        print({"validation": "rejected", "reason": str(exc)})
