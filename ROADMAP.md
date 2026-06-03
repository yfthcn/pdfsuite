# Yol Haritası

## v1 — Çekirdek PDF işlemleri ✅

Kapsam: tek çekirdek, üç arayüz (CLI / GUI / API + webgui).

- [x] **Bilgi** (`info`): sayfa sayısı, üstveri, şifreli mi, sayfa boyutları,
      dosya boyutu, PDF sürümü; JSON dışa aktarım.
- [x] **Birleştir** (`merge`): çok sayıda PDF, isteğe bağlı sayfa aralıkları
      (`(yol, "1-3,5")`).
- [x] **Ayır** (`split`): her sayfa / seçili aralıklar → ayrı PDF.
- [x] **Dönüştür** (`convert`):
  - PDF → görsel: **png / jpg / webp**, DPI seçilebilir.
  - Görseller → PDF.
- [x] Çıktı yönetimi: varsayılan `./output`, çakışmada `_1`/`_2`, tek `PdfToolError`.
- [x] Arayüzler: interaktif CLI, CustomTkinter GUI (koyu/açık tema), FastAPI + webgui.

## v2 — Ofis formatları (planlanan)

- [ ] **DOCX → PDF** ve diğer ofis formatları (xlsx, pptx, odt …).
      İmza yeri `core/convert.py` içinde yorum olarak ayrıldı:
      `docx_to_pdf(docx_path, output_dir=None) -> Path`.
- [ ] Dönüşüm motoru: **opsiyonel LibreOffice** bağımlılığı (headless `soffice`),
      yeni bir extra olarak: `pip install .[office]`.
- [ ] PDF → DOCX (metin/yerleşim çıkarımı) araştırması.

## v2+ — Olası eklentiler

- [ ] PDF sıkıştırma / optimizasyon.
- [ ] Şifre koyma / kaldırma, izinler.
- [ ] Sayfa döndürme, yeniden sıralama, filigran.
- [ ] Toplu (batch) işleme ve CLI alt komutları (argparse tabanlı, non-interaktif).
