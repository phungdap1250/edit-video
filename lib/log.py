"""Ghi log dùng chung — TDD §13.4. Không bao giờ ghi khoá API vào log."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from lib import paths

TZ = timezone(timedelta(hours=7))  # Asia/Saigon — TDD §13.5

_LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}


def now_iso() -> str:
    """ISO 8601 có offset: 2026-08-16T14:32:07+07:00."""
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def _write(level: str, text: str) -> None:
    line = f"{now_iso()} [{level.upper():5}] {text}"
    stream = sys.stderr if _LEVELS[level] >= _LEVELS["warn"] else sys.stdout
    print(line, file=stream)
    paths.LOGS.mkdir(parents=True, exist_ok=True)
    with paths.RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def debug(text: str) -> None:
    _write("debug", text)


def info(text: str) -> None:
    _write("info", text)


def warn(text: str) -> None:
    _write("warn", text)


def error(text: str) -> None:
    _write("error", text)


def step(name: str, phase: str, **extra) -> None:
    """log.step("02_detect_cuts", "xong", duration_sec=94.2)"""
    tail = " ".join(f"{k}={v}" for k, v in extra.items())
    _write("info", f"[{name}] {phase}{(' ' + tail) if tail else ''}")
