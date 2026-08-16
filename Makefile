PY := python

.PHONY: help setup dirs vendor status check check-fast check-arch test clean

help:
	@echo "make setup       — cài phụ thuộc Python"
	@echo "make vendor      — tải Alpine.js vào web/static/"
	@echo "make status      — in bảng trạng thái project.json"
	@echo "make check       — 11 script nghiệm thu (TDD §12.1)"
	@echo "make check-fast  — bỏ script cần render"
	@echo "make check-arch  — 5 script kiểm kiến trúc (TDD §12.2)"
	@echo "make test        — pytest"
	@echo "make clean       — xoá work/ và out/ (source/ và plans/ nguyên vẹn)"

RUNTIME_DIRS := source work/blocks work/generated_images assets hf/scenes plans .draft logs out

setup: dirs
	$(PY) -m pip install -r requirements.txt

# Thư mục runtime nằm ngoài git (TDD §13.6) — clone về là chưa có, tạo lại ở đây
dirs:
	@mkdir -p $(RUNTIME_DIRS)

vendor:
	curl -fsSL https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js -o web/static/alpine.min.js

status:
	$(PY) -m tools.status

# ── Nghiệm thu ────────────────────────────────────────────────────
CHECKS_ARCH := check_block_hash check_renderer_isolation check_no_hardcode \
               check_no_silent_except check_no_bind_all check_no_secrets

CHECKS_FAST := check_anchor_integrity check_frame_rules check_layout \
               check_variables_sync

CHECKS_RENDER := check_wer check_cut_coverage check_av_sync check_caption_timing \
                 check_vietnamese_glyphs check_storyboard_fidelity check_block_boundary

check-arch:
	@for c in $(CHECKS_ARCH); do echo "── $$c"; $(PY) -m checks.$$c || exit 1; done

check-fast: check-arch
	@for c in $(CHECKS_FAST); do echo "── $$c"; $(PY) -m checks.$$c || exit 1; done

check: check-fast
	@for c in $(CHECKS_RENDER); do echo "── $$c"; $(PY) -m checks.$$c || exit 1; done

test:
	$(PY) -m pytest -q

clean:
	rm -rf work/blocks/* work/generated_images/* work/*.mp4 work/*.m4a out/*
	@echo "Đã dọn work/ và out/ — source/ và plans/ nguyên vẹn"
