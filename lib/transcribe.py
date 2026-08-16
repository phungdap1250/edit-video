"""ElevenLabs Scribe — transcript tiếng Việt có timestamp cấp từ. TDD §5.2.

Thử lại tối đa 3 lần (backoff 2s/8s/32s) rồi DỪNG. Không bao giờ chạy tiếp với
transcript rỗng — thà hỏng ồn ào còn hơn dựng ra video không có caption.
"""

from __future__ import annotations

import time
from pathlib import Path

from lib import log
from lib.errors import AIEditorError

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL_ID = "scribe_v1"
LANGUAGE_CODE = "vie"
MAX_ATTEMPTS = 3
BACKOFF_SEC = (2, 8, 32)
TIMEOUT_SEC = 600


def transcribe(audio: Path, api_key: str) -> list[dict]:
    """Trả words[]: [{"text", "start", "end", "conf"}, ...] theo thứ tự thời gian."""
    import requests

    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            wait = BACKOFF_SEC[attempt - 1]
            log.warn(f"Scribe lỗi ({last_error}) — thử lại lần {attempt + 1} sau {wait}s")
            time.sleep(wait)
        try:
            with audio.open("rb") as f:
                response = requests.post(
                    API_URL,
                    headers={"xi-api-key": api_key},
                    files={"file": (audio.name, f, "audio/mp4")},
                    data={
                        "model_id": MODEL_ID,
                        "language_code": LANGUAGE_CODE,
                        "timestamps_granularity": "word",
                        "diarize": "false",
                    },
                    timeout=TIMEOUT_SEC,
                )
            if response.status_code == 200:
                return _parse(response.json())
            last_error = f"HTTP {response.status_code}: {response.text[:160]}"
        except requests.RequestException as exc:
            last_error = str(exc)

    raise AIEditorError(
        f"ElevenLabs Scribe thất bại sau {MAX_ATTEMPTS} lần thử — {last_error}",
        suggestion="Kiểm tra mạng và hạn mức tài khoản ElevenLabs rồi chạy lại "
        "python -m steps.01_transcript <video>",
    )


def _parse(payload: dict) -> list[dict]:
    """Lọc lấy phần tử `type == word`, bỏ spacing/audio_event."""
    words = [
        {
            "text": item["text"],
            "start": float(item["start"]),
            "end": float(item["end"]),
            "conf": round(float(item.get("logprob_confidence", item.get("confidence", 1.0))), 3),
        }
        for item in payload.get("words", [])
        if item.get("type", "word") == "word" and item.get("text", "").strip()
    ]
    if not words:
        raise AIEditorError(
            "Scribe trả về transcript rỗng",
            suggestion="Kiểm tra file audio có tiếng không: ffplay work/audio.m4a",
        )
    return words
