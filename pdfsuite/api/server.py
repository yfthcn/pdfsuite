"""FastAPI sunucusu: core fonksiyonlarını HTTP üzerinden sunar.

Yüklenen dosyalar geçici bir klasöre yazılır, core çağrılır, çıktı ./output'a
düşer. Statik webgui kök altında servis edilir. Sunucu iş mantığı içermez.

Dil İSTEK BAZLI çözülür (``?lang=`` > ``Accept-Language`` > ``en``); global değildir.
Hatalar ``PdfToolError.key``/``params`` ile o isteğin diline çevrilir; beklenmeyen
istisnalar da çevrilmiş genel bir mesaja dönüşür (ham traceback sızmaz).
"""

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import APP_NAME, APP_TAGLINE, AUTHOR, GITHUB, WEBSITE, __version__
from ..core import (
    PdfToolError,
    get_info,
    images_to_pdf,
    merge,
    pdf_to_images,
    split,
)
from ..i18n import DEFAULT_LOCALE, available_locales, t, translate_error

logger = logging.getLogger("pdfsuite.api")

_WEBGUI_DIR = Path(__file__).resolve().parent.parent / "webgui"
_MAX_UPLOAD_MIB = 100
_MAX_UPLOAD_BYTES = _MAX_UPLOAD_MIB * 1024 * 1024
# Belirli hata anahtarları için özel HTTP durum kodu (varsayılan 400).
_STATUS_BY_KEY = {"api.file_too_large": 413}

app = FastAPI(title=APP_NAME, version=__version__, description=APP_TAGLINE)


@app.get("/")
def root(request: Request) -> dict:
    """Kök endpoint: uygulama ve marka bilgisi (tanıtım metni istek diline çevrilir)."""
    locale = _request_locale(request)
    return {
        "app": APP_NAME,
        "version": __version__,
        "tagline": t("app.tagline", locale),
        "author": AUTHOR,
        "website": WEBSITE,
        "github": GITHUB,
        "locale": locale,
        "available_locales": available_locales(),
        "endpoints": [
            "/info",
            "/merge",
            "/split",
            "/convert/to-images",
            "/convert/to-pdf",
        ],
    }


@app.post("/info")
async def api_info(file: UploadFile = File(...)) -> dict:
    with _staged(file) as path:
        return get_info(path)


@app.post("/merge")
async def api_merge(
    files: list[UploadFile] = File(...),
    output_name: str = Form("merged.pdf"),
) -> FileResponse:
    with _staged_many(files) as paths:
        result = merge(list(paths), None, output_name)
    return FileResponse(result, filename=result.name, media_type="application/pdf")


@app.post("/split")
async def api_split(
    file: UploadFile = File(...),
    pages: str | None = Form(None),
) -> dict:
    with _staged(file) as path:
        results = split(path, None, pages or None)
    return {"count": len(results), "files": [str(p) for p in results]}


@app.post("/convert/to-images")
async def api_to_images(
    file: UploadFile = File(...),
    fmt: str = Form("png"),
    dpi: int = Form(150),
    pages: str | None = Form(None),
) -> dict:
    with _staged(file) as path:
        results = pdf_to_images(path, None, fmt, dpi, pages or None)
    return {"count": len(results), "files": [str(p) for p in results]}


@app.post("/convert/to-pdf")
async def api_to_pdf(
    files: list[UploadFile] = File(...),
    output_name: str = Form("output.pdf"),
) -> FileResponse:
    with _staged_many(files) as paths:
        result = images_to_pdf(list(paths), None, output_name)
    return FileResponse(result, filename=result.name, media_type="application/pdf")


# --- hata işleyiciler (istek diline çeviri) ------------------------------
@app.exception_handler(PdfToolError)
async def _pdf_error_handler(request: Request, exc: PdfToolError) -> JSONResponse:
    locale = _request_locale(request)
    status = _STATUS_BY_KEY.get(exc.key, 400)
    return JSONResponse(
        status_code=status, content={"detail": t(exc.key, locale, **exc.params)}
    )


@app.exception_handler(Exception)
async def _unexpected_handler(request: Request, exc: Exception) -> JSONResponse:
    # PdfToolError olmayan beklenmeyen hata: tam traceback SUNUCUDA loglanır,
    # istemciye yalnızca çevrilmiş genel mesaj döner (traceback yanıta EKLENMEZ).
    logger.exception(
        "Beklenmeyen sunucu hatası: %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    locale = _request_locale(request)
    return JSONResponse(
        status_code=500, content={"detail": translate_error(exc, locale)}
    )


# webgui statik dosyaları (varsa) /app altında servis edilir
if _WEBGUI_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=_WEBGUI_DIR, html=True), name="webgui")


# --- dil çözümü ----------------------------------------------------------
def _request_locale(request: Request) -> str:
    """İstek dilini çözer: ``?lang=`` her zaman önce, sonra ``Accept-Language``, sonra ``en``."""
    available = available_locales()
    lang = request.query_params.get("lang")
    if lang and lang.lower() in available:
        return lang.lower()
    return _parse_accept_language(request.headers.get("accept-language"), available)


def _parse_accept_language(header: str | None, available: dict[str, str]) -> str:
    """``"tr-TR,tr;q=0.9,en;q=0.8"`` gibi başlıktan ilk DESTEKLENEN 2-harfli kodu seçer."""
    if not header:
        return DEFAULT_LOCALE
    ranked: list[tuple[float, str]] = []
    for part in header.split(","):
        token, _, params = part.strip().partition(";")
        code = token.strip().lower().split("-", 1)[0]
        if not code:
            continue
        quality = 1.0
        for param in params.split(";"):
            key, _, value = param.strip().partition("=")
            if key.strip() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        ranked.append((quality, code))
    # Yüksek q önce; eşit q'da başlıktaki sıra korunur (kararlı sıralama).
    ranked.sort(key=lambda item: item[0], reverse=True)
    for _, code in ranked:
        if code in available:
            return code
    return DEFAULT_LOCALE


# --- yükleme yardımcıları ------------------------------------------------
def _read_capped(file: UploadFile) -> bytes:
    """Yüklenen dosyayı tavan kadar okur; aşılırsa çevrilebilir bir hata fırlatır."""
    if file.size is not None and file.size > _MAX_UPLOAD_BYTES:
        raise PdfToolError("api.file_too_large", max=_MAX_UPLOAD_MIB)
    data = file.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        raise PdfToolError("api.file_too_large", max=_MAX_UPLOAD_MIB)
    return data


def _stage_name(filename: str | None, fallback: str) -> str:
    """Yüklenen ad yalnız dosya adına indirgenir (geçici klasörde traversal koruması)."""
    return Path(filename).name if filename else fallback


class _staged:
    """Tek yüklenen dosyayı geçici bir yola yazan bağlam yöneticisi."""

    def __init__(self, file: UploadFile) -> None:
        self._file = file
        self._tmp: tempfile.TemporaryDirectory | None = None

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory(prefix="pdfsuite_")
        try:
            target = Path(self._tmp.name) / _stage_name(self._file.filename, "upload")
            target.write_bytes(_read_capped(self._file))
        except BaseException:
            self._tmp.cleanup()  # __enter__ hata verirse __exit__ çağrılmaz
            self._tmp = None
            raise
        return target

    def __exit__(self, *exc: object) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()


class _staged_many:
    """Birden çok yüklenen dosyayı geçici bir klasöre yazan bağlam yöneticisi."""

    def __init__(self, files: list[UploadFile]) -> None:
        self._files = files
        self._tmp: tempfile.TemporaryDirectory | None = None

    def __enter__(self) -> list[Path]:
        self._tmp = tempfile.TemporaryDirectory(prefix="pdfsuite_")
        try:
            base = Path(self._tmp.name)
            paths: list[Path] = []
            for i, file in enumerate(self._files):
                target = base / _stage_name(file.filename, f"upload_{i}")
                target.write_bytes(_read_capped(file))
                paths.append(target)
        except BaseException:
            self._tmp.cleanup()
            self._tmp = None
            raise
        return paths

    def __exit__(self, *exc: object) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()


def run(argv: list[str] | None = None) -> int:
    """uvicorn ile sunucuyu başlatır."""
    import uvicorn

    host, port = "127.0.0.1", 8000
    print(f"{APP_NAME} API: http://{host}:{port}  (webgui: http://{host}:{port}/app)")
    uvicorn.run(app, host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
