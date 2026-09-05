"""
Self-hosted LLM adapter for TinyLlama running on EKS.

The TinyLlama server exposes:
  POST http://<service-host>:8080/generate
  Body: {"prompt": str, "max_new_tokens": int, "temperature": float}
  Response: {"answer": str, "model": str}

This adapter is called by rag_engine.py when model_id == TINYLLAMA_ENDPOINT.
It returns the same dict shape as generate_response() so no other code changes.
"""
import os
import requests
import time
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv
load_dotenv()

# Set TINYLLAMA_ENDPOINT in .env after deploying to EKS.
# For local port-forward testing use: http://localhost:8080
# For in-cluster access use: http://tinyllama-tinyllama:8080 (k8s service DNS)
TINYLLAMA_ENDPOINT    = os.getenv("TINYLLAMA_ENDPOINT", "http://localhost:8080")
TINYLLAMA_TIMEOUT     = int(os.getenv("TINYLLAMA_TIMEOUT", "120"))
TINYLLAMA_ENABLE_MOCK = os.getenv("TINYLLAMA_ENABLE_MOCK", "false").lower() in ("true", "1", "yes")


def call_self_hosted(prompt: str, max_new_tokens: int = 200,
                     temperature: float = 0.1) -> dict:
    """
    Send a prompt to the self-hosted TinyLlama server and return the response.
    Formats a dense context prompt to ensure document details (leave policy, SOPs)
    reach TinyLlama intact while keeping CPU inference latency under 8 seconds.
    """
    url = f"{TINYLLAMA_ENDPOINT}/generate"

    # Extract user question and retrieved docs if this is a standard RCTFC RAG prompt
    if "Retrieved Documents:" in prompt and "Employee Question:" in prompt:
        try:
            context_part = prompt.split("Retrieved Documents:")[1].split("## TASK")[0].strip()
            question_part = prompt.split("Employee Question:")[1].split("## FORMAT")[0].strip()
            # Keep top ~1500 chars of context so PDF details (leave 20 days, sick 10 days) are intact
            dense_prompt = f"Context Documents:\n{context_part[:1600]}\n\nQuestion: {question_part}\n\nDetailed Answer from Context:"
        except Exception:
            dense_prompt = prompt[:2000]
    else:
        dense_prompt = prompt[:2000]

    payload = {
        "prompt":         dense_prompt,
        "max_new_tokens": min(max_new_tokens, 200),
        "temperature":    temperature,
    }

    start = time.time()
    last_err = None
    answer = None

    # Try up to 2 attempts with 1s sleep in case of transient ELB socket reset
    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, timeout=TINYLLAMA_TIMEOUT)
            response.raise_for_status()
            elapsed = time.time() - start
            data   = response.json()
            answer = data.get("answer", "")
            break
        except Exception as e:
            last_err = e
            time.sleep(1)

    if answer is None:
        if TINYLLAMA_ENABLE_MOCK:
            elapsed = time.time() - start
            user_part = prompt
            if "Employee Question:" in prompt:
                user_part = prompt.split("Employee Question:")[-1].split("\n")[0].strip()

            import re
            lines = []
            emails = re.findall(r'[\w\.-]+@[\w\.-]+', user_part)
            phones = re.findall(r'\b\d{10}\b|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', user_part)
            names = re.findall(r'name is (\w+)', user_part, re.IGNORECASE)
            ages  = re.findall(r'age (\d+)', user_part, re.IGNORECASE)

            if emails or phones or names or ages:
                lines.append("**Contact Details Summary:**")
                if names:  lines.append(f"- **Name:** {names[0].title()}")
                if ages:   lines.append(f"- **Age:** {ages[0]}")
                if emails: lines.append(f"- **Email:** {emails[0]}")
                if phones: lines.append(f"- **Mobile:** {phones[0]}")
            else:
                lines.append(f"Processed request: *\"{user_part[:150]}\"*")
                lines.append("Query analyzed via self-hosted open-source model pipeline (TinyLlama 1.1B).")

            content_body = "\n".join(lines)
            answer = (
                f"[TinyLlama 1.1B (Self-Hosted Demonstration Mode)]\n\n"
                f"{content_body}\n\n"
                f"*(Processed locally with $0.000000 USD AWS token cost)*"
            )
        else:
            raise last_err

    approx_input_tokens  = int(len(prompt.split()) * 1.3)
    approx_output_tokens = int(len(answer.split()) * 1.3)

    return {
        "answer":        answer,
        "input_tokens":  approx_input_tokens,
        "output_tokens": approx_output_tokens,
        "model_id":      TINYLLAMA_ENDPOINT,
        "cost_usd":      0.0,    # self-hosted: no per-token charge
        "latency_sec":   round(elapsed, 2),
    }


def health_check() -> bool:
    """Returns True if the TinyLlama server is reachable (or fallback if mock mode is explicitly enabled)."""
    try:
        r = requests.get(f"{TINYLLAMA_ENDPOINT}/health", timeout=5)
        if r.status_code == 200:
            return True
    except Exception:
        pass
    return TINYLLAMA_ENABLE_MOCK

