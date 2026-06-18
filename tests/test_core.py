"""core katmanı uçtan uca testleri."""

import json
from pathlib import Path

import pytest

from pdfsuite.core import (
    PdfToolError,
    export_info,
    get_info,
    images_to_pdf,
    merge,
    pdf_to_images,
    split,
)


# --- info ----------------------------------------------------------------
def test_get_info(sample_pdf: Path) -> None:
    info = get_info(sample_pdf)
    assert info["page_count"] == 3
    assert info["encrypted"] is False
    assert info["title"] == "Örnek"
    assert info["author"] == "kaktusdev"
    assert len(info["page_sizes"]) == 3
    assert info["pdf_version"]


def test_export_info(sample_pdf: Path, out_dir: Path) -> None:
    path = export_info(sample_pdf, out_dir)
    assert path.exists() and path.suffix == ".json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["page_count"] == 3


def test_invalid_pdf_rejected(tmp_path: Path) -> None:
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"not a pdf")
    with pytest.raises(PdfToolError) as ei:
        get_info(fake)
    assert ei.value.key == "error.invalid_pdf"


# --- merge ---------------------------------------------------------------
def test_merge_basic(sample_pdf: Path, out_dir: Path) -> None:
    result = merge([sample_pdf, sample_pdf], out_dir)
    assert get_info(result)["page_count"] == 6


def test_merge_page_ranges(sample_pdf: Path, out_dir: Path) -> None:
    result = merge([(sample_pdf, "1,3")], out_dir)
    assert get_info(result)["page_count"] == 2


# --- split ---------------------------------------------------------------
def test_split_all(sample_pdf: Path, out_dir: Path) -> None:
    parts = split(sample_pdf, out_dir)
    assert len(parts) == 3
    assert all(p.exists() for p in parts)


def test_split_range(sample_pdf: Path, out_dir: Path) -> None:
    parts = split(sample_pdf, out_dir, pages="2-3")
    assert len(parts) == 2


# --- convert -------------------------------------------------------------
@pytest.mark.parametrize("fmt", ["png", "jpg", "webp"])
def test_pdf_to_images(sample_pdf: Path, out_dir: Path, fmt: str) -> None:
    imgs = pdf_to_images(sample_pdf, out_dir, fmt=fmt, dpi=72, pages="1")
    assert len(imgs) == 1
    assert imgs[0].suffix == f".{fmt}"
    assert imgs[0].exists() and imgs[0].stat().st_size > 0


def test_images_to_pdf(sample_images: list[Path], out_dir: Path) -> None:
    result = images_to_pdf(sample_images, out_dir)
    assert get_info(result)["page_count"] == 2


def test_dpi_too_high_rejected(sample_pdf: Path, out_dir: Path) -> None:
    with pytest.raises(PdfToolError) as ei:
        pdf_to_images(sample_pdf, out_dir, dpi=5000)
    # Anahtar + biçimlendirme parametreleri taşınır (çeviri arayüzde yapılır).
    assert ei.value.key == "error.dpi_too_high"
    assert ei.value.params == {"max": 1200, "dpi": 5000}


def test_dpi_nonpositive_rejected(sample_pdf: Path, out_dir: Path) -> None:
    with pytest.raises(PdfToolError) as ei:
        pdf_to_images(sample_pdf, out_dir, dpi=0)
    assert ei.value.key == "error.dpi_not_positive"


# --- çakışma adlandırma --------------------------------------------------
def test_conflict_suffix(sample_pdf: Path, out_dir: Path) -> None:
    a = merge([sample_pdf], out_dir, "m.pdf")
    b = merge([sample_pdf], out_dir, "m.pdf")
    c = merge([sample_pdf], out_dir, "m.pdf")
    assert (a.name, b.name, c.name) == ("m.pdf", "m_1.pdf", "m_2.pdf")


# --- şifreli PDF ---------------------------------------------------------
def test_encrypted_info_no_crash(encrypted_pdf: Path) -> None:
    info = get_info(encrypted_pdf)
    assert info["encrypted"] is True
    assert info["page_count"] is None
    assert info["page_sizes"] == []


def test_encrypted_split_rejected(encrypted_pdf: Path, out_dir: Path) -> None:
    with pytest.raises(PdfToolError) as ei:
        split(encrypted_pdf, out_dir)
    assert ei.value.key == "error.encrypted_split"


def test_encrypted_merge_rejected(encrypted_pdf: Path, out_dir: Path) -> None:
    with pytest.raises(PdfToolError) as ei:
        merge([encrypted_pdf], out_dir)
    assert ei.value.key == "error.encrypted_merge"


# --- path traversal ------------------------------------------------------
@pytest.mark.parametrize("bad", ["../escape.pdf", "/tmp/escape.pdf", "../../etc/x.pdf"])
def test_traversal_reduced_to_basename(
    sample_pdf: Path, out_dir: Path, bad: str
) -> None:
    result = merge([sample_pdf], out_dir, bad).resolve()
    # Ad dosya adına indirgenmeli ve sonuç out_dir içinde kalmalı.
    assert result.parent == out_dir.resolve()


@pytest.mark.parametrize("bad", ["", ".", ".."])
def test_invalid_output_name_rejected(
    sample_pdf: Path, out_dir: Path, bad: str
) -> None:
    with pytest.raises(PdfToolError) as ei:
        merge([sample_pdf], out_dir, bad)
    assert ei.value.key == "error.bad_output_name"
