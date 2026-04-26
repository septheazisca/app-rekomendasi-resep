let bahanDipilih = new Set();

document.addEventListener("DOMContentLoaded", muatBahan);

// Ambil & render semua bahan dari API
async function muatBahan() {
  try {
    const { data } = await fetch("/api/bahan").then(r => r.json());
    const kontainer = document.getElementById("daftarBahan");
    kontainer.innerHTML = "";

    const kategoriList = ["Protein","Karbohidrat","Sayuran","Bumbu","Protein Nabati","Buah"];

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
              class="accordion-button ${isFirst ? '' : 'collapsed'} rounded-3 fw-semibold d-flex justify-content-between align-items-center"
              type="button"
              data-bs-toggle="collapse"
              data-bs-target="#collapse-${id}"
              aria-expanded="${isFirst ? 'true' : 'false'}"
              aria-controls="collapse-${id}"
              style="background-color: #80F6A3; color: #1a1a1a; box-shadow: none; padding: 12px 16px;">

              <span class="judul-kategori">${kat}</span>
              <i class="bi bi-chevron-down icon-panah"></i>

            </button>
          </h2>
          <div
            id="collapse-${id}"
            class="accordion-collapse collapse ${isFirst ? 'show' : ''}"
            aria-labelledby="heading-${id}"
            data-bs-parent="#daftarBahan">
            <div class="accordion-body pt-2 px-1">
              <div class="bahan-grid">
                ${data[kat].map(b => `
                  <div class="bahan-card" id="bahan-${b.id}" onclick="toggleBahan('${b.nama}', this)">
                    <span class="ikon">${b.emoji}</span>
                    <span class="nama">${b.nama}</span>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>
        `;
        kontainer.appendChild(item);
      });

  } catch (err) {
    document.getElementById("daftarBahan").innerHTML =
      `<p style="color:red">Gagal memuat bahan: ${err.message}</p>`;
  }
}

//  Pilih/batalkan bahan saat diklik
function toggleBahan(nama, card) {
  bahanDipilih[bahanDipilih.has(nama) ? "delete" : "add"](nama);
  card.classList.toggle("aktif");
  updateBarBahan();
}

// Hapus 1 bahan dari pilihan via tag
function hapusBahan(nama) {
  bahanDipilih.delete(nama);
  document.querySelectorAll(".bahan-card .nama")
    .forEach(el => el.textContent === nama && el.closest(".bahan-card").classList.remove("aktif"));
  updateBarBahan();
}

// Bersihkan semua pilihan & tampilan
function resetBahan() {
  bahanDipilih.clear();
  document.querySelectorAll(".bahan-card.aktif").forEach(c => c.classList.remove("aktif"));
  updateBarBahan();
  document.getElementById("hasilKonten").style.display = "none";
  document.getElementById("hasilPlaceholder").style.display = "block";
}

// Sinkronkan bar tags dengan state terkini
function updateBarBahan() {
  const tagsEl  = document.getElementById("bahanTags");
  const btnCari = document.getElementById("btnCari");
  btnCari.disabled = bahanDipilih.size === 0;

  tagsEl.innerHTML = bahanDipilih.size === 0
    ? `<span class="bahan-tag-empty">Belum ada bahan dipilih — klik ikon di bawah</span>`
    : [...bahanDipilih].map(nama => `
        <span class="bahan-tag">
          ${nama}
          <button onclick="hapusBahan('${nama}')" title="Hapus">✕</button>
        </span>
      `).join("");
}

// Kirim bahan ke backend, tunggu hasil
async function cariResep() {
  const konten = document.getElementById("hasilKonten");
  document.getElementById("hasilPlaceholder").style.display = "none";
  konten.style.display = "block";
  konten.innerHTML = `<div class="loading"><div class="spinner"></div><p>Mencari resep terbaik untukmu...</p></div>`;

  try {
    const { status, data } = await fetch("/api/rekomendasi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bahan: [...bahanDipilih] })
    }).then(r => r.json());

    if (status !== "ok" || !data.length) {
      konten.innerHTML = `
        <div class="hasil-placeholder">
          <div class="placeholder-icon">😕</div>
          <h3>Resep tidak ditemukan</h3>
          <p>Coba tambah lebih banyak bahan</p>
        </div>`;
      return;
    }
    tampilkanHasil(data);

  } catch (err) {
    konten.innerHTML = `<p style="color:red;padding:20px">Error: ${err.message}</p>`;
  }
}

// Render kartu resep dari response
function tampilkanHasil(resepList) {
  const rankLabel = ["🥇 Terbaik","🥈 Kedua","🥉 Ketiga"];
  const rankClass = ["rank-1","rank-2","rank-3"];

  document.getElementById("hasilKonten").innerHTML =
    `<div class="hasil-title"><i class="bi bi-stars" style="color: orange;"></i> ${resepList.length} Resep Direkomendasikan</div>` +
    resepList.map((resep, i) => `
      <div class="resep-card" onclick="this.classList.toggle('expanded')">
        <span class="resep-ranking ${rankClass[i] ?? ""}">${rankLabel[i] ?? `#${i+1}`}</span>
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
          ${resep.bahan_cocok.map(b => `<span class="badge badge-ada">✓ ${b}</span>`).join("")}
          ${resep.bahan_kurang.slice(0,4).map(b => `<span class="badge badge-kurang">+ ${b}</span>`).join("")}
          ${resep.bahan_kurang.length > 4 ? `<span class="badge badge-kurang">+${resep.bahan_kurang.length-4} lagi</span>` : ""}
        </div>
      </div>
    `).join("");
}