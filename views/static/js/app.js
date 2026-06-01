let bahanDipilih = new Set();

let stream = null;
let hasilScan = null;
let tmModel = null;
let modeKamera = false;
let lastAutoAdd = 0;
let realtimeTimer = null;

const TM_URL = "https://teachablemachine.withgoogle.com/models/CLV_1ruvN/";
const AUTO_ADD_THRESH = 50;
const SCAN_INTERVAL = 1000;
const COOLDOWN_MS = 3000;

document.addEventListener("DOMContentLoaded", () => {
  initRekomendasiPage();
  initJelajahiPage();
  initScrollTop();
});

function initRekomendasiPage() {
  if (!document.getElementById("daftarBahan")) return;

  muatBahan();

  const hasil = JSON.parse(localStorage.getItem("hasilScan") || "[]");
  if (hasil.length > 0) {
    hasil.forEach(item => bahanDipilih.add(item.toLowerCase()));
    localStorage.removeItem("hasilScan");

    setTimeout(() => {
      updateBarBahan();
      _aktifkanBahanDariScan();
      cariResep();
    }, 500);
  }
}

async function muatBahan() {
  const kontainer = document.getElementById("daftarBahan");
  if (!kontainer) return;

  try {
    const { data } = await fetch("/api/bahan").then(r => r.json());
    kontainer.innerHTML = "";

    const kategoriList = [
      "Karbohidrat",
      "Sayur",
      "Protein Hewan",
      "Protein Nabati",
      "Bumbu",
      "Rempah",
      "Lainnya",
    ];

    kategoriList
      .filter(kat => data[kat])
      .forEach((kat, index) => {
        const id = kat.replace(/\s+/g, "-").toLowerCase();
        const isFirst = index === 0;
        const item = document.createElement("div");
        item.className = "accordion-item border-0 mb-2";
        item.innerHTML = `
          <h2 class="accordion-header" id="heading-${id}">
            <button
              class="accordion-button rk-accordion-button ${isFirst ? "" : "collapsed"} rounded-3 fw-semibold d-flex justify-content-between align-items-center"
              type="button"
              data-bs-toggle="collapse"
              data-bs-target="#collapse-${id}"
              aria-expanded="${isFirst ? "true" : "false"}"
              aria-controls="collapse-${id}">
              <span class="judul-kategori">${kat}</span>
              <i class="bi bi-chevron-down icon-panah"></i>
            </button>
          </h2>
          <div
            id="collapse-${id}"
            class="accordion-collapse collapse ${isFirst ? "show" : ""}"
            aria-labelledby="heading-${id}"
            data-bs-parent="#daftarBahan">
            <div class="accordion-body pt-2 px-1">
              <div class="bahan-grid">
                ${data[kat].map(b => `
                  <div class="bahan-card" id="bahan-${b.id}" onclick="toggleBahan('${b.nama}', this)">
                    <span class="nama">${b.nama}</span>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>
        `;
        kontainer.appendChild(item);
      });

    _aktifkanBahanDariScan();
  } catch (err) {
    kontainer.innerHTML = `<p class="text-danger small">Gagal memuat bahan: ${err.message}</p>`;
  }
}

function _aktifkanBahanDariScan() {
  if (bahanDipilih.size === 0) return;
  document.querySelectorAll(".bahan-card").forEach(card => {
    const nama = card.querySelector(".nama")?.textContent?.toLowerCase();
    if (nama && bahanDipilih.has(nama)) card.classList.add("aktif");
  });
}

function toggleBahan(nama, card) {
  if (bahanDipilih.has(nama)) {
    bahanDipilih.delete(nama);
    card.classList.remove("aktif");
  } else {
    bahanDipilih.add(nama);
    card.classList.add("aktif");
  }
  updateBarBahan();
}

function hapusBahan(nama) {
  bahanDipilih.delete(nama);
  document.querySelectorAll(".bahan-card .nama").forEach(el => {
    if (el.textContent === nama) el.closest(".bahan-card").classList.remove("aktif");
  });
  updateBarBahan();
}

function resetBahan() {
  bahanDipilih.clear();
  document.querySelectorAll(".bahan-card.aktif").forEach(c => c.classList.remove("aktif"));
  updateBarBahan();

  const konten = document.getElementById("hasilKonten");
  const placeholder = document.getElementById("hasilPlaceholder");
  if (konten) konten.classList.add("d-none");
  if (placeholder) placeholder.classList.remove("d-none");
}

function updateBarBahan() {
  const tagsEl = document.getElementById("bahanTags");
  const btnCari = document.getElementById("btnCari");
  if (!tagsEl || !btnCari) return;

  btnCari.disabled = bahanDipilih.size === 0;
  tagsEl.innerHTML = bahanDipilih.size === 0
    ? `<span class="bahan-tag-empty">Belum ada bahan dipilih - klik ikon di bawah</span>`
    : [...bahanDipilih].map(nama => `
        <span class="bahan-tag">
          ${nama}
          <button onclick="hapusBahan('${nama}')" title="Hapus">x</button>
        </span>
      `).join("");
}

async function cariResep() {
  const konten = document.getElementById("hasilKonten");
  const placeholder = document.getElementById("hasilPlaceholder");
  if (!konten || !placeholder) return;

  placeholder.classList.add("d-none");
  konten.classList.remove("d-none");
  konten.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <p>Mencari resep terbaik untukmu...</p>
    </div>`;

  try {
    const { status, data } = await fetch("/api/rekomendasi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bahan: [...bahanDipilih] }),
    }).then(r => r.json());

    if (status !== "ok" || !data.length) {
      konten.innerHTML = `
        <div class="hasil-placeholder">
          <div class="placeholder-icon">:(</div>
          <h3>Resep tidak ditemukan</h3>
          <p>Coba tambah lebih banyak bahan</p>
        </div>`;
      return;
    }

    tampilkanHasil(data);
  } catch (err) {
    konten.innerHTML = `<p class="text-danger p-3">Error: ${err.message}</p>`;
  }
}

function tampilkanHasil(resepList) {
  const hasilKonten = document.getElementById("hasilKonten");
  if (!hasilKonten) return;

  const rankLabel = ["Terbaik", "Kedua", "Ketiga"];
  const rankClass = ["rank-1", "rank-2", "rank-3"];

  hasilKonten.innerHTML =
    `<div class="hasil-title">
       <i class="bi bi-stars text-warning"></i>
       ${resepList.length} Resep Direkomendasikan
     </div>` +
    resepList.map((resep, i) => `
      <a href="/resep/${resep.id_resep}" class="resep-card">
        <span class="resep-ranking ${rankClass[i] ?? ""}">${rankLabel[i] ?? `#${i + 1}`}</span>
        <div class="resep-header">
          <span class="resep-nama">${resep.nama_resep}</span>
          <span class="resep-kategori">${resep.kategori}</span>
        </div>
        <p class="resep-deskripsi">${resep.deskripsi}</p>
        <div class="resep-meta">
          <div class="skor-bar-wrap">
            <div class="skor-label">Kecocokan bahan</div>
            <div class="skor-bar">
              <div class="skor-bar-fill" style="width:${resep.persen_cocok}%"></div>
            </div>
          </div>
          <span class="skor-persen">${resep.persen_cocok}%</span>
        </div>
        <div class="bahan-badges">
          ${resep.bahan_cocok.map(b => `<span class="badge badge-ada">OK ${b}</span>`).join("")}
          ${resep.bahan_kurang.slice(0, 4).map(b => `<span class="badge badge-kurang">+ ${b}</span>`).join("")}
          ${resep.bahan_kurang.length > 4
            ? `<span class="badge badge-kurang">+${resep.bahan_kurang.length - 4} lagi</span>`
            : ""}
        </div>
      </a>
    `).join("");
}

function filterBahan() {
  const input = document.getElementById("inputCariBahan")?.value.toLowerCase() || "";
  document.querySelectorAll("#daftarBahan .accordion-item").forEach(item => {
    const cards = item.querySelectorAll(".bahan-card");
    let adaYangCocok = false;

    cards.forEach(card => {
      const nama = card.querySelector(".nama").textContent.toLowerCase();
      const cocok = nama.includes(input);
      card.classList.toggle("d-none", !cocok);
      if (cocok) adaYangCocok = true;
    });

    item.classList.toggle("d-none", !adaYangCocok);
    if (adaYangCocok && input.length > 0) {
      const collapse = item.querySelector(".accordion-collapse");
      if (!collapse.classList.contains("show")) {
        item.querySelector(".accordion-button").classList.remove("collapsed");
        collapse.classList.add("show");
      }
    }
  });
}

function initJelajahiPage() {
  if (!document.getElementById("containerKatalogResep")) return;
  jalankanLiveSearch();
}

function jalankanLiveSearch() {
  const input = document.getElementById("inputCariResep");
  const filter = document.getElementById("filterKategori");
  const pesanKosong = document.getElementById("pesanKosong");
  if (!input || !filter || !pesanKosong) return;

  const kataKunci = input.value.toLowerCase().trim();
  const kategoriTerpilih = filter.value.toLowerCase();
  const kartuResep = document.getElementsByClassName("item-kartu-resep");
  let jumlahDitemukan = 0;

  for (const item of kartuResep) {
    const nama = item.getAttribute("data-nama") || "";
    const deskripsi = item.getAttribute("data-deskripsi") || "";
    const kategori = item.getAttribute("data-kategori") || "";
    const cocokTeks = nama.includes(kataKunci) || deskripsi.includes(kataKunci);
    const cocokKategori = kategoriTerpilih === "semua" || kategori === kategoriTerpilih;
    const cocok = cocokTeks && cocokKategori;

    item.classList.toggle("d-flex", cocok);
    item.classList.toggle("d-none", !cocok);
    if (cocok) jumlahDitemukan++;
  }

  pesanKosong.classList.toggle("d-none", jumlahDitemukan > 0);
}

function resetFilter() {
  const input = document.getElementById("inputCariResep");
  const filter = document.getElementById("filterKategori");
  if (input) input.value = "";
  if (filter) filter.value = "semua";
  jalankanLiveSearch();
}

function initScrollTop() {
  const btnTop = document.getElementById("btnTop");
  if (!btnTop) return;

  btnTop.addEventListener("click", scrollKeAtas);
  window.addEventListener("scroll", () => {
    const show = document.documentElement.scrollTop > 200 || document.body.scrollTop > 200;
    btnTop.classList.toggle("show", show);
  });
}

function scrollKeAtas() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadTMModel() {
  if (tmModel) return;
  if (!window.tmImage) throw new Error("Library Teachable Machine belum dimuat.");

  const modelURL = TM_URL + "model.json";
  const metadataURL = TM_URL + "metadata.json";
  tmModel = await tmImage.load(modelURL, metadataURL);
}

async function aktifkanKamera() {
  const video = document.getElementById("videoEl");
  if (!video) return;

  try {
    modeKamera = true;
    setTipsKamera();

    const constraints = {
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    };

    stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = stream;
    await new Promise(resolve => { video.onloadedmetadata = resolve; });
    await video.play();
    await loadTMModel();

    showElement("videoEl");
    hideElement("placeholder-kamera");
    hideElement("btnAktifkan");
    hideElement("btnAmbil");
    document.getElementById("statusDot")?.classList.add("aktif");
    setText("statusTeks", "Kamera aktif - arahkan ke bahan");
    document.getElementById("livePredBar")?.classList.add("show");

    scanRealtime();
  } catch (err) {
    let pesan = "Tidak bisa akses kamera.";
    if (err.name === "NotAllowedError") pesan = "Izin kamera ditolak.";
    if (err.name === "NotFoundError") pesan = "Kamera tidak ditemukan.";
    setCameraPlaceholderError(pesan);
  }
}

function scanRealtime() {
  if (realtimeTimer) clearInterval(realtimeTimer);

  realtimeTimer = setInterval(async () => {
    const video = document.getElementById("videoEl");
    if (!tmModel || !video?.videoWidth || !modeKamera) return;

    const prediction = await tmModel.predict(video);
    const best = prediction.reduce(
      (winner, item) => item.probability > winner.probability ? item : winner,
      prediction[0],
    );

    const nama = best.className;
    const conf = best.probability * 100;
    const isUnknown = isUnknownLabel(nama);

    // ── Update live bar ──
    setText("livePredLabel", isUnknown ? "Objek tidak dikenali" : nama);
    const fill = document.getElementById("livePredFill");
    if (fill) {
      fill.style.width = `${conf.toFixed(0)}%`;
      fill.style.background = isUnknown
        ? "#bbb"
        : conf >= AUTO_ADD_THRESH ? "#00c53b" : "#ffa726";
    }
    setText("livePredConf", `${conf.toFixed(0)}%`);

    // ── Auto-add hanya kalau bukan unknown dan conf cukup ──
    if (isUnknown || conf < AUTO_ADD_THRESH) return;

    const now = Date.now();
    if (now - lastAutoAdd < COOLDOWN_MS) return;

    const namaBersih = nama.replace(/_/g, " ");
    const slug = _slugify(nama);
    if (document.getElementById(`valid-${slug}`)) return;

    lastAutoAdd = now;
    _tambahKeValid(namaBersih, slug, `${conf.toFixed(1)}%`);
    _tampilNotifAutoAdd();
  }, SCAN_INTERVAL);
}

function ambilFoto() {
  const video = document.getElementById("videoEl");
  const canvas = document.getElementById("canvasCapture");
  const preview = document.getElementById("imgPreview");
  if (!video || !canvas || !preview) return;

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  canvas.toBlob(blob => {
    if (!blob || blob.size === 0) return;
    preview.src = URL.createObjectURL(blob);
    hideElement("videoEl");
    showElement("preview-wrapper");
    hideElement("btnAmbil");
    showElement("btnUlang");
    stopCameraStream();
    prediksiTeachableMachine();
  }, "image/jpeg", 0.9);
}

async function prediksiTeachableMachine() {
  const canvas = document.getElementById("canvasCapture");
  if (!canvas) return;

  try {
    showOverlay();
    await loadTMModel();
    const prediction = await tmModel.predict(canvas);
    const best = prediction.reduce(
      (winner, item) => item.probability > winner.probability ? item : winner,
      prediction[0],
    );
    hideOverlay();

    const conf = best.probability * 100;
    if (isUnknownLabel(best.className) || conf < 80) {
      showScanContent();
      document.getElementById("listBahanValid").innerHTML = `
        <div class="tidak-dikenali">
          <i class="bi bi-question-circle scan-empty-icon"></i>
          Objek tidak dikenali
        </div>`;
      document.getElementById("listBahanRagu").innerHTML = "";
      _updateCounter();
      return;
    }

    tampilkanHasilScan({
      bahan_valid: [{ nama: best.className.replace(/_/g, " "), confidence: conf.toFixed(1) }],
      bahan_ragu: [],
      bbox_data: [],
    });
  } catch (err) {
    hideOverlay();
    console.error(err);
    tampilkanError("Gagal menjalankan Teachable Machine");
  }
}

function handleUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    alert("File harus berupa gambar (JPG, PNG, dll).");
    return;
  }

  modeKamera = false;
  stopCameraStream();
  setTipsUpload();

  const preview = document.getElementById("imgPreview");
  if (preview) preview.src = URL.createObjectURL(file);

  hideElement("videoEl");
  hideElement("placeholder-kamera");
  showElement("preview-wrapper");
  document.getElementById("livePredBar")?.classList.remove("show");
  hideElement("btnAktifkan");
  hideElement("btnAmbil");
  hideElement("btnUpload");
  showElement("btnUlang");
  document.getElementById("statusDot")?.classList.add("aktif");
  setText("statusTeks", "Foto dari galeri");

  event.target.value = "";
  kirimKeScan(file);
}

async function kirimKeScan(blob) {
  showOverlay();
  const formData = new FormData();
  formData.append("foto", blob, "foto.jpg");

  try {
    const res = await fetch("/api/scan", { method: "POST", body: formData });
    const data = await res.json();
    hideOverlay();

    if (data.status !== "ok") {
      tampilkanError(data.pesan || "Terjadi kesalahan saat analisa.");
      return;
    }

    hasilScan = data;
    tampilkanHasilScan(data);
    gambarBoundingBox(data.bbox_data);
  } catch (err) {
    hideOverlay();
    tampilkanError("Gagal terhubung ke server: " + err.message);
  }
}

function tampilkanHasilScan(data) {
  showScanContent();
  const valid = dedupeScanItems(data.bahan_valid || []);
  const ragu = dedupeScanItems(data.bahan_ragu || [], new Set(valid.map(b => normalizeName(b.nama))));

  document.getElementById("listBahanValid").innerHTML = valid.map(b => {
    const conf = b.confidence ? `${b.confidence}%` : "100%";
    const slug = _slugify(b.nama);
    return `
      <div class="bahan-item valid" id="valid-${slug}" data-nama="${b.nama}" data-conf="${conf}">
        ${b.nama.replace(/_/g, " ")}
        <span class="badge-conf">${conf}</span>
        <button class="btn-hapus-bahan" title="Hapus" onclick="hapusBahanHasil('${slug}','valid')">x</button>
      </div>`;
  }).join("");

  document.getElementById("listBahanRagu").innerHTML = ragu.map(b => {
    const conf = b.confidence ? `${b.confidence}%` : "-";
    const slug = _slugify(b.nama);
    return `
      <div class="bahan-item ragu" id="ragu-${slug}" data-nama="${b.nama}" data-conf="${conf}">
        ${b.nama.replace(/_/g, " ")}
        <div class="aksi-ragu">
          <button class="btn-yakin" onclick="konfirmasiBahan('${slug}','${b.nama}','${conf}')">OK</button>
          <button class="btn-hapus-bahan" onclick="hapusBahanHasil('${slug}','ragu')">x</button>
        </div>
      </div>`;
  }).join("");

  valid.forEach(b => _aktifkanBahanDiAccordion(b.nama));

  _updateCounter();
}

function dedupeScanItems(items, existing = new Set()) {
  const seen = new Set(existing);
  const unique = [];

  items.forEach(item => {
    const key = normalizeName(item.nama);
    // Buang item kosong atau yang terdeteksi sebagai unknown
    if (!key || isUnknownLabel(key) || seen.has(key)) return;
    seen.add(key);
    unique.push(item);
  });

  return unique;
}

function _tambahKeValid(nama, slug, confStr) {
  if (isUnknownLabel(nama)) return;

  showScanContent();
  document.getElementById("listBahanValid").insertAdjacentHTML("beforeend", `
    <div class="bahan-item valid" id="valid-${slug}" data-nama="${nama}" data-conf="${confStr}">
      ${nama}
      <span class="badge-conf">${confStr}</span>
      <button class="btn-hapus-bahan" title="Hapus" onclick="hapusBahanHasil('${slug}','valid')">x</button>
    </div>`);

  _aktifkanBahanDiAccordion(nama);

  _updateCounter();
}

function _aktifkanBahanDiAccordion(nama) {
  const namaNormal = normalizeName(nama);
  document.querySelectorAll(".bahan-card").forEach(card => {
    const namaCard = normalizeName(card.querySelector(".nama")?.textContent || "");
    if (namaCard === namaNormal) {
      card.classList.add("aktif");
    }
  });
}

function _tampilNotifAutoAdd() {
  const el = document.getElementById("notifAutoAdd");
  if (!el) return;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2500);
}

function _slugify(nama) {
  return String(nama).toLowerCase().replace(/[\s_]+/g, "-").replace(/[^a-z0-9-]/g, "");
}

function konfirmasiBahan(slug, nama, conf) {
  document.getElementById(`ragu-${slug}`)?.remove();
  if (!document.getElementById(`valid-${slug}`)) {
    _tambahKeValid(nama.replace(/_/g, " "), slug, conf);
  }
  _updateCounter();
}

function hapusBahanHasil(slug, dari) {
  document.getElementById(`${dari}-${slug}`)?.remove();
  _updateCounter();
}

function setujuiSemuaRagu() {
  document.querySelectorAll("#listBahanRagu .bahan-item.ragu").forEach(el => {
    const slug = el.id.replace("ragu-", "");
    const nama = el.getAttribute("data-nama");
    const conf = el.getAttribute("data-conf");
    if (!document.getElementById(`valid-${slug}`)) _tambahKeValid(nama.replace(/_/g, " "), slug, conf);
    el.remove();
  });
  _updateCounter();
}

function batalSemuaRagu() {
  const list = document.getElementById("listBahanRagu");
  if (list) list.innerHTML = "";
  _updateCounter();
}

function _updateCounter() {
  // Bersihkan sisa unknown yang lolos masuk DOM
  document.querySelectorAll("#listBahanValid .bahan-item").forEach(el => {
    if (isUnknownLabel(el.dataset.nama || "")) el.remove();
  });

  const jmlValid = document.querySelectorAll("#listBahanValid .bahan-item.valid").length;
  const jmlRagu  = document.querySelectorAll("#listBahanRagu .bahan-item.ragu").length;

  setText("titleValid", `TERDETEKSI (${jmlValid})`);
  setText("titleRagu", `TIDAK YAKIN (${jmlRagu})`);
  toggleElement("headerValid", jmlValid > 0);
  toggleElement("headerRagu", jmlRagu > 0);
  document.getElementById("btnKonfirmasi")?.classList.toggle("show", jmlValid > 0);
  document.getElementById("notifKonfirmasi")?.classList.toggle("show", jmlValid > 0);
}

function konfirmasiDanCariResep() {
  const bahanValid = [];
  document.querySelectorAll("#listBahanValid .bahan-item.valid").forEach(el => {
    const nama = el.getAttribute("data-nama")?.replace(/_/g, " ");
    if (nama && !isUnknownLabel(nama)) bahanValid.push(nama);
  });

  if (bahanValid.length === 0) {
    alert("Tidak ada bahan yang valid untuk dicari resepnya.");
    return;
  }

  localStorage.setItem("hasilScan", JSON.stringify(bahanValid));
  window.location.href = "/?mode=scan";
}

function gambarBoundingBox(bboxData) {
  if (!bboxData || !bboxData.length) return;
  const img = document.getElementById("imgPreview");
  const canvas = document.getElementById("canvasBbox");
  if (!img || !canvas) return;

  img.onload = () => {
    canvas.width  = img.naturalWidth;
    canvas.height = img.naturalHeight;
    canvas.style.width  = "100%";
    canvas.style.height = "100%";
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    bboxData.forEach(item => {
      const { bbox, nama, status, confidence } = item;
      const color = status === "valid" ? "#00c53b" : "#ffa726";
      ctx.strokeStyle = color;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.rect(bbox.x1, bbox.y1, bbox.x2 - bbox.x1, bbox.y2 - bbox.y1);
      ctx.stroke();

      const label = `${nama.replace(/_/g, " ")}${confidence ? " " + confidence + "%" : ""}`;
      ctx.font = "bold 14px Nunito, sans-serif";
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = color;
      ctx.fillRect(bbox.x1, bbox.y1 - 24, tw + 12, 24);
      ctx.fillStyle = "white";
      ctx.fillText(label, bbox.x1 + 6, bbox.y1 - 6);
    });
  };

  if (img.complete) img.onload();
}

function ulangi() {
  hasilScan  = null;
  modeKamera = false;
  stopCameraStream();
  if (realtimeTimer) {
    clearInterval(realtimeTimer);
    realtimeTimer = null;
  }

  hideElement("preview-wrapper");
  showElement("placeholder-kamera");
  hideElement("btnUlang");
  showElement("btnAktifkan");
  showElement("btnUpload");
  showElement("hasilPlaceholder");
  hideElement("hasilKonten");
  document.getElementById("statusDot")?.classList.remove("aktif");
  setText("statusTeks", "Kamera belum aktif");
  document.getElementById("livePredBar")?.classList.remove("show");
  setTipsUpload();

  const canvas = document.getElementById("canvasBbox");
  const ctx = canvas?.getContext("2d");
  if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function tampilkanError(pesan) {
  showScanContent();
  hideElement("headerValid");
  hideElement("headerRagu");
  document.getElementById("listBahanValid").innerHTML = `
    <div class="scan-error">
      <i class="bi bi-exclamation-triangle scan-error-icon"></i>
      <p>${pesan}</p>
    </div>`;
  document.getElementById("listBahanRagu").innerHTML = "";
  document.getElementById("btnKonfirmasi")?.classList.remove("show");
  document.getElementById("notifKonfirmasi")?.classList.remove("show");
}

function setCameraPlaceholderError(pesan) {
  const placeholder = document.getElementById("placeholder-kamera");
  if (!placeholder) return;
  placeholder.innerHTML = `
    <i class="bi bi-exclamation-triangle camera-error-icon"></i>
    <p class="camera-error-text">${pesan}</p>`;
}

function setTipsKamera() {
  const tips = document.getElementById("tipsBox");
  if (!tips) return;
  tips.innerHTML = `
    <i class="bi bi-lightbulb-fill"></i>
    <strong>Tips kamera:</strong>
    Arahkan kamera satu per satu ke bahan Anda.
    Bahan akan otomatis ditambahkan saat keyakinan >= ${AUTO_ADD_THRESH}%.`;
}

function setTipsUpload() {
  const tips = document.getElementById("tipsBox");
  if (!tips) return;
  tips.innerHTML = `
    <i class="bi bi-lightbulb-fill"></i>
    <strong>Tips foto yang baik:</strong>
    Letakkan semua bahan di permukaan datar, pastikan pencahayaan cukup, dan ambil foto lurus dari atas.`;
}

function showScanContent() {
  hideElement("hasilPlaceholder");
  showElement("hasilKonten");
}

function showOverlay() {
  document.getElementById("loading-overlay")?.classList.add("show");
}

function hideOverlay() {
  document.getElementById("loading-overlay")?.classList.remove("show");
}

function stopCameraStream() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }
}

// ── Cek apakah label adalah "unknown" dalam berbagai variasi ──
function isUnknownLabel(value) {
  const name = normalizeName(value);
  return (
    name === "unknow" ||
    name.includes("unknow") ||
    name.includes("unknown") ||
    name.includes("background") ||
    name.includes("tidak")
  );
}

function normalizeName(value) {
  return String(value || "").toLowerCase().replace(/_/g, " ").trim();
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function showElement(id) {
  toggleElement(id, true);
}

function hideElement(id) {
  toggleElement(id, false);
}

function toggleElement(id, show) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle("d-none", !show);
}

Object.assign(window, {
  aktifkanKamera,
  ambilFoto,
  batalSemuaRagu,
  cariResep,
  filterBahan,
  handleUpload,
  hapusBahan,
  hapusBahanHasil,
  jalankanLiveSearch,
  konfirmasiBahan,
  konfirmasiDanCariResep,
  resetBahan,
  resetFilter,
  scrollKeAtas,
  setujuiSemuaRagu,
  toggleBahan,
  ulangi,
});