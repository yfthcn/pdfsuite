"""API hata yolu testleri: beklenmeyen istisna sunucuda loglanır, istemciye sızmaz."""

import logging

import pytest
from fastapi.testclient import TestClient

import pdfsuite.api.server as server


@pytest.fixture
def client() -> TestClient:
    # raise_server_exceptions=False -> beklenmeyen hata 500 yanıtına dönüşsün.
    return TestClient(server.app, raise_server_exceptions=False)


def test_unexpected_error_logged_but_not_leaked(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # get_info'yu beklenmeyen (PdfToolError OLMAYAN) bir hata fırlatacak şekilde değiştir.
    def boom(_path: object) -> dict:
        raise ValueError("patladi-12345")

    monkeypatch.setattr(server, "get_info", boom)

    files = {"file": ("x.pdf", b"%PDF-1.7 fake", "application/pdf")}
    with caplog.at_level(logging.ERROR, logger="pdfsuite.api"):
        resp = client.post("/info?lang=en", files=files)

    # İstemci: çevrilmiş genel mesaj, traceback YOK, iç ayrıntı (dosya/satır) sızmaz.
    assert resp.status_code == 500
    body = resp.text
    detail = resp.json()["detail"]
    assert detail == "Unexpected error: patladi-12345"
    assert "Traceback (most recent call last)" not in body
    assert "ValueError" not in body
    assert "server.py" not in body

    # Sunucu logu: tam traceback burada görünmeli.
    assert "Traceback (most recent call last)" in caplog.text
    assert "ValueError: patladi-12345" in caplog.text
    assert any(r.exc_info for r in caplog.records)


def test_pdftoolerror_still_translated_400(client: TestClient) -> None:
    # Bilinen hata (PdfToolError) yolu bozulmamış olmalı: çevrilmiş 400.
    files = {"file": ("x.pdf", b"not a pdf", "application/pdf")}
    resp = client.post("/info?lang=tr", files=files)
    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("Geçerli bir PDF değil")
