from backend.services.pdf_parser import normalize_whitespace


def test_normalize_whitespace() -> None:
    assert normalize_whitespace("Hello\n\nworld\tfrom   PDF") == "Hello world from PDF"
