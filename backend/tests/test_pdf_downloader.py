from pathlib import Path

from backend.services.pdf_downloader import download_pdf


def test_download_pdf_uses_cache_when_file_exists(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / ".cache"
    pdfs_dir = cache_dir / "pdfs"
    pdfs_dir.mkdir(parents=True)
    cached_file = pdfs_dir / "paper_1.pdf"
    cached_file.write_bytes(b"cached")

    monkeypatch.setenv("CACHE_DIR", str(cache_dir))

    path = download_pdf("https://example.org/paper.pdf", "paper 1")
    assert path == str(cached_file)


def test_download_pdf_saves_pdf_bytes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / ".cache"))

    class DummyResponse:
        status_code = 200
        headers = {"Content-Type": "application/pdf"}
        content = b"%PDF-1.4 fake"

        def raise_for_status(self) -> None:
            return

    monkeypatch.setattr("backend.services.pdf_downloader.requests.get", lambda *args, **kwargs: DummyResponse())

    path = download_pdf("https://example.org/paper.pdf", "paper-2")
    assert path is not None
    assert Path(path).exists()
    assert Path(path).read_bytes() == b"%PDF-1.4 fake"
