"""Çok dilli (i18n) altyapı — ARAYÜZ katmanı içindir; core bunu BİLMEZ.

Dil dosyaları ``pdfsuite.locales`` paketindeki ``*.json``'lardır ve
``importlib.resources`` ile okunur (dosya yolu değil; kurulu wheel'de de çalışır).
Dil listesi bu klasörden DİNAMİK üretilir — hiçbir yerde sabit liste yoktur.

© 2026 Fatih (github.com/yfthcn) — Licensed under AGPL-3.0-or-later.
"""

import json
import locale as _locale
import os
from functools import lru_cache
from importlib.resources import files

_LOCALES_PKG = "pdfsuite.locales"
DEFAULT_LOCALE = "en"


def available_locales() -> dict[str, str]:
    """``{kod: görünen_ad}`` — klasördeki ``*.json``'lardan dinamik üretilir.

    Kod = dosya adı (``en.json`` -> ``"en"``), görünen ad = dosyadaki ``_name``.
    Önbelleğe alınmaz; yeni bir dosya eklenince otomatik görünür.
    """
    result: dict[str, str] = {}
    for entry in files(_LOCALES_PKG).iterdir():
        name = entry.name
        if name.endswith(".json"):
            code = name[:-5]
            try:
                data = json.loads(entry.read_text(encoding="utf-8"))
            except OSError, json.JSONDecodeError:
                continue
            result[code] = data.get("_name", code)
    return dict(sorted(result.items()))


def t(key: str, locale: str, **kwargs: object) -> str:
    """``key``'i ``locale``'de çevirir; yoksa ``en``'e, o da yoksa key'in kendisine düşer.

    ``str.format(**kwargs)`` ile interpolasyon yapılır.
    """
    template = _load(locale).get(key)
    if template is None and locale != DEFAULT_LOCALE:
        template = _load(DEFAULT_LOCALE).get(key)
    if template is None:
        return key
    try:
        return template.format(**kwargs)
    except KeyError, IndexError, ValueError:
        return template


def translate_error(exc: Exception, locale: str) -> str:
    """Bir istisnayı kullanıcıya gösterilecek çevrilmiş mesaja dönüştürür.

    ``PdfToolError`` gibi ``.key``/``.params`` taşıyan istisnalar anahtarla çevrilir;
    aksi halde (beklenmeyen/programlama hatası) genel ``error.unexpected`` mesajı
    verilir — ham anahtar ya da traceback ASLA kullanıcıya sızmaz. (core'a bağlanmamak
    için ördek-tipleme kullanılır.)
    """
    key = getattr(exc, "key", None)
    params = getattr(exc, "params", None)
    if isinstance(key, str) and isinstance(params, dict):
        return t(key, locale, **params)
    return t("error.unexpected", locale, exc=str(exc))


def resolve_locale(explicit: str | None = None) -> str:
    """Etkin dili seçer: (1) açık kullanıcı seçimi, (2) sistem dili, (3) ``en``."""
    available = available_locales()
    if explicit and explicit in available:
        return explicit
    system = _system_locale()
    if system and system in available:
        return system
    return DEFAULT_LOCALE


@lru_cache(maxsize=None)
def _load(code: str) -> dict[str, str]:
    """Bir locale dosyasının içeriğini okur (çeviriler çalışma anında değişmez)."""
    resource = files(_LOCALES_PKG) / f"{code}.json"
    if not resource.is_file():
        return {}
    try:
        return json.loads(resource.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}


def _system_locale() -> str | None:
    """Sistem dilinin 2-harfli kodunu döndürür (deprecated getdefaultlocale KULLANMADAN)."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            code = value.split(".")[0].split("_")[0].strip().lower()
            if code:
                return code
    try:
        current = _locale.getlocale()[0]
    except ValueError, TypeError:
        current = None
    if current:
        return current.split("_")[0].strip().lower()
    return None
