from __future__ import annotations

import pytest

from m3u8_spider.utils.movie_url_import import read_records


def test_read_records_accepts_number_and_url_per_line(tmp_path) -> None:
    source = tmp_path / "records.txt"
    source.write_text(
        "# comment\nSNOS-234 https://jable.tv/videos/snos-234/\nMIDA-649 https://jable.tv/videos/mida-649/\n",
        encoding="utf-8",
    )

    assert read_records(source) == [
        ("SNOS-234", "https://jable.tv/videos/snos-234/"),
        ("MIDA-649", "https://jable.tv/videos/mida-649/"),
    ]


def test_read_records_rejects_duplicate_number(tmp_path) -> None:
    source = tmp_path / "records.txt"
    source.write_text(
        "SNOS-234 https://jable.tv/videos/snos-234/\nSNOS-234 https://example.com/\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="编号重复"):
        read_records(source)
