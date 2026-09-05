"""
Creates or updates the Bedrock Guardrail for the Knowledge Assistant.
Run once before launching the application.

Usage:
    python guardrails/setup_guardrail.py

Effect:
    - Creates or updates guardrail in Amazon Bedrock (us-east-1 by default)
    - Creates a guardrail version
    - Writes GUARDRAIL_ID and GUARDRAIL_VERSION into .env automatically
"""
import boto3
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from guardrails.guardrail_config import (
    GUARDRAIL_NAME,
    GUARDRAIL_DESCRIPTION,
    PII_ENTITIES,
    DENIED_TOPICS,
    CONTENT_FILTERS,
    BLOCKED_INPUT_MESSAGE,
    BLOCKED_OUTPUT_MESSAGE,
)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def create_guardrail():
    client = boto3.client("bedrock", region_name=AWS_REGION)
    print(f"Setting up Bedrock Guardrail: '{GUARDRAIL_NAME}' in {AWS_REGION} ...")

    existing_id = None
    try:
        # Check existing guardrails
        list_resp = client.list_guardrails(maxResults=100)
        for g in list_resp.get("guardrails", []):
            if g["name"] == GUARDRAIL_NAME:
                existing_id = g["id"]
                break
    except Exception as e:
        print(f"  Note checking existing guardrails: {e}")

    sensitive_policy = {
        "piiEntitiesConfig": [
            {"type": e["type"], "action": e["action"]} for e in PII_ENTITIES
        ]
    }
    topic_policy = {
        "topicsConfig": [
            {
                "name":       t["name"],
                "definition": t["definition"],
                "examples":   t["examples"],
                "type":       t["type"],
            }
            for t in DENIED_TOPICS
        ]
    }
    content_policy = {
        "filtersConfig": [
            {
                "type":           f["type"],
                "inputStrength":  f["inputStrength"],
                "outputStrength": f["outputStrength"],
            }
            for f in CONTENT_FILTERS
        ]
    }

    if existing_id:
        print(f"  Updating existing Guardrail ID: {existing_id}")
        response = client.update_guardrail(
            guardrailIdentifier=existing_id,
            name=GUARDRAIL_NAME,
            description=GUARDRAIL_DESCRIPTION,
            sensitiveInformationPolicyConfig=sensitive_policy,
            topicPolicyConfig=topic_policy,
            contentPolicyConfig=content_policy,
            blockedInputMessaging=BLOCKED_INPUT_MESSAGE,
            blockedOutputsMessaging=BLOCKED_OUTPUT_MESSAGE,
        )
        guardrail_id = response["guardrailId"]
    else:
        response = client.create_guardrail(
            name=GUARDRAIL_NAME,
            description=GUARDRAIL_DESCRIPTION,
            sensitiveInformationPolicyConfig=sensitive_policy,
            topicPolicyConfig=topic_policy,
            contentPolicyConfig=content_policy,
            blockedInputMessaging=BLOCKED_INPUT_MESSAGE,
            blockedOutputsMessaging=BLOCKED_OUTPUT_MESSAGE,
        )
        guardrail_id = response["guardrailId"]

    # Create version
    try:
        ver_resp = client.create_guardrail_version(
            guardrailIdentifier=guardrail_id,
            description="Version 1 created by setup_guardrail.py"
        )
        guardrail_version = ver_resp.get("version", "1")
    except Exception:
        guardrail_version = "DRAFT"

    print(f"  Guardrail ID:      {guardrail_id}")
    print(f"  Guardrail Version: {guardrail_version}")

    # Write back to .env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            content = f.read()

        if re.search(r"^GUARDRAIL_ID=.*$", content, flags=re.MULTILINE):
            content = re.sub(r"^GUARDRAIL_ID=.*$", f"GUARDRAIL_ID={guardrail_id}", content, flags=re.MULTILINE)
        else:
            content += f"\nGUARDRAIL_ID={guardrail_id}\n"

        if re.search(r"^GUARDRAIL_VERSION=.*$", content, flags=re.MULTILINE):
            content = re.sub(r"^GUARDRAIL_VERSION=.*$", f"GUARDRAIL_VERSION={guardrail_version}", content, flags=re.MULTILINE)
        else:
            content += f"\nGUARDRAIL_VERSION={guardrail_version}\n"

        with open(env_path, "w") as f:
            f.write(content)
        print("  GUARDRAIL_ID and GUARDRAIL_VERSION written to .env [OK]")
    else:
        print("  .env not found — set these manually:")
        print(f"    GUARDRAIL_ID={guardrail_id}")
        print(f"    GUARDRAIL_VERSION={guardrail_version}")

    return guardrail_id, guardrail_version


if __name__ == "__main__":
    create_guardrail()
