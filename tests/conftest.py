"""Test fikstürleri — test PDF'leri/görselleri test içinde üretilir."""

from pathlib import Path

import pymupdf
import pytest


def _make_pdf(
    path: Path,
    pages: int = 3,
    *,
    encrypt: bool = False,
    metadata: dict[str, str] | None = None,
) -> Path:
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 100), f"Sayfa {i + 1}")
    if metadata:
        doc.set_metadata(metadata)
    if encrypt:
        doc.save(
            path,
            encryption=pymupdf.PDF_ENCRYPT_RC4_128,
            owner_pw="o",
            user_pw="u",
        )
    else:
        doc.save(path)
    doc.close()
    return path


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    return _make_pdf(
        tmp_path / "sample.pdf",
        pages=3,
        metadata={"title": "Örnek", "author": "kaktusdev"},
    )


@pytest.fixture
def encrypted_pdf(tmp_path: Path) -> Path:
    return _make_pdf(tmp_path / "enc.pdf", pages=1, encrypt=True)


@pytest.fixture
def sample_images(tmp_path: Path) -> list[Path]:
    paths: list[Path] = []
    for i in range(2):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 100), f"img{i}")
        target = tmp_path / f"img{i}.png"
        page.get_pixmap().save(target)
        doc.close()
        paths.append(target)
    return paths


@pytest.fixture
def out_dir(tmp_path: Path) -> Path:
    """Her test için izole çıktı klasörü (./output kirlenmez)."""
    return tmp_path / "out"
