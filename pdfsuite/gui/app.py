"""CustomTkinter ile modern masaüstü arayüz.

Koyu/açık tema, yuvarlatılmış köşeler, her işlem için ayrı sekme. İş yapmaz;
yalnızca core fonksiyonlarını çağırır ve sonucu gösterir. Tüm görünen metinler
``i18n.t`` ile çevrilir; dil açılır menüden değiştirilince ``refresh()`` kayıtlı
widget'ları yeni dile günceller (tam rebuild yok).
"""

import threading
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from .. import APP_NAME, AUTHOR, GITHUB, WEBSITE, __version__
from ..core import (
    export_info,
    get_info,
    images_to_pdf,
    merge,
    pdf_to_images,
    split,
)
from ..i18n import available_locales, resolve_locale, t, translate_error


def run(argv: list[str] | None = None) -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    PdfSuiteApp(resolve_locale()).mainloop()
    return 0


class PdfSuiteApp(ctk.CTk):
    def __init__(self, locale: str) -> None:
        super().__init__()
        self.locale = locale
        # Dil değişiminde yeniden çevrilecek kayıtlar.
        self._texts: list[tuple[ctk.CTkBaseClass, str, dict[str, object]]] = []
        self._phs: list[tuple[ctk.CTkEntry, str]] = []
        self._dark = True

        self.title(f"{APP_NAME} v{__version__}")
        self.geometry("860x620")
        self.minsize(740, 540)

        self._build_header()
        self._build_tabs()
        self._build_footer()

    # --- çeviri / kayıt yardımcıları --------------------------------------
    def t(self, key: str, **params: object) -> str:
        return t(key, self.locale, **params)

    def _reg_text[W: ctk.CTkBaseClass](
        self, widget: W, key: str, **params: object
    ) -> W:
        """Metin taşıyan bir widget'ı kaydeder ve ilk metnini ayarlar."""
        self._texts.append((widget, key, params))
        widget.configure(text=self.t(key, **params))
        return widget

    def _reg_ph(self, entry: ctk.CTkEntry, key: str) -> ctk.CTkEntry:
        """Bir girişin placeholder'ını kaydeder ve ayarlar."""
        self._phs.append((entry, key))
        entry.configure(placeholder_text=self.t(key))
        return entry

    def refresh(self) -> None:
        """Dil değişince tüm kayıtlı görünen metinleri yeni locale ile günceller."""
        for widget, key, params in self._texts:
            widget.configure(text=self.t(key, **params))
        for entry, key in self._phs:
            entry.configure(placeholder_text=self.t(key))
        # Sekme başlıkları (CTkTabview.rename ile).
        for key in self._tab_keys:
            new = self.t(key)
            old = self._tab_names[key]
            if new != old:
                self.tabs.rename(old, new)
                self._tab_names[key] = new
        # Tema segmenti — seçimi indeksle koru.
        idx = self._theme_values.index(self._theme_btn.get())
        self._theme_values = [self.t(k) for k in self._theme_keys]
        self._theme_btn.configure(values=self._theme_values)
        self._theme_btn.set(self._theme_values[idx])
        # Ayırma modu menüsü — seçimi indeksle koru.
        midx = self._mode_values.index(self.split_mode.get())
        self._mode_values = [self.t(k) for k in self._mode_keys]
        self.split_mode.configure(values=self._mode_values)
        self.split_mode.set(self._mode_values[midx])
        # Ekranda kalan durum eski dilde kalmasın.
        self._set_status("gui.status.ready")

    # --- yerleşim ---------------------------------------------------------
    def _build_header(self) -> None:
        head = ctk.CTkFrame(self, corner_radius=16)
        head.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            head, text=APP_NAME, font=ctk.CTkFont(size=26, weight="bold")
        ).pack(side="left", padx=16, pady=12)
        self._reg_text(
            ctk.CTkLabel(head, text_color=("gray40", "gray70")), "app.tagline"
        ).pack(side="left", padx=4)

        # Dil açılır menüsü — available_locales()'ten dinamik (yeni json otomatik).
        locales = available_locales()
        self._lang_by_name = {name: code for code, name in locales.items()}
        self._lang_menu = ctk.CTkOptionMenu(
            head, values=list(locales.values()), command=self._on_language, width=120
        )
        self._lang_menu.set(locales.get(self.locale, self.locale))
        self._lang_menu.pack(side="right", padx=16)

        # Tema segmenti.
        self._theme_keys = ("gui.theme.dark", "gui.theme.light")
        self._theme_values = [self.t(k) for k in self._theme_keys]
        self._theme_btn = ctk.CTkSegmentedButton(
            head, values=self._theme_values, command=self._on_theme
        )
        self._theme_btn.set(self._theme_values[0])
        self._theme_btn.pack(side="right", padx=8)

    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(self, corner_radius=16)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=8)
        self._tab_keys = [
            "gui.tab.info",
            "gui.tab.merge",
            "gui.tab.split",
            "gui.tab.images",
            "gui.tab.about",
        ]
        self._tab_names: dict[str, str] = {}
        for key in self._tab_keys:
            name = self.t(key)
            self._tab_names[key] = name
            self.tabs.add(name)
        self._tab_info(self.tabs.tab(self._tab_names["gui.tab.info"]))
        self._tab_merge(self.tabs.tab(self._tab_names["gui.tab.merge"]))
        self._tab_split(self.tabs.tab(self._tab_names["gui.tab.split"]))
        self._tab_images(self.tabs.tab(self._tab_names["gui.tab.images"]))
        self._tab_about(self.tabs.tab(self._tab_names["gui.tab.about"]))

    def _build_footer(self) -> None:
        foot = ctk.CTkFrame(self, corner_radius=16)
        foot.pack(fill="x", padx=16, pady=(0, 16))
        self.status = ctk.CTkLabel(foot, anchor="w")
        self.status.pack(side="left", padx=16, pady=8)
        self._set_status("gui.status.ready")
        ctk.CTkLabel(
            foot, text=f"{AUTHOR} · {WEBSITE}", text_color=("gray40", "gray70")
        ).pack(side="right", padx=16)

    # --- sekmeler ---------------------------------------------------------
    def _tab_info(self, tab: ctk.CTkFrame) -> None:
        self.info_path = self._file_row(tab, "gui.label.pdf_file", self._pick_pdf)
        self.info_box = ctk.CTkTextbox(tab, height=260, corner_radius=12)
        self.info_box.pack(fill="both", expand=True, padx=12, pady=8)
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 12))
        self._reg_text(
            ctk.CTkButton(bar, command=self._action_info), "gui.btn.get_info"
        ).pack(side="left")
        self._reg_text(
            ctk.CTkButton(bar, command=self._action_export_info), "gui.btn.export_info"
        ).pack(side="left", padx=8)

    def _tab_merge(self, tab: ctk.CTkFrame) -> None:
        self._reg_text(ctk.CTkLabel(tab), "gui.label.merge_list").pack(
            anchor="w", padx=12, pady=(12, 2)
        )
        self.merge_list = ctk.CTkTextbox(tab, height=180, corner_radius=12)
        self.merge_list.pack(fill="both", expand=True, padx=12, pady=4)
        self._reg_text(
            ctk.CTkLabel(tab, text_color=("gray40", "gray70")), "gui.label.merge_hint"
        ).pack(anchor="w", padx=12)
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=8)
        self._reg_text(
            ctk.CTkButton(bar, command=self._merge_add), "gui.btn.add_pdf"
        ).pack(side="left")
        self.merge_name = self._reg_ph(
            ctk.CTkEntry(bar, width=180), "gui.ph.merge_name"
        )
        self.merge_name.pack(side="left", padx=8)
        self._reg_text(
            ctk.CTkButton(bar, command=self._action_merge), "gui.btn.merge"
        ).pack(side="right")

    def _tab_split(self, tab: ctk.CTkFrame) -> None:
        self.split_path = self._file_row(tab, "gui.label.pdf_file", self._pick_pdf_to)
        opts = ctk.CTkFrame(tab, fg_color="transparent")
        opts.pack(fill="x", padx=12, pady=8)
        self.split_pages = self._reg_ph(ctk.CTkEntry(opts), "gui.ph.pages")
        self.split_pages.pack(side="left", fill="x", expand=True)
        self._mode_keys = ("gui.split.mode_pdf", "gui.split.mode_image")
        self._mode_values = [self.t(k) for k in self._mode_keys]
        self.split_mode = ctk.CTkOptionMenu(opts, values=self._mode_values)
        self.split_mode.pack(side="left", padx=8)
        self.split_fmt = ctk.CTkOptionMenu(opts, values=["png", "jpg", "webp"])
        self.split_fmt.pack(side="left")
        self.split_dpi = ctk.CTkOptionMenu(opts, values=["72", "150", "200", "300"])
        self.split_dpi.set("150")
        self.split_dpi.pack(side="left", padx=8)
        self._reg_text(
            ctk.CTkButton(tab, command=self._action_split), "gui.btn.run"
        ).pack(padx=12, pady=8, anchor="w")
        self.split_out = ctk.CTkTextbox(tab, height=200, corner_radius=12)
        self.split_out.pack(fill="both", expand=True, padx=12, pady=8)

    def _tab_images(self, tab: ctk.CTkFrame) -> None:
        self._reg_text(ctk.CTkLabel(tab), "gui.label.images_list").pack(
            anchor="w", padx=12, pady=(12, 2)
        )
        self.img_list = ctk.CTkTextbox(tab, height=220, corner_radius=12)
        self.img_list.pack(fill="both", expand=True, padx=12, pady=4)
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=8)
        self._reg_text(
            ctk.CTkButton(bar, command=self._img_add), "gui.btn.add_image"
        ).pack(side="left")
        self.img_name = self._reg_ph(ctk.CTkEntry(bar, width=180), "gui.ph.images_name")
        self.img_name.pack(side="left", padx=8)
        self._reg_text(
            ctk.CTkButton(bar, command=self._action_images), "gui.btn.make_pdf"
        ).pack(side="right")

    def _tab_about(self, tab: ctk.CTkFrame) -> None:
        box = ctk.CTkFrame(tab, corner_radius=16)
        box.pack(expand=True, padx=24, pady=24)
        ctk.CTkLabel(
            box,
            text=f"{APP_NAME} v{__version__}",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(padx=24, pady=(24, 4))
        self._reg_text(ctk.CTkLabel(box), "app.tagline").pack(padx=24)
        self._reg_text(
            ctk.CTkLabel(box, text_color=("gray40", "gray70")),
            "gui.about.copyright",
            author=AUTHOR,
        ).pack(padx=24, pady=(8, 16))
        for label, url in ((WEBSITE, WEBSITE), (GITHUB, GITHUB)):
            ctk.CTkButton(
                box, text=label, width=320, command=lambda u=url: _open_url(u)
            ).pack(padx=24, pady=6)
        ctk.CTkLabel(box, text="").pack(pady=8)

    # --- eylemler (core çağrıları, arka planda) ---------------------------
    def _action_info(self) -> None:
        path = self.info_path.get().strip()
        self._run_bg(lambda: get_info(path), self._show_info)

    def _show_info(self, info: object) -> None:
        assert isinstance(info, dict)
        self.info_box.delete("1.0", "end")
        for key, value in info.items():
            shown = self.t("unit.pages", n=len(value)) if key == "page_sizes" else value
            self.info_box.insert("end", f"{key:>18}: {shown}\n")
        self._set_status("gui.status.ready")

    def _action_export_info(self) -> None:
        path = self.info_path.get().strip()
        self._run_bg(
            lambda: export_info(path),
            lambda p: self._ok(self.t("gui.result.written", path=p)),
        )

    def _action_merge(self) -> None:
        inputs = _parse_merge_lines(self.merge_list.get("1.0", "end"))
        name = self.merge_name.get().strip() or "merged.pdf"
        self._run_bg(
            lambda: merge(inputs, None, name),
            lambda p: self._ok(self.t("gui.result.written", path=p)),
        )

    def _action_split(self) -> None:
        path = self.split_path.get().strip()
        pages = self.split_pages.get().strip() or None
        is_image = self._mode_values.index(self.split_mode.get()) == 1
        if is_image:
            fmt = self.split_fmt.get()
            dpi = int(self.split_dpi.get())

            def job() -> list[Path]:
                return pdf_to_images(path, None, fmt, dpi, pages)
        else:

            def job() -> list[Path]:
                return split(path, None, pages)

        self._run_bg(job, self._show_split)

    def _show_split(self, paths: object) -> None:
        assert isinstance(paths, list)
        self.split_out.delete("1.0", "end")
        self.split_out.insert(
            "end", self.t("gui.result.files_written", n=len(paths)) + "\n"
        )
        for p in paths:
            self.split_out.insert("end", f"  {p}\n")
        self._ok(self.t("gui.result.files_written", n=len(paths)))

    def _action_images(self) -> None:
        images = [
            ln.strip()
            for ln in self.img_list.get("1.0", "end").splitlines()
            if ln.strip()
        ]
        name = self.img_name.get().strip() or "output.pdf"
        self._run_bg(
            lambda: images_to_pdf(images, None, name),
            lambda p: self._ok(self.t("gui.result.written", path=p)),
        )

    # --- altyapı ----------------------------------------------------------
    def _run_bg(
        self, job: Callable[[], object], on_ok: Callable[[object], None]
    ) -> None:
        """İşi arka planda çalıştırır; arayüzü kilitlemez, sonucu ana iş parçacığında işler."""
        self._set_status("gui.status.working")

        def worker() -> None:
            try:
                result = job()
            except Exception as exc:
                # PdfToolError ya da beklenmeyen — ikisi de çevrilir, traceback sızmaz.
                msg = translate_error(exc, self.locale)
                self.after(0, lambda: self._err(msg))
            else:
                self.after(0, lambda: on_ok(result))

        threading.Thread(target=worker, daemon=True).start()

    def _file_row(
        self, tab: ctk.CTkFrame, label_key: str, picker: Callable[[ctk.CTkEntry], None]
    ) -> ctk.CTkEntry:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(12, 4))
        self._reg_text(ctk.CTkLabel(row, width=90, anchor="w"), label_key).pack(
            side="left"
        )
        entry = ctk.CTkEntry(row)
        entry.pack(side="left", fill="x", expand=True, padx=8)
        self._reg_text(
            ctk.CTkButton(row, width=80, command=lambda: picker(entry)),
            "gui.btn.browse",
        ).pack(side="left")
        return entry

    def _pick_pdf(self, entry: ctk.CTkEntry | None = None) -> None:
        target = entry if isinstance(entry, ctk.CTkEntry) else self.info_path
        self._pick_into(target, [("PDF", "*.pdf")])

    def _pick_pdf_to(self, entry: ctk.CTkEntry) -> None:
        self._pick_into(entry, [("PDF", "*.pdf")])

    def _pick_into(self, entry: ctk.CTkEntry, types: list[tuple[str, str]]) -> None:
        path = filedialog.askopenfilename(filetypes=types)
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _merge_add(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            self.merge_list.insert("end", f"{path}\n")

    def _img_add(self) -> None:
        paths = filedialog.askopenfilenames(
            filetypes=[("Image", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff")]
        )
        for p in paths:
            self.img_list.insert("end", f"{p}\n")

    def _on_theme(self, value: str) -> None:
        self._dark = self._theme_values.index(value) == 0
        ctk.set_appearance_mode("dark" if self._dark else "light")

    def _on_language(self, display: str) -> None:
        code = self._lang_by_name.get(display)
        if code and code != self.locale:
            self.locale = code
            self.refresh()

    def _set_status(self, key: str) -> None:
        self.status.configure(text=self.t(key), text_color=("gray10", "gray90"))

    def _ok(self, text: str) -> None:
        self.status.configure(text=f"✓ {text}", text_color=("green", "lightgreen"))

    def _err(self, text: str) -> None:
        self.status.configure(text=f"✗ {text}", text_color=("red", "salmon"))


def _parse_merge_lines(text: str) -> list[str | tuple[str, str]]:
    inputs: list[str | tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            path, spec = line.split("|", 1)
            inputs.append((path.strip(), spec.strip()))
        else:
            inputs.append(line)
    return inputs


def _open_url(url: str) -> None:
    import webbrowser

    webbrowser.open(url)


if __name__ == "__main__":
    raise SystemExit(run())
