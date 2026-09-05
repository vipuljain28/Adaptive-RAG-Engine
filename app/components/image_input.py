"""
Image upload component for the Knowledge Assistant.

Renders a file uploader in the Streamlit UI.
Resizes images that exceed Claude's vision limits, converts to JPEG,
and returns a (base64_string, media_type) tuple.

Claude vision limits:
  Max image dimension: 1568 px on any side
  Supported formats:   JPEG, PNG, GIF, WebP
"""

from __future__ import annotations
from typing import Tuple, Optional
import streamlit as st
import base64
import io

from PIL import Image


# Claude's maximum image dimension (either width or height)
_MAX_DIM = 1568


def render_image_upload() -> Tuple[Optional[str], Optional[str]]:
    """
    Render an image file uploader.

    Returns:
        (base64_string, "image/jpeg") if an image was uploaded.
        (None, None)                  if no image was uploaded.
    """
    uploaded = st.file_uploader(
        "📎 Attach Image",
        type=["jpg", "jpeg", "png", "gif", "webp"],
        key="image_uploader",
        help="Upload an image to ask questions about it. Vision model is used automatically.",
        label_visibility="collapsed",
    )

    if uploaded is None:
        return None, None

    try:
        img = Image.open(uploaded)

        # Convert to RGB so we can always save as JPEG
        # (PNG/GIF may have alpha channel or palette mode)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resize if larger than Claude's vision limit
        if img.width > _MAX_DIM or img.height > _MAX_DIM:
            img.thumbnail((_MAX_DIM, _MAX_DIM), Image.LANCZOS)
            st.caption(f"Image resized to {img.width}×{img.height} px for vision model.")

        # Show preview
        st.image(img, caption="Attached image", width=200)

        # Encode to base64
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return b64, "image/jpeg"

    except Exception as e:
        st.error(f"Could not process image: {e}", icon="❌")
        return None, None


def clear_image_upload():
    """Reset the image uploader widget by clearing its session state key."""
    if "image_uploader" in st.session_state:
        del st.session_state["image_uploader"]
