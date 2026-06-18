"""i18n altyapısı testleri: anahtar paritesi, çeviri, fallback, Accept-Language."""

import json
from importlib.resources import files

import pytest

from pdfsuite.api.server import _parse_accept_language
from pdfsuite.core import PdfToolError
from pdfsuite.i18n import (
    available_locales,
    resolve_locale,
    t,
    translate_error,
)


def _load_raw(code: str) -> dict[str, str]:
    return json.loads((files("pdfsuite.locales") / f"{code}.json").read_text("utf-8"))


# --- anahtar paritesi ----------------------------------------------------
def test_en_tr_key_parity() -> None:
    en = set(_load_raw("en")) - {"_name"}
    tr = set(_load_raw("tr")) - {"_name"}
    assert en == tr, f"yalnız en'de: {en - tr} | yalnız tr'de: {tr - en}"


def test_all_locales_match_en() -> None:
    """Her dil dosyası en ile aynı anahtar kümesine sahip olmalı (_name hariç)."""
    en = set(_load_raw("en")) - {"_name"}
    for code in available_locales():
        keys = set(_load_raw(code)) - {"_name"}
        assert keys == en, f"{code} farkı: {keys ^ en}"


def test_every_locale_has_name() -> None:
    for code in available_locales():
        assert _load_raw(code).get("_name"), f"{code} dosyasında _name yok"


# --- available_locales ---------------------------------------------------
def test_available_locales_finds_en_tr() -> None:
    av = available_locales()
    assert av["en"] == "English"
    assert av["tr"] == "Türkçe"


# --- t() -----------------------------------------------------------------
def test_t_interpolation() -> None:
    assert (
        t("error.dpi_too_high", "en", max=1200, dpi=5000)
        == "DPI too high (max 1200): 5000"
    )
    assert (
        t("error.dpi_too_high", "tr", max=1200, dpi=5000)
        == "DPI çok yüksek (en fazla 1200): 5000"
    )


def test_t_repr_param() -> None:
    assert (
        t("error.bad_output_name", "en", name="../x") == "Invalid output name: '../x'"
    )


def test_t_fallback_to_en() -> None:
    # Desteklenmeyen locale -> en içeriğine düşer.
    assert t("app.tagline", "zz") == t("app.tagline", "en")


def test_t_unknown_key_returns_key() -> None:
    assert t("error.does_not_exist", "tr") == "error.does_not_exist"


def test_t_missing_kwargs_returns_template() -> None:
    # Eksik parametrede ham şablon döner, çökmez.
    assert "{path}" in t("error.invalid_pdf", "en")


# --- resolve_locale ------------------------------------------------------
def test_resolve_locale_explicit() -> None:
    assert resolve_locale("tr") == "tr"
    assert resolve_locale("en") == "en"


def test_resolve_locale_unsupported_explicit_falls_back() -> None:
    assert resolve_locale("zz") in available_locales()


def test_resolve_locale_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "tr_TR.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert resolve_locale() == "tr"


def test_resolve_locale_unsupported_env_is_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LC_ALL", "fr_FR.UTF-8")
    assert resolve_locale() == "en"


# --- Accept-Language ayrıştırma ------------------------------------------
@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("tr-TR,tr;q=0.9,en;q=0.8", "tr"),
        ("en-US,en;q=0.9,tr;q=0.8", "en"),
        ("fr-FR,de;q=0.7", "en"),  # desteklenmez -> varsayılan
        ("tr", "tr"),
        ("", "en"),
        (None, "en"),
        ("en;q=0.1,tr;q=0.9", "tr"),  # q'ya göre sırala
    ],
)
def test_accept_language(header: str | None, expected: str) -> None:
    assert _parse_accept_language(header, available_locales()) == expected


# --- translate_error -----------------------------------------------------
def test_translate_error_pdftoolerror() -> None:
    exc = PdfToolError("error.invalid_pdf", path="/x.pdf")
    assert translate_error(exc, "en") == "Not a valid PDF: /x.pdf"
    assert translate_error(exc, "tr") == "Geçerli bir PDF değil: /x.pdf"


def test_translate_error_unexpected() -> None:
    exc = ValueError("boom")
    assert translate_error(exc, "en") == "Unexpected error: boom"
    assert translate_error(exc, "tr") == "Beklenmeyen hata: boom"
