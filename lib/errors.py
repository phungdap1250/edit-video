"""Lỗi nghiệp vụ có thông báo tiếng Việt — TDD §13.3."""

from __future__ import annotations

import sys


class AIEditorError(Exception):
    """Lỗi nghiệp vụ — thông báo tiếng Việt, kèm gợi ý lệnh chạy tiếp."""

    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion

    def render(self) -> str:
        out = f"\n✗ {self.message}\n"
        if self.suggestion:
            out += f"\n  → {self.suggestion}\n"
        return out


class PlanConflict(AIEditorError):
    """Version trên đĩa khác version lúc đọc → có tác nhân khác đã ghi."""

    def __init__(self, message: str, conflicts: list[dict] | None = None, saved: int = 0):
        super().__init__(message, suggestion="Xem danh sách conflicts và quyết từng mục")
        self.conflicts = conflicts or []
        self.saved = saved


def die(exc: AIEditorError, *, verbose: bool = False) -> None:
    """In lỗi nghiệp vụ rồi thoát mã 1 — không stack trace trừ khi --verbose."""
    sys.stderr.write(exc.render())
    if verbose:
        raise exc
    sys.exit(1)
