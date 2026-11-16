"""Text-to-speech backends with an on-disk cache.

    synth("text") -> (audio_path, duration_seconds)

Pick the backend with the TTS_BACKEND env var:
    espeak      free, offline, robotic (default; good for testing timing)
    openai      needs OPENAI_API_KEY          (TTS_VOICE e.g. "onyx", "nova")
    elevenlabs  needs ELEVENLABS_API_KEY      (TTS_VOICE = a voice ID)

Audio is cached by (backend, voice, text), so re-rendering after a visual
tweak doesn't re-bill you for lines that didn't change.
"""
import hashlib
import os
import subprocess
from pathlib import Path

BACKEND = os.environ.get("TTS_BACKEND", "espeak")
VOICE = os.environ.get("TTS_VOICE", "")
CACHE = Path(os.environ.get("TTS_CACHE", "tts_cache"))



def _duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _espeak(text, path):
    subprocess.run(["espeak-ng", "-v", VOICE or "en-us", "-s", "165", "-w", str(path), text], check=True)


def _openai(text, path):
    from openai import OpenAI
    resp = OpenAI().audio.speech.create(
        model=os.environ.get("TTS_MODEL", "gpt-4o-mini-tts"),
        voice=VOICE or "onyx",
        input=text,
        response_format="wav",
    )
    path.write_bytes(resp.read())


def _elevenlabs(text, path):
    from elevenlabs.client import ElevenLabs
    audio = ElevenLabs().text_to_speech.convert(
        voice_id=VOICE,  # copy the voice ID from your ElevenLabs voice library
        text=text,
        model_id=os.environ.get("TTS_MODEL", "eleven_multilingual_v2"),
        output_format="mp3_44100_128",
    )
    with open(path, "wb") as f:
        for chunk in audio:
            f.write(chunk)


_BACKENDS = {"espeak": (_espeak, "wav"), "openai": (_openai, "wav"), "elevenlabs": (_elevenlabs, "mp3")}


_SAY = [  # how symbols in captions should be read aloud (longest first)
    ("O(n log n)", "O of n log n"), ("O(n²)", "O of n squared"), ("O(n^2)", "O of n squared"),
    ("O(n)", "O of n"), ("O(1)", "O of 1"), ("O(log n)", "O of log n"),
    ("→", " to "), ("−", " minus "), ("≤", " at most "), ("≥", " at least "),
    ("#", "number "), ("\n", " "),
]


def speakable(text):
    for a, b in _SAY:
        text = text.replace(a, b)
    return " ".join(text.split())


def synth(text):
    text = speakable(text)
    fn, ext = _BACKENDS[BACKEND]
    CACHE.mkdir(exist_ok=True)
    key = hashlib.sha1(f"{BACKEND}|{VOICE}|{text}".encode()).hexdigest()[:16]
    path = CACHE / f"{key}.{ext}"
    if not path.exists() or path.stat().st_size == 0:
        tmp = path.with_suffix(".part." + ext)
        try:
            fn(text, tmp)
            tmp.rename(path)  # only cache a file once it fully succeeded
        finally:
            tmp.unlink(missing_ok=True)
    return str(path), _duration(path)
