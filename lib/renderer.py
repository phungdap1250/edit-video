"""Hàng rào chống rủi ro HyperFrames — TDD §2.4.

TOÀN BỘ tiếp xúc với HyperFrames nằm trong file này. Không file nào khác được
import hyperframes hay chạy lệnh `hf ...` / `npx hyperframes ...` —
`checks/check_renderer_isolation.py` grep khẳng định điều đó.

XÁC MINH THẬT (16/08/2026): CLI thật là `npx hyperframes <lệnh>`, KHÔNG PHẢI
binary `hf` trong PATH như TDD §14 giả định (`HYPERFRAMES_BIN=hf`). Project
scaffold thật gồm `index.html` + `hyperframes.json` (không phải `project.hf`
như TDD §2.3 phác thảo trước khi xác minh) — điều chỉnh theo thực tế đã kiểm
bằng `npx hyperframes doctor` + `npx hyperframes init` thật trên máy này.
Node 22.23.2, ffmpeg 8.1, HyperFrames 0.7.109 — đều sẵn sàng.

Nếu HyperFrames hụt tiếp ở phần nào đó (không làm được caption karaoke, không
ghi được Variables từ ngoài) thì chỗ phải sửa vẫn là đúng một file này.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from html import escape as escape_html
from pathlib import Path

from lib import log
from lib.errors import AIEditorError

# Tăng tay khi đổi logic dựng — vào block_hash, làm mọi khối render lại (§6.3).
RENDERER_VERSION = 2

# Điểm chèn clip tiếp theo trong index.html — build_video_track để lại, các
# lớp sau (caption/overlay/cutaway) chèn thêm vào đây, KHÔNG xoá marker đi.
CLIPS_MARKER = (
    "      <!-- Điểm chèn clip tiếp theo — không xoá, các lớp sau cần nó -->"
)

CAPTION_TRACK_INDEX = 20

# init/check/render tự kiểm tra AI skill trên GitHub trừ khi tắt — chạy tự
# động (không phải phiên tương tác) nên tắt để không phụ thuộc mạng.
_ENV = {**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1"}

_RESOLUTION_PRESETS = {
    "landscape": (1920, 1080),
    "portrait": (1080, 1920),
}


def _run(args: list[str], cwd: Path | None, *, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["npx", "hyperframes", *args],
        cwd=str(cwd) if cwd else None,
        env=_ENV,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def hf_available() -> tuple[bool, str]:
    """Kiểm HyperFrames có cài và chạy được không. Trả (ok, phiên bản/lý do).

    Chỉ Node.js và bản thân CLI là điều kiện chặn cứng. TTS/BGM/Docker là tính
    năng không dùng tới trong scope [RND-01]; RAM thấp chỉ cảnh báo, không chặn
    (đã có cơ chế tạm dừng render riêng — TDD §11.2).
    """
    try:
        result = _run(["doctor", "--json"], cwd=None, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, f"Không chạy được 'npx hyperframes doctor': {exc}"

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, "doctor không trả JSON hợp lệ — kiểm tra cài đặt Node/npx"

    checks = {c["name"]: c for c in data.get("checks", [])}
    blocking = [name for name in ("Node.js", "Version") if not checks.get(name, {}).get("ok")]
    if blocking:
        return False, f"Thiếu điều kiện chặn cứng: {', '.join(blocking)}"

    version = checks.get("Version", {}).get("detail", "?")
    for name, check in checks.items():
        if not check.get("ok") and name not in ("Node.js", "Version"):
            log.warn(f"HyperFrames doctor: {name} — {check.get('detail')}")
    return True, version


def resolution_preset(width: int, height: int) -> str:
    """Khung ngang → landscape (1920×1080), khung dọc → portrait (1080×1920).

    TDD §4.1 Done khi [RND-01]: chỉ hỗ trợ 16:9/9:16, méo/vuông chưa cần.
    """
    return "portrait" if height > width else "landscape"


def create_project(project_dir: Path, width: int, height: int, fps: int) -> tuple[int, int]:
    """Sinh project HyperFrames rỗng (idempotent) — trả (canvas_width, canvas_height).

    `npx hyperframes init` chỉ nhận preset khung hình, không nhận width/height
    tuỳ ý — width/height đầu vào ở đây dùng để CHỌN preset (landscape/portrait),
    canvas thật luôn đúng 1920×1080 hoặc 1080×1920 theo PRD [RND-01] Done khi.
    """
    if (project_dir / "hyperframes.json").exists():
        log.info(f"project HyperFrames đã có ở {project_dir.name}/, bỏ qua init")
        return _RESOLUTION_PRESETS[resolution_preset(width, height)]

    project_dir.parent.mkdir(parents=True, exist_ok=True)
    preset = resolution_preset(width, height)
    result = _run(
        [
            "init", project_dir.name,
            "--non-interactive", "--example", "blank", "--resolution", preset,
        ],
        cwd=project_dir.parent,
        timeout=120,
    )
    if result.returncode != 0:
        raise AIEditorError(
            f"Sinh project HyperFrames thất bại: {result.stderr.strip()[-400:]}",
            suggestion="Chạy 'npx hyperframes doctor --json' để kiểm môi trường",
        )
    log.info(f"đã sinh project HyperFrames ({preset}) tại {project_dir.name}/")
    return _RESOLUTION_PRESETS[preset]


def build_video_track(
    project_dir: Path,
    source_rel_path: str,
    segments: list[tuple[float, float]],
    canvas_width: int,
    canvas_height: int,
    fps: int,
) -> float:
    """Ghi các đoạn giữ lại thành clip nối tiếp trên timeline — lớp 1 (§6.1).

    Mỗi đoạn (lo, hi) trong `segments` là khoảng THEO GIÂY TRÊN FILE NGUỒN cần
    giữ (đã tính từ cut_plan qua lib.timeline.kept_segments). `data-media-start`
    trỏ vào nguồn, `data-start` trên clip là vị trí TRÊN TIMELINE ĐẦU RA —
    hai trục thời gian khác nhau, không được lẫn.

    Trả tổng thời lượng (giây) — dùng để đặt data-duration của root.
    """
    if not segments:
        raise AIEditorError(
            "Không có đoạn nào để dựng — cut_plan xoá sạch video",
            suggestion="Mở lại python review.py cut và bỏ bớt điểm cắt",
        )

    index_html = project_dir / "index.html"
    html = index_html.read_text(encoding="utf-8")

    # Full-bleed bắt buộc: <video> mặc định trôi theo document flow, không tự
    # phủ kín canvas — thiếu style này thì khung hình dựng ra toàn màu đen dù
    # HyperFrames check/render đều báo thành công (không phải lỗi lint bắt được).
    video_style = (
        f"position:absolute;inset:0;width:{canvas_width}px;height:{canvas_height}px;"
        "object-fit:cover"
    )

    cursor = 0.0
    video_tags: list[str] = []
    audio_tags: list[str] = []
    for i, (lo, hi) in enumerate(segments):
        duration = round(hi - lo, 3)
        video_tags.append(
            f'      <video id="seg-{i:03d}" src="{source_rel_path}" style="{video_style}" '
            f'data-start="{cursor}" data-duration="{duration}" '
            f'data-media-start="{lo}" data-track-index="0" muted playsinline></video>'
        )
        audio_tags.append(
            f'      <audio id="seg-{i:03d}-audio" src="{source_rel_path}" '
            f'data-start="{cursor}" data-duration="{duration}" '
            f'data-media-start="{lo}" data-track-index="10" data-volume="1"></audio>'
        )
        cursor = round(cursor + duration, 3)

    clips_html = "\n".join(video_tags) + "\n" + "\n".join(audio_tags) + "\n" + CLIPS_MARKER
    marker = (
        "      <!--\n"
        "        Add your clips here. Example:\n"
        '        <div id="title" class="clip" data-start="0" data-duration="5" data-track-index="1"\n'
        '             style="font-size: 64px; color: #fff; padding: 40px">\n'
        "          Hello World\n"
        "        </div>\n"
        "      -->"
    )
    if marker not in html:
        raise AIEditorError(
            "index.html của project HyperFrames không đúng khung mẫu 'blank' — "
            "có thể đã bị sửa tay trước đó",
            suggestion="Xoá thư mục hf/ rồi chạy lại để sinh project mới",
        )
    html = html.replace(marker, clips_html)

    # Scaffold "blank" không tự cấp CSS cho #root (data-width/height chỉ là
    # thuộc tính máy đọc, không tự sinh box). Thiếu position:relative + kích
    # thước pixel thật thì <video absolute> không có ngữ cảnh định vị đúng —
    # `npx hyperframes check` KHÔNG bắt được lỗi này, chỉ soi khung mới thấy.
    root_css = (
        "      #root {\n"
        "        position: relative;\n"
        f"        width: {canvas_width}px;\n"
        f"        height: {canvas_height}px;\n"
        "        overflow: hidden;\n"
        "        background: #000;\n"
        "      }"
    )
    html = html.replace("    </style>", root_css + "\n    </style>")

    html = html.replace(
        f'data-duration="10"\n      data-width="{canvas_width}"',
        f'data-duration="{cursor}"\n      data-width="{canvas_width}"',
    )

    index_html.write_text(html, encoding="utf-8")
    log.info(f"đã ghi {len(segments)} đoạn video vào timeline, tổng {cursor}s")
    return cursor


def build_caption_track(project_dir: Path, caption_plan: dict, style, canvas_width: int, canvas_height: int) -> int:
    """Lớp 4 — caption karaoke, viết THẲNG vào timeline chính (không phải sub-comp).

    Lý do không dùng sub-composition (data-composition-src): việc mount sub-comp
    do CHÍNH CLI HyperFrames xử lý lúc render/preview, không chạy khi mở
    index.html thẳng trong trình duyệt — mà `checks/check_caption_timing.py`
    (Playwright) cần mở thẳng file để seek + đọc DOM. Viết trực tiếp vào
    timeline chính (`window.__timelines[<id>]`) tránh phụ thuộc đó hoàn toàn.

    Mỗi dòng caption là 1 `class="clip"` (data-start/data-duration tự động
    ẩn/hiện — KHÔNG tween opacity trên chính clip, luật cứng §6.1/determinism).
    Trong dòng, mỗi từ là 1 `<span>` màu mờ tĩnh; timeline CHÍNH chỉ thêm
    `tl.set(...)` đổi màu từng từ đúng lúc — karaoke highlight.

    TDD: §5.3, §6.1 · Trả tổng số dòng đã ghi.
    """
    index_html = project_dir / "index.html"
    html = index_html.read_text(encoding="utf-8")

    match = re.search(r'data-composition-id="([^"]+)"', html)
    if not match:
        raise AIEditorError("Không tìm thấy data-composition-id trong index.html")
    comp_id = match.group(1)

    if CLIPS_MARKER not in html:
        raise AIEditorError(
            "Không tìm thấy điểm chèn clip trong index.html",
            suggestion="Chạy lại build_video_track trước build_caption_track",
        )
    timeline_marker = f'window.__timelines["{comp_id}"] = tl;'
    if timeline_marker not in html:
        raise AIEditorError("Không tìm thấy dòng đăng ký timeline trong index.html")

    lines = caption_plan.get("lines", [])
    lines_html = "\n".join(_caption_line_html(line, style) for line in lines)
    set_calls = "\n".join(
        call for line in lines for call in _caption_word_set_calls(line, style)
    )
    orientation = "portrait" if canvas_height > canvas_width else "landscape"
    css = _caption_css(style, orientation, canvas_width, canvas_height)

    html = html.replace(CLIPS_MARKER, lines_html + "\n" + CLIPS_MARKER)
    html = html.replace("    </style>", css + "\n    </style>")
    html = html.replace(timeline_marker, set_calls + "\n      " + timeline_marker)

    index_html.write_text(html, encoding="utf-8")
    log.info(f"đã ghi {len(lines)} dòng caption vào lớp 4 (mode={caption_plan.get('mode')})")
    return len(lines)


def _caption_line_html(line: dict, style) -> str:
    words_html = "".join(
        f'<span id="{line["id"]}_w{i}" class="cap-word'
        + (' cap-word--emphasis"' if word_id in line.get("emphasis_word_ids", []) else '"')
        + f'>{escape_html(text)} </span>'
        for i, (word_id, text) in enumerate(zip(line["word_ids"], line["text"].split(" ")))
    )
    duration = round(line["t_end"] - line["t_start"], 3)
    return (
        f'      <div id="{line["id"]}" class="clip cap-line" '
        f'data-start="{line["t_start"]}" data-duration="{duration}" '
        f'data-track-index="{CAPTION_TRACK_INDEX}">{words_html}</div>'
    )


def _caption_word_set_calls(line: dict, style) -> list[str]:
    emphasis = set(line.get("emphasis_word_ids", []))
    calls = []
    words = line["text"].split(" ")
    starts = _word_starts_within_line(line)
    for i, word_id in enumerate(line["word_ids"]):
        if i >= len(words) or i >= len(starts):
            continue
        color = style.color.emphasis if word_id in emphasis else style.color.active
        calls.append(f'      tl.set("#{line["id"]}_w{i}", {{ color: "{color}" }}, {starts[i]});')
    return calls


def _word_starts_within_line(line: dict) -> list[float]:
    """`lib.caption_group.to_caption_lines` luôn ghi `word_starts` thật (mốc lời
    nói thật của từng từ) — chia đều thời lượng dòng chỉ dùng khi thiếu trường
    này (plan cũ/ghi tay), sai lệch lúc đó KHÔNG đạt trần 150ms của Done khi."""
    if "word_starts" in line:
        return line["word_starts"]
    count = max(1, len(line["word_ids"]))
    span = (line["t_end"] - line["t_start"]) / count
    return [round(line["t_start"] + i * span, 3) for i in range(count)]


def _caption_css(style, orientation: str, canvas_width: int, canvas_height: int) -> str:
    font_size = style.size.portrait_px if orientation == "portrait" else style.size.landscape_px
    max_chars = (
        style.layout.max_chars_per_line_portrait
        if orientation == "portrait"
        else style.layout.max_chars_per_line_landscape
    )
    bottom_px = round(canvas_height * style.layout.bottom_margin_percent / 100)
    font_family = resolve_embeddable_font(style)
    return (
        "      .cap-line {\n"
        "        position: absolute;\n"
        # `left:0; right:0; margin:auto` — KHÔNG dùng `left:50%; transform:
        # translateX(-50%)`: với absolute + chỉ có `left`, CSS tính width theo
        # "available width" = khoảng trống từ `left` tới rìa containing block,
        # ở đây chỉ bằng 50% khung — `max-width` lớn hơn con số đó thì VÔ
        # NGHĨA, bị kẹp ở nửa khung bất kể giá trị đặt (kiểm bằng Playwright
        # thật: câu đúng sát trần ký tự bị đẩy tràn thành 4 dòng thay vì 2).
        # Có cả `left` và `right` thì available width = TRỌN khung, `margin:
        # auto` mới canh giữa đúng theo `width: fit-content` thật sự.
        "        left: 0;\n"
        "        right: 0;\n"
        "        margin-left: auto;\n"
        "        margin-right: auto;\n"
        f"        bottom: {bottom_px}px;\n"
        "        width: fit-content;\n"
        f"        max-width: {max_chars}ch;\n"
        "        text-align: center;\n"
        f'        font-family: "{font_family}", sans-serif;\n'
        f"        font-size: {font_size}px;\n"
        f"        font-weight: {style.font.weight_normal};\n"
        "        line-height: 1.3;\n"
        "      }\n"
        "      .cap-word {\n"
        f"        color: {style.color.dim};\n"
        "      }\n"
        "      .cap-word--emphasis {\n"
        f"        font-weight: {style.font.weight_emphasis};\n"
        "      }"
    )


# 18 font HyperFrames nhúng sẵn (data URI, không gọi mạng) — xác minh thật
# bằng `npx hyperframes check` (16/08/2026): "Be Vietnam Pro" cấu hình trong
# caption_style.json KHÔNG nằm trong danh sách này → lint chặn render với lỗi
# font_family_without_font_face. Đây là bảng cứng để nhận biết TRƯỚC khi build
# thay vì dựng ra bản vỡ dấu rồi mới phát hiện qua check thất bại.
_EMBEDDABLE_FONTS = frozenset({
    "inter", "roboto", "open sans", "lato", "nunito", "montserrat", "poppins",
    "outfit", "oswald", "league gothic", "archivo black", "playfair display",
    "eb garamond", "space mono", "ibm plex mono", "jetbrains mono",
    "source code pro", "noto sans jp",
})
_SAFE_FALLBACK_FONT = "Inter"  # cũng là font mặc định của khung 'blank' — đã kiểm chứng


def resolve_embeddable_font(style) -> str:
    """PRD [CAP] edge case: font thiếu → dùng font dự phòng đã kiểm chứng dấu
    tiếng Việt, báo rõ tên font thiếu — KHÔNG âm thầm dựng bản vỡ dấu."""
    candidates = [style.font.family, *style.font.fallbacks]
    for family in candidates:
        if family.strip().lower() in _EMBEDDABLE_FONTS:
            if family != style.font.family:
                log.warn(
                    f"Font '{style.font.family}' không được HyperFrames nhúng sẵn "
                    f"(offline, không gọi mạng) — dùng font dự phòng '{family}'"
                )
            return family
    log.warn(
        f"Không font nào trong {candidates} được HyperFrames nhúng sẵn "
        f"(offline, không gọi mạng) — dùng font dự phòng {_SAFE_FALLBACK_FONT}"
    )
    return _SAFE_FALLBACK_FONT


def add_overlay_layer(scene_id: str, html_path: Path, t_in: float, t_out: float) -> None:
    """Lớp 3 — đồ hoạ motion. Việc của [MGX-01]."""
    raise NotImplementedError("[MGX-01] — xem docs/TDD.md §5.5")


def add_cutaway_layer(scene_id: str, image: Path, t_in: float, t_out: float) -> None:
    """Lớp 2 — cutaway. Việc của [JMP-01]."""
    raise NotImplementedError("[JMP-01] — xem docs/TDD.md §5.4")


def write_variables(vars_dict: dict) -> None:
    """Đồng bộ MỘT CHIỀU plan → Variables (§6.5). Cấm đọc ngược. Việc của [MGX-01]."""
    raise NotImplementedError("[MGX-01] — xem docs/TDD.md §6.5")


def read_variables() -> dict:
    """CHỈ dùng cho checks/check_variables_sync.py. Việc của [MGX-01]."""
    raise NotImplementedError("[MGX-01] — xem docs/TDD.md §6.5")


def check(project_dir: Path) -> None:
    """Cổng bắt buộc trước preview/render — lint + runtime + layout + contrast."""
    result = _run(["check", "--json"], cwd=project_dir, timeout=180)
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        report = None

    if result.returncode != 0:
        detail = _summarize_check_errors(report) if report else result.stderr.strip()[-400:]
        raise AIEditorError(
            f"HyperFrames check thất bại: {detail}",
            suggestion=f"Xem chi tiết: cd {project_dir} && npx hyperframes check",
        )
    log.info("HyperFrames check: 0 lỗi chặn")


def _summarize_check_errors(report: dict) -> str:
    """Gom mọi finding severity=error từ các mục con (lint/runtime/layout/motion/contrast)."""
    messages = [
        f"[{section}] {finding.get('code')}: {finding.get('message')}"
        for section, part in report.items()
        if isinstance(part, dict)
        for finding in part.get("findings", [])
        if finding.get("severity") == "error"
    ]
    return "; ".join(messages) or "không rõ (chạy 'npx hyperframes check' để xem chi tiết)"


def render(project_dir: Path, out: Path, *, quality: str) -> Path:
    """Render TOÀN BỘ composition ra MP4. quality ∈ 'draft' | 'high'.

    [RND-01] bản mỏng: render nguyên video một lần, chưa chia khối tăng dần
    (§6.2/§6.3 — cần timeline caption/overlay để tìm điểm an toàn, các lớp đó
    thuộc [CAP-01]/[MGX-01], chưa tồn tại). Khung hash/manifest cắm ở
    steps/07_render.py, chưa có logic chọn nhiều khối.
    """
    if quality not in ("draft", "high"):
        raise AIEditorError(f"quality không hợp lệ: {quality} (chỉ nhận draft|high)")

    out.parent.mkdir(parents=True, exist_ok=True)
    result = _run(
        ["render", "--quality", quality, "--output", str(out.resolve())],
        cwd=project_dir,
        timeout=2400,
    )
    if result.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        raise AIEditorError(
            f"Render thất bại: {result.stderr.strip()[-400:]}",
            suggestion="Kiểm RAM trống và chạy lại — TDD §11.2",
        )
    log.info(f"render {quality} xong: {out} ({out.stat().st_size / 1e6:.1f}MB)")
    return out


def render_block(block_id: str, t_in: float, t_out: float, out: Path, quality: str) -> None:
    """Render một khối — phần render tăng dần của §6.2/§6.3. Chưa implement."""
    raise NotImplementedError("Render tăng dần theo khối — TDD §6.2, tuần 4")


def open_studio(project_dir: Path) -> str:
    """Mở HyperFrames Studio để tua xem trước khi render — PRD [RND-01] bước 4.

    `npx hyperframes preview` chạy server tương tác (không thoát), nên chạy nền
    và trả lại lệnh cho người dùng tự mở — giống review.py không tự động hoá
    việc xem bằng mắt.
    """
    log.info(f"Mở Studio bằng lệnh: cd {project_dir} && npx hyperframes preview")
    return f"cd {project_dir} && npx hyperframes preview"
