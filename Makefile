.PHONY: daemon batch-merge batch-merge-dry lint format clean install

daemon:
	uv run python -m cli.daemon

batch-merge-dry:
	uv run python -m cli.batch_merge --dry-run

batch-merge:
	uv run python -m cli.batch_merge

lint:
	uv run ruff check .

format:
	uv run ruff format .

install:
	uv pip install -e .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf .ruff_cache temp_playlist.m3u8 file_list.txt 2>/dev/null || true
