# pdfsuite

**[English](#english) · [Türkçe](#türkçe)**

Modern, minimum-dependency PDF toolkit with one core and three interfaces (CLI / GUI / API).
Built for **Python 3.14**.

📚 [TECHNICAL.md](TECHNICAL.md) (developer/architecture) · 🗺️ [ROADMAP.md](ROADMAP.md) (versions)

---

## English

### What it does

A single, interface-agnostic core (`core/`) on top of which run a text **CLI**, a CustomTkinter
**GUI**, and a FastAPI **API** (+ a static web UI).

| Feature | Description |
|---------|-------------|
| **Info** | Page count, metadata, encrypted?, page sizes, file size, PDF version; JSON export |
| **Merge** | Combine many PDFs (with optional page ranges) into one |
| **Split** | Write each page / selected ranges as separate PDFs |
| **Convert** | PDF → images (png/jpg/webp, selectable DPI) and images → PDF |

Plus: **multi-language** (i18n), available across **CLI / GUI / API**.

> Written for **Python 3.14 only** — no backward compatibility; modern idioms (PEP 695 type
> parameters, `X | Y` unions, `match`/`case`, `pathlib`).

### Installation

```bash
python3.14 -m venv .venv
source .venv/bin/activate

pip install .            # minimum: pypdf + pymupdf + pillow (CLI works)
pip install .[gui]       # + CustomTkinter desktop GUI
pip install .[web]       # + FastAPI/uvicorn web API
pip install .[gui,web]   # everything
```

### Running

```bash
python -m pdfsuite        # CLI (default) — interactive menu
python -m pdfsuite gui    # desktop GUI   (needs .[gui])
python -m pdfsuite api    # API server    (needs .[web])
```

When the API is up:
- REST root: <http://127.0.0.1:8000/>
- Web UI: <http://127.0.0.1:8000/app>
- Auto docs (Swagger): <http://127.0.0.1:8000/docs>

If the relevant extra is missing, the app tells you what to install
(e.g. `GUI için kur: pip install .[gui]`).

### Language support

Default is **en**; on startup it switches to your system language if supported. Currently **tr**
and **en**, and the language can be changed at runtime:

- **CLI:** `python -m pdfsuite cli --lang tr` (or the "Change language" menu option).
- **GUI:** the language dropdown (top right).
- **API:** per request — `?lang=tr` (takes priority) or the `Accept-Language` header.

**Adding a language** needs no code change: drop an `xx.json` into `pdfsuite/locales/`
(`_name` + the existing keys). The language list is built **dynamically** from that folder.

### Roadmap (v2)

DOCX and other office formats (via an optional LibreOffice dependency). See [ROADMAP.md](ROADMAP.md).

### License

pdfsuite is free and open-source software, licensed under the **GNU Affero General Public
License v3.0 or later (AGPL-3.0-or-later)** — see [LICENSE](LICENSE).

You may use, study, share and modify it freely. Under the AGPL's copyleft, any derivative work
— including software made available to users **over a network** — must also remain open and be
distributed under the AGPL-3.0.

© 2026 Fatih · <https://github.com/yfthcn>

### Contact / brand

- 🌐 Site: <https://kaktusdev.net>
- 💻 GitHub: <https://github.com/yfthcn>

---

## Türkçe

### Ne yapar

Arayüzden bağımsız tek bir çekirdek (`core/`) üzerine: metin tabanlı **CLI**, CustomTkinter
**GUI** ve FastAPI **API** (+ statik bir web arayüzü).

| Özellik | Açıklama |
|---------|----------|
| **Bilgi** | Sayfa sayısı, üstveri, şifreli mi, sayfa boyutları, dosya boyutu, PDF sürümü; JSON dışa aktarım |
| **Birleştir** | Çok sayıda PDF'i (isteğe bağlı sayfa aralıklarıyla) tek dosyada birleştir |
| **Ayır** | Her sayfayı / seçili aralıkları ayrı PDF olarak yaz |
| **Dönüştür** | PDF → görsel (png/jpg/webp, DPI seçilebilir) ve görseller → PDF |

Ayrıca: **çok dilli** (i18n), **CLI / GUI / API** üçünde de.

> Yalnızca **Python 3.14** için yazıldı — geriye dönük uyumluluk yok; modern idiomlar (PEP 695
> tip parametreleri, `X | Y` birleşim tipleri, `match`/`case`, `pathlib`).

### Kurulum

```bash
python3.14 -m venv .venv
source .venv/bin/activate

pip install .            # minimum: pypdf + pymupdf + pillow (CLI çalışır)
pip install .[gui]       # + CustomTkinter masaüstü GUI
pip install .[web]       # + FastAPI/uvicorn web API
pip install .[gui,web]   # hepsi
```

### Çalıştırma

```bash
python -m pdfsuite        # CLI (varsayılan) — interaktif menü
python -m pdfsuite gui    # masaüstü GUI   (.[gui] gerekir)
python -m pdfsuite api    # API sunucusu   (.[web] gerekir)
```

API açıldığında:
- REST kökü: <http://127.0.0.1:8000/>
- Web arayüzü: <http://127.0.0.1:8000/app>
- Otomatik dokümanlar (Swagger): <http://127.0.0.1:8000/docs>

İlgili extra kurulu değilse uygulama ne kuracağınızı söyler
(ör. `GUI için kur: pip install .[gui]`).

### Dil desteği

Varsayılan **en**; başlangıçta sistem diliniz destekleniyorsa ona geçilir. Şu an **tr** ve **en**
var, dil çalışırken değiştirilebilir:

- **CLI:** `python -m pdfsuite cli --lang tr` (ya da menüde "Dil değiştir").
- **GUI:** sağ üstteki dil açılır menüsü.
- **API:** istek bazlı — `?lang=tr` (önce) ya da `Accept-Language` başlığı.

**Yeni dil eklemek** kod değişikliği gerektirmez: `pdfsuite/locales/` içine bir `xx.json` koyun
(`_name` + mevcut anahtarlar). Dil listesi bu klasörden **dinamik** üretilir.

### Yol haritası (v2)

DOCX ve diğer ofis formatları (opsiyonel LibreOffice bağımlılığıyla). Bkz. [ROADMAP.md](ROADMAP.md).

### Lisans

pdfsuite ücretsiz ve açık kaynaklı bir yazılımdır; **GNU Affero Genel Kamu Lisansı v3.0 veya
sonrası (AGPL-3.0-or-later)** altında lisanslanmıştır — bkz. [LICENSE](LICENSE).

Yazılımı özgürce kullanabilir, inceleyebilir, paylaşabilir ve değiştirebilirsiniz. AGPL'nin
copyleft koşulu gereği, türev çalışmalar — kullanıcılara **ağ üzerinden** sunulanlar dahil — de
açık kalmak ve AGPL-3.0 altında dağıtılmak zorundadır.

© 2026 Fatih · <https://github.com/yfthcn>

### İletişim / marka

- 🌐 Site: <https://kaktusdev.net>
- 💻 GitHub: <https://github.com/yfthcn>
