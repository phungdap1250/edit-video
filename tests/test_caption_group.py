"""lib.caption_group — gom dòng caption karaoke — TDD §5.3."""

from __future__ import annotations

from lib import caption_group
from lib.config import Section

STYLE = Section({
    "mode_auto": {"word_pop_if_vertical_and_under_sec": 120},
    "timing": {"max_linger_after_speech_ms": 1000, "min_display_ms": 500},
})


def w(wid, text, start, end):
    return {"id": wid, "text": text, "start": start, "end": end}


def test_build_kept_words_bo_tu_bi_cat():
    transcript_words = [{"id": "w1", "text": "a"}, {"id": "w2", "text": "b"}]
    timeline_map = {"w1": (0.0, 0.5)}  # w2 đã bị cắt, không có trong map
    kept = caption_group.build_kept_words(transcript_words, timeline_map)
    assert [k["id"] for k in kept] == ["w1"]


def test_group_lines_ngat_o_dau_cau():
    words = [w("w1", "Xin", 0.0, 0.3), w("w2", "chào.", 0.3, 0.6), w("w3", "Tạm", 1.0, 1.3), w("w4", "biệt", 1.3, 1.6)]
    groups = caption_group.group_lines(words, char_budget=80)
    assert [[x["id"] for x in g] for g in groups] == [["w1", "w2"], ["w3", "w4"]]


def test_group_lines_ngat_o_khoang_lang():
    words = [w("w1", "a", 0.0, 0.3), w("w2", "b", 1.0, 1.3)]  # gap 700ms >= 300ms
    groups = caption_group.group_lines(words, char_budget=80)
    assert len(groups) == 2


def test_group_lines_khong_bao_gio_ngat_giua_tu():
    """Budget nhỏ hơn 1 từ vẫn không được cắt ký tự trong từ đó."""
    words = [w("w1", "supercalifragilistic", 0.0, 1.0)]
    groups = caption_group.group_lines(words, char_budget=5)
    assert groups == [[words[0]]]


def test_group_lines_vuot_budget_thi_ngat_som():
    words = [w("w1", "aaaa", 0.0, 0.3), w("w2", "bbbb", 0.4, 0.7), w("w3", "cccc", 0.8, 1.1)]
    groups = caption_group.group_lines(words, char_budget=9)  # "aaaa bbbb" = 9 ký tự vừa khít
    ids = [[x["id"] for x in g] for g in groups]
    assert ids == [["w1", "w2"], ["w3"]]


def test_group_words_pop_toi_da_3_tu():
    words = [w(f"w{i}", "x", i * 0.2, i * 0.2 + 0.1) for i in range(7)]
    groups = caption_group.group_words_pop(words, max_words=3)
    assert [len(g) for g in groups] == [3, 3, 1]


def test_choose_mode_doc_ngan_thi_word_pop():
    assert caption_group.choose_mode(STYLE, "portrait", 60) == "word_pop"


def test_choose_mode_doc_dai_thi_karaoke():
    assert caption_group.choose_mode(STYLE, "portrait", 200) == "karaoke_word"


def test_choose_mode_ngang_luon_karaoke():
    assert caption_group.choose_mode(STYLE, "landscape", 30) == "karaoke_word"


def test_to_caption_lines_min_display_keo_dai():
    words = [w("w1", "a", 0.0, 0.1)]  # tự nhiên chỉ dài 0.1s < min_display 0.5s
    lines = caption_group.to_caption_lines([words], STYLE, max_chars_per_line=80)
    assert lines[0]["t_end"] - lines[0]["t_start"] == 0.5


def test_to_caption_lines_khong_de_de_len_dong_sau():
    group_a = [w("w1", "a", 0.0, 0.1)]
    group_b = [w("w2", "b", 0.3, 0.6)]
    lines = caption_group.to_caption_lines([group_a, group_b], STYLE, max_chars_per_line=80)
    assert lines[0]["t_end"] <= lines[1]["t_start"]


def test_to_caption_lines_word_starts_la_moc_that():
    words = [w("w1", "a", 1.0, 1.2), w("w2", "b", 1.3, 1.5)]
    lines = caption_group.to_caption_lines([words], STYLE, max_chars_per_line=80)
    assert lines[0]["word_starts"] == [1.0, 1.3]


def test_to_caption_lines_khong_gan_emphasis():
    words = [w("w1", "a", 0.0, 0.5)]
    lines = caption_group.to_caption_lines([words], STYLE, max_chars_per_line=80)
    assert lines[0]["emphasis_word_ids"] == []


def test_line_break_after_vua_1_dong_thi_none():
    words = [w("w1", "ab", 0, 1), w("w2", "cd", 1, 2)]
    lines = caption_group.to_caption_lines([words], STYLE, max_chars_per_line=10)
    assert lines[0]["line_break_after"] is None


def test_line_break_after_tinh_dung_diem_ngat():
    words = [w("w1", "aaaa", 0, 1), w("w2", "bbbb", 1, 2), w("w3", "cccc", 2, 3)]
    # "aaaa bbbb" = 9 ký tự <= 9, thêm " cccc" -> 14 > 9 => ngắt sau từ chỉ số 1
    lines = caption_group.to_caption_lines([words], STYLE, max_chars_per_line=9)
    assert lines[0]["line_break_after"] == 1
