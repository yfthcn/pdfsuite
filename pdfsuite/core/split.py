"""PDF'i ayrı PDF dosyalarına ayırma (görsele çevirme DEĞİL — bkz. convert.py)."""

from pathlib import Path

import pypdf

from .utils import (
    PdfToolError,
    ensure_output_dir,
    open_reader,
    parse_page_ranges,
    resolve_input,
    safe_output_path,
)


def split(
    pdf_path: str | Path,
    output_dir: Path | None = None,
    pages: str | None = None,
) -> list[Path]:
    """PDF'i ayrı PDF dosyalarına böler ve oluşan yolların listesini döndürür.

    ``pages`` ``None`` ise her sayfa kendi dosyasına; ``"1-3,5"`` verilirse
    yalnızca seçili sayfalar tek tek dosyalara yazılır.
    """
    path = resolve_input(pdf_path)

    with open_reader(path) as reader:
        if reader.is_encrypted:
            raise PdfToolError("error.encrypted_split", path=path)

        total = len(reader.pages)
        if total == 0:
            raise PdfToolError("error.empty_pdf", path=path)

        indices = parse_page_ranges(pages, total) if pages else list(range(total))

        out_dir = ensure_output_dir(output_dir)
        stem = path.stem
        written: list[Path] = []
        for idx in indices:
            writer = pypdf.PdfWriter()
            writer.add_page(reader.pages[idx])
            target = safe_output_path(f"{stem}_page_{idx + 1}.pdf", out_dir)
            try:
                with target.open("wb") as fh:
                    writer.write(fh)
            except OSError as exc:
                raise PdfToolError(
                    "error.page_write_failed", path=target, exc=exc
                ) from exc
            finally:
                writer.close()
            written.append(target)
        return written
