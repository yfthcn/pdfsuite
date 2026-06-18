"""GUI dil değiştirme testi — ekran (display) gerektirir; yoksa atlanır."""

import os
import sys

import pytest

ctk = pytest.importorskip("customtkinter")


def _has_display() -> bool:
    if sys.platform in ("darwin", "win32"):
        return True
    return bool(os.environ.get("DISPLAY"))


@pytest.mark.skipif(not _has_display(), reason="GUI bir ekran gerektirir")
def test_gui_language_switch() -> None:
    from pdfsuite.gui.app import PdfSuiteApp
    from pdfsuite.i18n import t

    try:
        app = PdfSuiteApp("en")
    except ctk.TclError as exc:  # type: ignore[attr-defined]
        pytest.skip(f"Tk başlatılamadı: {exc}")

    try:
        app.update()
        # Başlangıç: İngilizce
        assert app._tab_names["gui.tab.info"] == t("gui.tab.info", "en")
        assert app._theme_btn.get() == t("gui.theme.dark", "en")

        # Türkçe'ye geç (dropdown görünen adıyla)
        app._on_language("Türkçe")
        app.update()
        assert app.locale == "tr"
        # Statik etiketler (sekme), segment (seçim korunarak) ve placeholder döner.
        assert app._tab_names["gui.tab.info"] == t("gui.tab.info", "tr")
        assert app._theme_btn.get() == t("gui.theme.dark", "tr")
        assert app.split_mode.get() == t("gui.split.mode_pdf", "tr")
        assert app.split_pages.cget("placeholder_text") == t("gui.ph.pages", "tr")
        assert app.status.cget("text") == t("gui.status.ready", "tr")

        # Geri dön
        app._on_language("English")
        app.update()
        assert app._tab_names["gui.tab.info"] == t("gui.tab.info", "en")
    finally:
        app.destroy()
