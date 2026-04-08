"""
ORINOX v3 — Shared Configuration
Centralized auth (ADC + API key fallback) using the new google.genai SDK.
Every agent and tool imports from here instead of configuring independently.
"""
import os
from google import genai
from google.genai import types

# ─── Auth ───
# New SDK: Client() auto-detects ADC on Cloud Run/Cloud Shell.
# For API key fallback: set GOOGLE_API_KEY env var.

_api_key = os.getenv("GOOGLE_API_KEY")
if _api_key:
    client = genai.Client(api_key=_api_key)
else:
    # ADC via Vertex AI — uses service account on Cloud Run,
    # gcloud auth on Cloud Shell
    client = genai.Client(
        vertexai=True,
        project=os.getenv("PROJECT_ID"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )

# ─── Model Names (configurable via env) ───
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

# ─── GCP Project ───
PROJECT_ID = os.getenv("PROJECT_ID", "")
SA_EMAIL = os.getenv("SA_EMAIL", "")


def generate_content(prompt: str) -> str:
    """Generate text content using Gemini. Returns the response text."""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text


def embed_text(text: str) -> list[float]:
    """Generate embedding vector for text using Gemini."""
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return response.embeddings[0].values
