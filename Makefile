.PHONY: daemon batch-merge batch-merge-dry

daemon:
	uv run python -m cli.daemon

batch-merge-dry:
	uv run python -m cli.batch_merge --dry-run

batch-merge:
	uv run python -m cli.batch_merge