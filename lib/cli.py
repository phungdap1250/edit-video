"""Khung CLI dùng chung — quy ước §4.1.

Mã thoát: 0 thành công · 1 lỗi nghiệp vụ (tiếng Việt) · 2 lỗi hệ thống.
Cờ chung: --dry-run · --json (cho Claude đọc) · --verbose (in stack trace).
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from typing import Callable

from lib import log
from lib.errors import AIEditorError


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--dry-run", action="store_true", help="in ra sẽ làm gì, không ghi file")
    parser.add_argument("--json", action="store_true", help="in kết quả JSON một dòng (cho Claude)")
    parser.add_argument("--verbose", action="store_true", help="in stack trace khi lỗi")
    return parser


def run(name: str, main: Callable[[argparse.Namespace], dict], args: argparse.Namespace) -> None:
    """Chạy một step/tool, lo mã thoát và định dạng đầu ra."""
    log.step(name, "bắt đầu")
    try:
        result = main(args) or {}
    except AIEditorError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": exc.message}, ensure_ascii=False))
        else:
            sys.stderr.write(exc.render())
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    except NotImplementedError as exc:
        sys.stderr.write(f"\n✗ Chưa implement: {exc}\n")
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        log.error(f"[{name}] lỗi hệ thống")
        sys.exit(2)

    if args.json:
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    log.step(name, "xong")
