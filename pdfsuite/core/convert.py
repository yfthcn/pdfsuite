"""PDF <-> görsel dönüşümleri (PyMuPDF ile).

Görsele çevirme, sayfa ayırmadan AYRIDIR: burada PDF sayfaları PNG/JPG/WEBP
olur; ``split.py`` ise ayrı PDF üretir.
"""

from io import BytesIO
from pathlib import Path

import pypdf
import pymupdf

from .utils import (
    PdfToolError,
    ensure_output_dir,
    is_pdf,
    parse_page_ranges,
    resolve_input,
    safe_output_path,
)

_IMAGE_FORMATS = {"png", "jpg", "jpeg", "webp"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
_MAX_DPI = 1200  # bellek patlamasına karşı üst sınır (devasa pixmap engellenir)


def pdf_to_images(
    pdf_path: str | Path,
    output_dir: Path | None = None,
    fmt: str = "png",
    dpi: int = 150,
    pages: str | None = None,
) -> list[Path]:
    """PDF sayfalarını görsele çevirir ve oluşan dosya yollarını döndürür.

    ``fmt``: ``png`` | ``jpg`` | ``webp``. ``pages`` ``None`` ise tüm sayfalar.
    """
    fmt_norm = fmt.lower().lstrip(".")
    if fmt_norm not in _IMAGE_FORMATS:
        raise PdfToolError("error.unsupported_image_format", fmt=fmt)
    if dpi <= 0:
        raise PdfToolError("error.dpi_not_positive", dpi=dpi)
    if dpi > _MAX_DPI:
        raise PdfToolError("error.dpi_too_high", max=_MAX_DPI, dpi=dpi)

    path = resolve_input(pdf_path)
    if not is_pdf(path):
        raise PdfToolError("error.invalid_pdf", path=path)

    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        raise PdfToolError("error.pdf_open_failed", path=path, exc=exc) from exc

    try:
        if doc.needs_pass:
            raise PdfToolError("error.encrypted_convert", path=path)

        total = doc.page_count
        if total == 0:
            raise PdfToolError("error.empty_pdf", path=path)
        indices = parse_page_ranges(pages, total) if pages else list(range(total))

        out_dir = ensure_output_dir(output_dir)
        stem = path.stem
        ext = "jpg" if fmt_norm == "jpeg" else fmt_norm
        matrix = pymupdf.Matrix(dpi / 72, dpi / 72)

        written: list[Path] = []
        for idx in indices:
            pixmap = doc.load_page(idx).get_pixmap(matrix=matrix)
            target = safe_output_path(f"{stem}_page_{idx + 1}.{ext}", out_dir)
            try:
                # png/jpg PyMuPDF ile native; webp Pillow üzerinden.
                if ext == "webp":
                    _save_webp(pixmap, target)
                else:
                    pixmap.save(target)
            except PdfToolError:
                raise
            except Exception as exc:
                raise PdfToolError(
                    "error.image_write_failed", path=target, exc=exc
                ) from exc
            written.append(target)
        return written
    finally:
        doc.close()


def images_to_pdf(
    image_paths: list[str | Path],
    output_dir: Path | None = None,
    output_name: str = "output.pdf",
) -> Path:
    """Verilen görselleri sırayla tek bir PDF'e dönüştürür ve yolunu döndürür."""
    if not image_paths:
        raise PdfToolError("error.images_no_input")

    out_dir = ensure_output_dir(output_dir)
    writer = pypdf.PdfWriter()

    for raw in image_paths:
        image = resolve_input(raw)
        if image.suffix.lower() not in _IMAGE_SUFFIXES:
            raise PdfToolError("error.unsupported_image", path=image)
        try:
            with pymupdf.open(image) as img_doc:
                pdf_bytes = img_doc.convert_to_pdf()
        except Exception as exc:
            raise PdfToolError("error.image_failed", path=image, exc=exc) from exc
        page_doc = pypdf.PdfReader(BytesIO(pdf_bytes))
        try:
            for page in page_doc.pages:
                writer.add_page(page)
        finally:
            page_doc.close()

    target = safe_output_path(output_name, out_dir)
    try:
        with target.open("wb") as fh:
            writer.write(fh)
    except OSError as exc:
        raise PdfToolError("error.pdf_write_failed", path=target, exc=exc) from exc
    finally:
        writer.close()
    return target


def _save_webp(pixmap: pymupdf.Pixmap, target: Path) -> None:
    """PyMuPDF webp yazamaz; pikselleri Pillow'a verip webp olarak kaydeder."""
    from PIL import Image

    mode = "RGBA" if pixmap.alpha else "RGB"
    image = Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)
    image.save(target, format="WEBP")


# DOCX -> PDF dönüşümü v1'de YOK. v2'de (opsiyonel LibreOffice bağımlılığıyla)
# buraya eklenecek:
#   def docx_to_pdf(docx_path: str | Path, output_dir: Path | None = None) -> Path: ...
