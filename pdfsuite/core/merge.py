"""Birden çok PDF'i (ve isteğe bağlı sayfa aralıklarını) tek dosyada birleştirme."""

from contextlib import ExitStack
from pathlib import Path

import pypdf

from .utils import (
    PdfToolError,
    ensure_output_dir,
    open_reader,
    parse_page_ranges,
    safe_output_path,
)


def merge(
    inputs: list[str | Path | tuple[str | Path, str]],
    output_dir: Path | None = None,
    output_name: str = "merged.pdf",
) -> Path:
    """Verilen PDF'leri sırayla birleştirir ve oluşan dosyanın yolunu döndürür.

    Her girdi ya yalın bir yol ya da ``(yol, "1-3,5")`` demetidir; demet halinde
    yalnızca belirtilen sayfalar alınır.
    """
    if not inputs:
        raise PdfToolError("error.merge_no_input")

    out_dir = ensure_output_dir(output_dir)
    writer = pypdf.PdfWriter()

    # Tüm reader'lar yazma bitene kadar açık kalmalı; ExitStack hepsini kapatır.
    with ExitStack() as stack:
        for item in inputs:
            match item:
                case (path, page_spec):
                    source = _enter(stack, path)
                    for idx in parse_page_ranges(page_spec, len(source.pages)):
                        writer.add_page(source.pages[idx])
                case path:
                    source = _enter(stack, path)
                    for page in source.pages:
                        writer.add_page(page)

        target = safe_output_path(output_name, out_dir)
        try:
            with target.open("wb") as fh:
                writer.write(fh)
        except OSError as exc:
            raise PdfToolError(
                "error.merge_write_failed", path=target, exc=exc
            ) from exc
        finally:
            writer.close()
    return target


def _enter(stack: ExitStack, path: str | Path) -> pypdf.PdfReader:
    """Bir PDF'i ``open_reader`` ile açıp ``stack``'e ekler; şifreliyse reddeder."""
    reader = stack.enter_context(open_reader(path))
    if reader.is_encrypted:
        raise PdfToolError("error.encrypted_merge", path=path)
    return reader
