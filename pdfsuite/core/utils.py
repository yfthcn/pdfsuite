"""Ortak yardımcılar: yol doğrulama, çıktı yönetimi, çakışma çözümü, hata sınıfı.

Bu modül hiçbir arayüz bilmez; ekrana yazmaz, kullanıcıdan girdi istemez.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pypdf

# Varsayılan çıktı klasörü: çalışma dizinindeki ./output (paketin DIŞINDA).
DEFAULT_OUTPUT_DIR = Path("output")


class PdfToolError(Exception):
    """Core katmanındaki beklenen hatalar — çevrilmiş METİN değil, ANAHTAR taşır.

    Çeviri arayüz katmanında yapılır: ``t(exc.key, locale, **exc.params)``. Core
    hiçbir dili bilmez; yalnızca ``key`` ve biçimlendirme parametrelerini üretir.
    """

    def __init__(self, key: str, **params: object) -> None:
        self.key = key
        self.params = params
        super().__init__(key)

    def __str__(self) -> str:
        # Çeviriye uğramadan loglanırsa parametreler kaybolmasın (debug kolaylığı).
        # Kullanıcıya gösterim DAİMA t(exc.key, locale, **exc.params) ile yapılır.
        if not self.params:
            return self.key
        params = ", ".join(f"{k}={v!r}" for k, v in self.params.items())
        return f"{self.key} ({params})"


def resolve_input(path: str | Path) -> Path:
    """Girdi yolunu mutlak, var olan bir dosyaya çözer.

    Dosya yoksa ya da bir klasörse ``PdfToolError`` fırlatır.
    """
    p = Path(path).expanduser()
    if not p.exists():
        raise PdfToolError("error.file_not_found", path=p)
    if not p.is_file():
        raise PdfToolError("error.not_a_file", path=p)
    return p.resolve()


def is_pdf(path: Path) -> bool:
    """Dosyanın uzantısına ve sihirli baytlarına bakarak PDF olup olmadığını söyler."""
    if path.suffix.lower() != ".pdf":
        return False
    try:
        with path.open("rb") as fh:
            return fh.read(5) == b"%PDF-"
    except OSError:
        return False


def ensure_output_dir(output_dir: Path | None) -> Path:
    """Çıktı klasörünü hazırlar; ``None`` ise ./output kullanır, yoksa oluşturur."""
    target = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    target = target.expanduser()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PdfToolError("error.output_dir_failed", path=target, exc=exc) from exc
    return target


def safe_output_path(name: str, output_dir: Path) -> Path:
    """Çakışmada ``_1``, ``_2`` ekleyerek üzerine yazmayan benzersiz bir yol döndürür.

    ``name`` yalnız dosya adına indirgenir (path traversal koruması): ``../`` ve
    mutlak yollar etkisizleşir; sonucun ``output_dir`` altında kaldığı doğrulanır.
    """
    safe_name = Path(name).name
    if not safe_name or safe_name in (".", ".."):
        raise PdfToolError("error.bad_output_name", name=name)

    base = output_dir.resolve()
    candidate = base / safe_name
    if candidate.resolve().parent != base:
        raise PdfToolError("error.output_name_escapes", name=name)

    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        candidate = base / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def parse_page_ranges(spec: str, page_count: int) -> list[int]:
    """``"1-3,5"`` gibi 1 tabanlı bir aralık ifadesini 0 tabanlı indeks listesine çevirir.

    Sıra korunur, yinelenenler çıkarılır. Geçersiz/aralık dışı değerlerde
    ``PdfToolError`` fırlatır.
    """
    indices: list[int] = []
    seen: set[int] = set()
    for raw in spec.split(","):
        part = raw.strip()
        if not part:
            continue
        match part.split("-"):
            case [single]:
                start = end = single
            case [start, end]:
                pass
            case _:
                raise PdfToolError("error.bad_page_range", part=part)
        try:
            lo = int(start)
            hi = int(end)
        except ValueError:
            raise PdfToolError("error.bad_page_number", part=part) from None
        if lo < 1 or hi < 1 or lo > page_count or hi > page_count:
            raise PdfToolError(
                "error.page_range_out_of_bounds", count=page_count, part=part
            )
        step = 1 if hi >= lo else -1
        for n in range(lo, hi + step, step):
            idx = n - 1
            if idx not in seen:
                seen.add(idx)
                indices.append(idx)
    if not indices:
        raise PdfToolError("error.empty_page_spec", spec=spec)
    return indices


@contextmanager
def open_reader(path: str | Path) -> Iterator[pypdf.PdfReader]:
    """Yolu doğrulayıp bir ``pypdf.PdfReader`` açan ve daima kapatan bağlam yöneticisi.

    Yalnızca açar, doğrular ve kapatır — şifreleme politikası GÖMÜLMEZ; "şifreli mi"
    kararını çağıran verir (``reader.is_encrypted`` üzerinden).
    """
    resolved = resolve_input(path)
    if not is_pdf(resolved):
        raise PdfToolError("error.invalid_pdf", path=resolved)
    try:
        reader = pypdf.PdfReader(resolved)
    except Exception as exc:  # pypdf çeşitli düşük seviye hatalar fırlatabilir
        raise PdfToolError("error.read_failed", path=resolved, exc=exc) from exc
    try:
        yield reader
    finally:
        reader.close()
