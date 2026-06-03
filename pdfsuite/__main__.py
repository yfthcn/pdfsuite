"""Giriş noktası: `python -m pdfsuite [cli|gui|api]`.

pdfsuite — © 2026 Fatih (github.com/yfthcn) — Licensed under AGPL-3.0-or-later.

Arayüz bağımlılıkları (customtkinter, fastapi/uvicorn) yalnızca ilgili dalda
ve TEMBEL olarak import edilir; böylece minimum kurulumda CLI tek başına çalışır.
"""

import importlib.util
import sys


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    mode = args[0].lower() if args else "cli"
    rest = args[1:]

    match mode:
        case "cli":
            from .cli.menu import run

            return run(rest)
        case "gui":
            # Yalnız opsiyonel paket eksikse yönlendir; modülün KENDİ
            # ImportError'ını maskeleme (gerçek bir hata propagate olsun).
            if importlib.util.find_spec("customtkinter") is None:
                print("GUI için kur: pip install .[gui]", file=sys.stderr)
                return 1
            from .gui.app import run

            return run(rest)
        case "api":
            if importlib.util.find_spec("fastapi") is None:
                print("Web/API için kur: pip install .[web]", file=sys.stderr)
                return 1
            from .api.server import run

            return run(rest)
        case "-h" | "--help" | "help":
            print("Kullanım: python -m pdfsuite [cli|gui|api]")
            print("  cli  (varsayılan)  metin tabanlı menü")
            print("  gui                CustomTkinter masaüstü arayüzü  [.[gui]]")
            print("  api                FastAPI sunucusu                [.[web]]")
            return 0
        case other:
            print(f"Bilinmeyen mod: {other!r} (cli|gui|api)", file=sys.stderr)
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
