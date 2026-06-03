"""İnteraktif CLI menüsü. Sadece girdi alır, core'u çağırır, sonucu yazar.

İş mantığı yoktur; her seçenek bir core fonksiyonuna yönlenir. Tüm kullanıcıya
görünen metinler ``i18n.t`` ile çevrilir; dil oturum içinde değiştirilebilir.
"""

from pathlib import Path

from .. import APP_NAME, GITHUB, WEBSITE, __version__
from ..core import (
    PdfToolError,
    export_info,
    get_info,
    images_to_pdf,
    merge,
    pdf_to_images,
    split,
)
from ..i18n import available_locales, resolve_locale, t, translate_error


def run(argv: list[str] | None = None) -> int:
    """CLI'yi başlatır. ``--lang xx`` verilirse o dil, yoksa resolve_locale()."""
    locale = resolve_locale(_lang_flag(argv))
    return CliMenu(locale).run()


class CliMenu:
    def __init__(self, locale: str) -> None:
        self.locale = locale

    def run(self) -> int:
        self._banner()
        while True:
            print(
                "\n  "
                + "\n  ".join(
                    self.t(key)
                    for key in (
                        "cli.menu.info",
                        "cli.menu.merge",
                        "cli.menu.split",
                        "cli.menu.images",
                        "cli.menu.language",
                        "cli.menu.quit",
                    )
                )
            )
            choice = self._ask("cli.prompt.choice")
            try:
                match choice:
                    case "1":
                        self._do_info()
                    case "2":
                        self._do_merge()
                    case "3":
                        self._do_split_or_convert()
                    case "4":
                        self._do_images_to_pdf()
                    case "5":
                        self._change_language()
                    case "0" | "q" | "":
                        print(self.t("cli.goodbye"))
                        return 0
                    case _:
                        print(self.t("cli.invalid_choice"))
            except PdfToolError as exc:
                print(
                    f"  ✗ {self.t('cli.error', msg=translate_error(exc, self.locale))}"
                )
            except KeyboardInterrupt:
                print("\n" + self.t("cli.cancelled"))
                return 130
            except Exception as exc:  # beklenmeyen — çeviri, ham traceback gösterme
                print(
                    f"  ✗ {self.t('cli.error', msg=translate_error(exc, self.locale))}"
                )

    # --- eylemler ---------------------------------------------------------
    def _do_info(self) -> None:
        path = self._ask("cli.prompt.pdf_path")
        info = get_info(path)
        print("\n  " + self.t("cli.info.header"))
        for key, value in info.items():
            if key == "page_sizes":
                print(f"  {key}: {self.t('unit.pages', n=len(value))}")
            else:
                print(f"  {key}: {value}")
        if self._yes_no("cli.info.export_q"):
            out = export_info(path, self._opt_output_dir())
            print(f"  ✓ {self.t('cli.written', path=out)}")

    def _do_merge(self) -> None:
        inputs: list[str | Path | tuple[str | Path, str]] = []
        print(self.t("cli.merge.intro"))
        while True:
            path = self._ask(
                "cli.merge.prompt_pdf", allow_empty=True, n=len(inputs) + 1
            )
            if not path:
                break
            spec = self._ask("cli.merge.prompt_range", allow_empty=True)
            inputs.append((path, spec) if spec else path)
        if not inputs:
            print("  " + self.t("cli.no_files"))
            return
        name = self._ask("cli.merge.prompt_name", allow_empty=True) or "merged.pdf"
        out = merge(inputs, self._opt_output_dir(), name)
        print(f"  ✓ {self.t('cli.written', path=out)}")

    def _do_split_or_convert(self) -> None:
        path = self._ask("cli.prompt.pdf_path")
        spec = self._ask("cli.split.prompt_range", allow_empty=True) or None
        print(self.t("cli.split.output_type"))
        match self._ask("cli.prompt.choice"):
            case "2":
                fmt = self._ask("cli.split.prompt_fmt", allow_empty=True) or "png"
                dpi_raw = self._ask("cli.split.prompt_dpi", allow_empty=True) or "150"
                try:
                    dpi = int(dpi_raw)
                except ValueError:
                    raise PdfToolError("error.dpi_not_positive", dpi=dpi_raw) from None
                results = pdf_to_images(path, self._opt_output_dir(), fmt, dpi, spec)
            case _:
                results = split(path, self._opt_output_dir(), spec)
        print(f"  ✓ {self.t('cli.files_written', n=len(results))}")
        for r in results:
            print(f"    {r}")

    def _do_images_to_pdf(self) -> None:
        images: list[str | Path] = []
        print(self.t("cli.images.intro"))
        while True:
            path = self._ask(
                "cli.images.prompt_img", allow_empty=True, n=len(images) + 1
            )
            if not path:
                break
            images.append(path)
        if not images:
            print("  " + self.t("cli.no_images"))
            return
        name = self._ask("cli.images.prompt_name", allow_empty=True) or "output.pdf"
        out = images_to_pdf(images, self._opt_output_dir(), name)
        print(f"  ✓ {self.t('cli.written', path=out)}")

    def _change_language(self) -> None:
        locales = available_locales()
        codes = list(locales)
        print("\n  " + self.t("cli.language.choose"))
        for i, code in enumerate(codes, start=1):
            marker = "•" if code == self.locale else " "
            print(f"   {marker} {i}) {locales[code]} ({code})")
        raw = self._ask("cli.prompt.choice", allow_empty=True)
        if raw.isdigit() and 1 <= int(raw) <= len(codes):
            self.locale = codes[int(raw) - 1]
        elif raw in locales:
            self.locale = raw
        print("  " + self.t("cli.language.changed", name=locales[self.locale]))

    # --- yardımcılar ------------------------------------------------------
    def _opt_output_dir(self) -> Path | None:
        raw = self._ask("cli.prompt.output_dir", allow_empty=True)
        return Path(raw) if raw else None

    def _ask(self, key: str, allow_empty: bool = False, **params: object) -> str:
        prompt = self.t(key, **params)
        while True:
            value = input(f"{prompt}: ").strip()
            if value or allow_empty:
                return value
            print("  " + self.t("cli.not_empty"))

    def _yes_no(self, key: str) -> bool:
        # "evet" hem en (yes) hem tr (evet) için 'e'/'y' baş harfini kabul et.
        answer = self._ask(key, allow_empty=True).strip().lower()
        return answer.startswith(("e", "y"))

    def t(self, key: str, **params: object) -> str:
        return t(key, self.locale, **params)

    def _banner(self) -> None:
        bar = "─" * 60
        print(f"\n  {bar}")
        print(f"   📄  {APP_NAME}  v{__version__}")
        print(f"   {self.t('app.tagline')}")
        print(f"   {WEBSITE}  ·  {GITHUB}")
        print(f"  {bar}")


def _lang_flag(argv: list[str] | None) -> str | None:
    """``--lang xx`` ya da ``--lang=xx`` bayrağını ayıklar."""
    if not argv:
        return None
    for i, arg in enumerate(argv):
        if arg == "--lang" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return None


if __name__ == "__main__":
    raise SystemExit(run())
