"""
Voice input component for the Knowledge Assistant.

Renders a microphone button in the Streamlit UI.
When clicked, records audio, transcribes it via Google Speech Recognition,
and returns the text string.

Dependencies:
  SpeechRecognition==3.10.4  (pip)
  pyaudio==0.2.14            (pip — also needs PortAudio system library)

On EC2 Linux without audio hardware:
  The button will appear but clicking it shows a warning instead of crashing.
"""

from __future__ import annotations
from typing import Optional
import streamlit as st


def render_voice_input() -> Optional[str]:
    """
    Render a 🎙️ Record Voice button.

    Returns:
        Transcribed text string if recording succeeded.
        None if the button was not clicked, recording failed, or no audio device.
    """
    if not st.button("🎙️ Voice", key="voice_btn", help="Record a question by voice"):
        return None

    # Try to import pyaudio/speech_recognition — gracefully degrade if missing
    try:
        import speech_recognition as sr
    except ImportError:
        st.warning(
            "SpeechRecognition library not installed. "
            "Run: `pip install SpeechRecognition pyaudio`",
            icon="⚠️",
        )
        return None

    recognizer = sr.Recognizer()

    try:
        with st.spinner("🎙️ Listening… speak now (up to 30 seconds)"):
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=30)

        with st.spinner("Transcribing…"):
            text = recognizer.recognize_google(audio)

        st.success(f"Heard: *{text}*", icon="✅")
        return text

    except sr.WaitTimeoutError:
        st.warning("No speech detected. Please try again.", icon="⚠️")
    except sr.UnknownValueError:
        st.warning("Could not understand the audio. Please speak clearly and try again.", icon="⚠️")
    except sr.RequestError as e:
        st.error(f"Speech recognition service error: {e}", icon="❌")
    except OSError:
        st.warning(
            "No microphone found. "
            "Voice input requires a connected audio device.",
            icon="⚠️",
        )
    except Exception as e:
        st.error(f"Voice input error: {e}", icon="❌")

    return None
