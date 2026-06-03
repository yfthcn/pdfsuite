"""PDF üstveri ve sayfa bilgisi okuma."""

import json
from pathlib import Path

from .utils import (
    PdfToolError,
    ensure_output_dir,
    open_reader,
    resolve_input,
    safe_output_path,
)


def get_info(pdf_path: str | Path) -> dict:
    """PDF hakkında özet bilgi döndürür.

    Sayfa sayısı, başlık, yazar, tarih, şifreli mi, sayfa boyutları,
    dosya boyutu ve PDF sürümünü içerir. Şifreli PDF reddedilmez; ``encrypted``
    True, ``page_count`` ve ``page_sizes`` ise okunamadığından ``None``/boş döner.
    """
    path = resolve_input(pdf_path)

    with open_reader(path) as reader:
        encrypted = reader.is_encrypted
        meta = reader.metadata if not encrypted else None
        version = _pdf_version(reader.pdf_header)

        # Şifreli dosyada sayfalara erişmek çözme gerektirir; çökmeden raporla.
        page_sizes: list[dict[str, float]] = []
        page_count: int | None = None
        if not encrypted:
            page_count = len(reader.pages)
            for page in reader.pages:
                box = page.mediabox
                page_sizes.append(
                    {
                        "width": round(float(box.width), 2),
                        "height": round(float(box.height), 2),
                    }
                )

        return {
            "file": str(path),
            "file_size_bytes": path.stat().st_size,
            "pdf_version": version,
            "page_count": page_count,
            "encrypted": encrypted,
            "title": getattr(meta, "title", None),
            "author": getattr(meta, "author", None),
            "subject": getattr(meta, "subject", None),
            "creator": getattr(meta, "creator", None),
            "producer": getattr(meta, "producer", None),
            "creation_date": _meta_str(meta, "creation_date"),
            "modification_date": _meta_str(meta, "modification_date"),
            "page_sizes": page_sizes,
        }


def export_info(pdf_path: str | Path, output_dir: Path | None = None) -> Path:
    """`get_info` çıktısını JSON dosyası olarak yazar ve yolunu döndürür."""
    info = get_info(pdf_path)
    out_dir = ensure_output_dir(output_dir)
    name = f"{Path(info['file']).stem}_info.json"
    target = safe_output_path(name, out_dir)
    try:
        target.write_text(
            json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        raise PdfToolError("error.info_write_failed", path=target, exc=exc) from exc
    return target


def _pdf_version(header: str) -> str | None:
    """Açık reader'ın başlığından sürümü çıkarır (ör. ``%PDF-1.7`` -> ``1.7``).

    Sürüm zaten açık olan reader'dan gelir; dosya ayrıca açılmaz.
    """
    if header.startswith("%PDF-"):
        return header[5:8]
    return None


def _meta_str(meta: object | None, attr: str) -> str | None:
    value = getattr(meta, attr, None)
    return str(value) if value is not None else None
