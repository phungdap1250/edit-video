"""Sinh HTML/CSS/GSAP cho 4 loại đồ hoạ motion — TDD §5.5.

Module THUẦN: chỉ trả chuỗi, không ghi file, không gọi HyperFrames CLI. Mỗi
`build_fragment()` trả nội dung BÊN TRONG của thẻ — lib/renderer.py chịu
trách nhiệm bọc `<div class="clip" id=... data-start=... data-duration=...>`
vì data-start/duration phụ thuộc NGỮ CẢNH (scene riêng luôn bắt đầu tại 0,
ghép vào timeline chính thì bắt đầu tại thời điểm thật).

Trường TEXT/SỐ dùng `data-var-text` (biến HyperFrames thật, TDD §6.5) thay vì
in cứng — sửa qua `tools.sync_variables` rồi render lại không cần build lại
DOM. `variables[]` trả về là khai báo `data-composition-variables` tương ứng.
"""

from __future__ import annotations

from html import escape as esc

_POSITION_RECTS = {
    "right_third": {"x": 0.62, "y": 0.06, "w": 0.34, "h": 0.55},
    "left_third": {"x": 0.04, "y": 0.06, "w": 0.34, "h": 0.55},
    "top_center": {"x": 0.18, "y": 0.04, "w": 0.64, "h": 0.30},
}
DEFAULT_POSITION = "right_third"


def resolve_rect(position: str | None) -> dict:
    return _POSITION_RECTS.get(position or DEFAULT_POSITION, _POSITION_RECTS[DEFAULT_POSITION])


def extract_variables(item: dict) -> dict[str, str]:
    """{var_id: giá trị hiện tại} — dùng bởi `tools.sync_variables` (TDD §6.5),
    KHÔNG cần dựng cả fragment chỉ để biết tên biến."""
    content, item_id = item["content"], item["id"]
    if item["type"] == "con_so_nhay":
        return {f"{item_id}__number": str(content["number"]), f"{item_id}__label": content.get("label", "")}
    if item["type"] == "pill_tu_khoa":
        return {f"{item_id}__text": content["text"]}
    if item["type"] == "card_khai_niem":
        return {f"{item_id}__title": content["title"], f"{item_id}__definition": content["definition"]}
    if item["type"] == "danh_sach_bung_dan":
        return {f"{item_id}__item{i}": entry["text"] for i, entry in enumerate(content["items"])}
    return {}


def box_style(item: dict, canvas_width: int, canvas_height: int) -> str:
    rect = resolve_rect(item.get("position"))
    return (
        "position:absolute;"
        f"left:{round(rect['x'] * canvas_width)}px;"
        f"top:{round(rect['y'] * canvas_height)}px;"
        f"width:{round(rect['w'] * canvas_width)}px;"
    )


def build_fragment(item: dict, frame, t_start: float) -> dict:
    """Trả {inner_html, css, tween_lines, variables} — nội dung BÊN TRONG khung
    `.ov-card` + khai báo biến cho các trường text/số của mục này.

    `item["_t_start"]` phải đã được set = mốc GSAP tuyệt đối để tween lên đúng
    lúc (khác `t_start` tham số dưới, vốn chỉ dùng để tính mốc list-reveal mặc
    định — hai giá trị trùng nhau khi gọi từ ngữ cảnh timeline chính, nhưng
    khác nhau khi dựng scene riêng luôn bắt đầu tại 0)."""
    builders = {
        "con_so_nhay": _number_pop,
        "danh_sach_bung_dan": _list_reveal,
        "card_khai_niem": _concept_card,
        "pill_tu_khoa": _keyword_pill,
    }
    return builders[item["type"]](item, frame, t_start)


def _card_css(frame, extra: str = "") -> str:
    # Giá trị này luôn được nhúng vào thuộc tính HTML style="..." (nháy KÉP) ở
    # nơi gọi — mọi ký tự " bên trong đây sẽ đóng attribute sớm và phá vỡ toàn
    # bộ style còn lại. font-family dùng nháy ĐƠN để tránh đúng lỗi đó.
    return (
        f"background:{frame.colors['paper']};color:{frame.colors['ink']};"
        f"border-radius:{frame.radius_px}px;"
        f"font-family:'{frame.font_family}',sans-serif;"
        f"box-shadow:0 4px 24px rgba(0,0,0,.18);{extra}"
    )


def _var_decl(var_id: str, label: str, default: str) -> dict:
    return {"id": var_id, "type": "string", "label": label, "default": default}


def _number_pop(item: dict, frame, t_start: float) -> dict:
    content = item["content"]
    box_id = f"{item['id']}_box"
    number_var, label_var = f"{item['id']}__number", f"{item['id']}__label"
    number_text = esc(str(content["number"]))
    label_text = esc(content.get("label", ""))
    card_css = _card_css(frame, "padding:28px 32px;text-align:center;")
    weight_bold, weight_normal = frame.font_weights[-1], frame.font_weights[0]
    accent = frame.colors["primary"]
    inner_html = (
        f'<div id="{box_id}" style="{card_css}">'
        f'<div data-var-text="{number_var}" style="font-size:64px;font-weight:{weight_bold};color:{accent}">{number_text}</div>'
        f'<div data-var-text="{label_var}" style="font-size:20px;font-weight:{weight_normal}">{label_text}</div>'
        "</div>"
    )
    css = f"#{box_id} {{ opacity: 0; transform: scale(0.3); }}"
    tween = [f'tl.fromTo("#{box_id}", {{ scale: 0.3, opacity: 0 }}, '
             f'{{ scale: 1, opacity: 1, duration: 0.45, ease: "back.out(1.7)" }}, {t_start});']
    variables = [_var_decl(number_var, "Con số", str(content["number"])),
                 _var_decl(label_var, "Nhãn", content.get("label", ""))]
    return {"inner_html": inner_html, "css": css, "tween_lines": tween, "variables": variables}


def _keyword_pill(item: dict, frame, t_start: float) -> dict:
    content = item["content"]
    box_id = f"{item['id']}_box"
    text_var = f"{item['id']}__text"
    text = esc(content["text"])
    pill_extra = f"padding:12px 24px;display:inline-block;background:{frame.colors['primary']};color:{frame.colors['paper']};"
    card_css = _card_css(frame, pill_extra)
    weight_bold = frame.font_weights[-1]
    inner_html = (
        f'<div id="{box_id}" style="{card_css}">'
        f'<span data-var-text="{text_var}" style="font-size:22px;font-weight:{weight_bold}">{text}</span>'
        "</div>"
    )
    css = f"#{box_id} {{ opacity: 0; transform: translateX(24px); }}"
    tween = [f'tl.fromTo("#{box_id}", {{ x: 24, opacity: 0 }}, '
             f'{{ x: 0, opacity: 1, duration: 0.3, ease: "power2.out" }}, {t_start});']
    variables = [_var_decl(text_var, "Từ khoá", content["text"])]
    return {"inner_html": inner_html, "css": css, "tween_lines": tween, "variables": variables}


def _concept_card(item: dict, frame, t_start: float) -> dict:
    content = item["content"]
    box_id = f"{item['id']}_box"
    title_var, def_var = f"{item['id']}__title", f"{item['id']}__definition"
    title = esc(content["title"])
    definition = esc(content["definition"])
    card_css = _card_css(frame, "padding:20px 24px;")
    weight_bold, weight_normal = frame.font_weights[-1], frame.font_weights[0]
    accent = frame.colors["primary"]
    inner_html = (
        f'<div id="{box_id}" style="{card_css}">'
        f'<div data-var-text="{title_var}" style="font-size:22px;font-weight:{weight_bold};color:{accent}">{title}</div>'
        f'<div data-var-text="{def_var}" style="font-size:16px;font-weight:{weight_normal};margin-top:6px">{definition}</div>'
        "</div>"
    )
    css = f"#{box_id} {{ opacity: 0; transform: scale(0.92); }}"
    tween = [f'tl.fromTo("#{box_id}", {{ scale: 0.92, opacity: 0 }}, '
             f'{{ scale: 1, opacity: 1, duration: 0.35, ease: "power2.out" }}, {t_start});']
    variables = [_var_decl(title_var, "Tiêu đề", content["title"]),
                 _var_decl(def_var, "Định nghĩa", content["definition"])]
    return {"inner_html": inner_html, "css": css, "tween_lines": tween, "variables": variables}


def _list_reveal(item: dict, frame, t_start: float) -> dict:
    content = item["content"]
    box_id = f"{item['id']}_box"
    weight_normal = frame.font_weights[0]
    rows, css_rows, tween, variables = [], [], [], []
    for i, entry in enumerate(content["items"]):
        row_id = f"{box_id}_i{i}"
        row_var = f"{item['id']}__item{i}"
        text = esc(entry["text"])
        rows.append(
            f'<div id="{row_id}" data-var-text="{row_var}" '
            f'style="font-size:18px;font-weight:{weight_normal};padding:6px 0">{text}</div>'
        )
        css_rows.append(f"#{row_id} {{ opacity: 0; transform: translateY(8px); }}")
        reveal_at = entry.get("_reveal_at_sec", t_start)
        tween.append(
            f'tl.fromTo("#{row_id}", {{ y: 8, opacity: 0 }}, '
            f'{{ y: 0, opacity: 1, duration: 0.25, ease: "power2.out" }}, {reveal_at});'
        )
        variables.append(_var_decl(row_var, f"Mục {i + 1}", entry["text"]))
    card_css = _card_css(frame, "padding:18px 22px;")
    inner_html = f'<div id="{box_id}" style="{card_css}">' + "".join(rows) + "</div>"
    return {"inner_html": inner_html, "css": "\n".join(css_rows), "tween_lines": tween, "variables": variables}
