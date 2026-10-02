import json
import os
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

from bedrock.exceptions import BedrockError, BedrockNotConfigured

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_REGION = "eu-west-1"


def get_client(region: str | None = None):
    region = region or os.getenv("AWS_DEFAULT_REGION", DEFAULT_REGION)
    return boto3.client("bedrock-runtime", region_name=region)


def converse(
    prompt: str,
    *,
    system: str | None = None,
    model_id: str | None = None,
    max_tokens: int = 1400,
    temperature: float = 0.7,
    client=None,
) -> str:
    """Send a single-turn prompt through the Bedrock Converse API and return the text reply."""
    model_id = model_id or os.getenv("BEDROCK_MODEL_ID")
    if not model_id:
        raise BedrockNotConfigured("Set BEDROCK_MODEL_ID in the backend environment.")

    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system:
        kwargs["system"] = [{"text": system}]

    try:
        client = client or get_client()
        response = client.converse(**kwargs)
        content = response["output"]["message"]["content"]
        return next(block["text"] for block in content if "text" in block)
    except (BotoCoreError, ClientError, KeyError, StopIteration) as exc:
        raise BedrockError("Amazon Bedrock did not return a valid response.") from exc


def parse_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from model output, tolerating surrounding prose."""
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
    raise BedrockError("Amazon Bedrock did not return a valid JSON object.")


def converse_json(prompt: str, **kwargs: Any) -> dict[str, Any]:
    return parse_json_object(converse(prompt, **kwargs))
