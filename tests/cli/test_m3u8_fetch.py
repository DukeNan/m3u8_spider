"""cli/m3u8_fetch 单元测试"""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.m3u8_fetch import main, read_urls_from_file

PAGE_URL = "https://example.com/videos/a/"
OTHER_PAGE_URL = "https://example.com/videos/b/"
M3U8_URL = "https://example.com/media/playlist.m3u8"


class TestReadUrlsFromFile:
    """read_urls_from_file() 批量文件解析测试"""

    def test_skip_blank_and_comment_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "urls.txt"
        path.write_text(
            "\n".join(
                [
                    "# 注释行",
                    PAGE_URL,
                    "",
                    "   ",
                    f"  {OTHER_PAGE_URL}  ",
                    "#另一条注释",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        assert read_urls_from_file(path) == [PAGE_URL, OTHER_PAGE_URL]

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "urls.txt"
        path.write_text("", encoding="utf-8")
        assert read_urls_from_file(path) == []


class TestArgValidation:
    """page_url 与 --file 互斥校验测试"""

    def test_both_given_exits_1(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([PAGE_URL, "--file", "urls.txt"])
        assert exc_info.value.code == 1

    def test_neither_given_exits_1(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1

    def test_missing_file_exits_1(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--file", str(tmp_path / "not_exist.txt")])
        assert exc_info.value.code == 1


class TestSingleUrlMode:
    """单 URL 模式测试"""

    def test_success_prints_only_url_to_stdout(self, monkeypatch, capsys) -> None:
        monkeypatch.setattr("cli.m3u8_fetch.fetch_m3u8_from_page", lambda url: M3U8_URL)

        main([PAGE_URL])

        # stdout 仅含结果 URL，日志全部走 stderr
        assert capsys.readouterr().out == f"{M3U8_URL}\n"

    def test_not_found_exits_1(self, monkeypatch) -> None:
        monkeypatch.setattr("cli.m3u8_fetch.fetch_m3u8_from_page", lambda url: None)

        with pytest.raises(SystemExit) as exc_info:
            main([PAGE_URL])

        assert exc_info.value.code == 1

    def test_import_error_exits_1(self, monkeypatch) -> None:
        def raise_import_error(url: str) -> str:
            raise ImportError("需要 crawl4ai")

        monkeypatch.setattr(
            "cli.m3u8_fetch.fetch_m3u8_from_page", raise_import_error
        )

        with pytest.raises(SystemExit) as exc_info:
            main([PAGE_URL])

        assert exc_info.value.code == 1


class TestBatchMode:
    """批量模式测试"""

    def test_partial_success_writes_found_urls_to_output(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        def fake_fetch(url: str) -> str | None:
            return M3U8_URL if url == PAGE_URL else None

        monkeypatch.setattr("cli.m3u8_fetch.fetch_m3u8_from_page", fake_fetch)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(f"{PAGE_URL}\n{OTHER_PAGE_URL}\n", encoding="utf-8")
        output_file = tmp_path / "found.txt"

        main(["--file", str(urls_file), "--output", str(output_file)])

        assert output_file.read_text(encoding="utf-8") == f"{M3U8_URL}\n"

    def test_all_failed_exits_1(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setattr("cli.m3u8_fetch.fetch_m3u8_from_page", lambda url: None)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(f"{PAGE_URL}\n{OTHER_PAGE_URL}\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            main(["--file", str(urls_file)])

        assert exc_info.value.code == 1

    def test_no_valid_urls_in_file_exits_1(self, tmp_path: Path) -> None:
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("# 只有注释\n\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            main(["--file", str(urls_file)])

        assert exc_info.value.code == 1

    def test_exception_in_one_task_does_not_stop_batch(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        def fake_fetch(url: str) -> str | None:
            if url == PAGE_URL:
                raise RuntimeError("网络错误")
            return M3U8_URL

        monkeypatch.setattr("cli.m3u8_fetch.fetch_m3u8_from_page", fake_fetch)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(f"{PAGE_URL}\n{OTHER_PAGE_URL}\n", encoding="utf-8")

        # 第一条异常被吞掉继续，第二条成功 → 整体成功，不抛 SystemExit
        main(["--file", str(urls_file)])
