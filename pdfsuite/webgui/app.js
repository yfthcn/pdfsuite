"use strict";

// API kökü: webgui /app altında servis edildiği için bir üst dizine gidiyoruz.
const API = new URL("..", window.location.href).href.replace(/\/$/, "");

// --- sekme geçişi ---------------------------------------------------------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab).classList.add("active");
  });
});

// --- tema ----------------------------------------------------------------
document.getElementById("theme-toggle").addEventListener("click", () => {
  document.documentElement.classList.toggle("light");
});

// --- eylemler ------------------------------------------------------------
const actions = {
  async info() {
    const file = pick("info-file");
    const data = await post("/info", form({ file }));
    show("info-out", JSON.stringify(data, null, 2));
  },

  async merge() {
    const files = pickMany("merge-files");
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    fd.append("output_name", val("merge-name") || "merged.pdf");
    await download("/merge", fd, val("merge-name") || "merged.pdf");
    show("merge-out", "✓ Birleştirildi ve indirildi.");
  },

  async split() {
    const file = pick("split-file");
    const pages = val("split-pages");
    if (val("split-mode") === "image") {
      const fd = form({ file });
      fd.append("fmt", val("split-fmt"));
      fd.append("dpi", val("split-dpi"));
      if (pages) fd.append("pages", pages);
      const data = await post("/convert/to-images", fd);
      show("split-out", `✓ ${data.count} görsel:\n` + data.files.join("\n"));
    } else {
      const fd = form({ file });
      if (pages) fd.append("pages", pages);
      const data = await post("/split", fd);
      show("split-out", `✓ ${data.count} PDF:\n` + data.files.join("\n"));
    }
  },

  async images() {
    const files = pickMany("images-files");
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    fd.append("output_name", val("images-name") || "output.pdf");
    await download("/convert/to-pdf", fd, val("images-name") || "output.pdf");
    show("images-out", "✓ PDF üretildi ve indirildi.");
  },
};

document.querySelectorAll("[data-action]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const out = btn.parentElement.querySelector(".output");
    try {
      if (out) out.textContent = "Çalışıyor…";
      await actions[btn.dataset.action]();
    } catch (err) {
      if (out) out.textContent = "✗ " + err.message;
    }
  });
});

// --- yardımcılar ----------------------------------------------------------
function val(id) { return document.getElementById(id).value.trim(); }
function show(id, text) { document.getElementById(id).textContent = text; }

function pick(id) {
  const f = document.getElementById(id).files[0];
  if (!f) throw new Error("Dosya seçilmedi.");
  return f;
}
function pickMany(id) {
  const files = [...document.getElementById(id).files];
  if (!files.length) throw new Error("Dosya seçilmedi.");
  return files;
}
function form(fields) {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) fd.append(k, v);
  return fd;
}

async function post(path, body) {
  const res = await fetch(API + path, { method: "POST", body });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

async function download(path, body, filename) {
  const res = await fetch(API + path, { method: "POST", body });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
