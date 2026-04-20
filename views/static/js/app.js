// ============  State aplikasi ============ 
let bahanDipilih = new Set();   // Menyimpan nama bahan yang sudah diklik


// ============  Saat halaman selesai dimuat, ambil data bahan dari API ============ 
document.addEventListener("DOMContentLoaded", () => {
  muatBahan();
});


// ============ Muat semua bahan dari API backend ============
async function muatBahan() {
  try {
    const res = await fetch("/api/bahan");
    const json = await res.json();

    const kontainer = document.getElementById("daftarBahan");
    kontainer.innerHTML = "";

    const urutanKategori = ["Protein", "Karbohidrat", "Sayuran", "Bumbu", "Protein Nabati", "Buah"];
    const data = json.data;

    urutanKategori.forEach(kat => {
      if (!data[kat]) return;

      const section = document.createElement("div");
      section.className = "kategori-section";

      const header = document.createElement("div");
      header.className = "kategori-header";
      header.innerHTML = `<span class="kategori-nama">${kat}</span>`;
      section.appendChild(header);

      const grid = document.createElement("div");
      grid.className = "bahan-grid";

      data[kat].forEach(bahan => {
        const card = document.createElement("div");
        card.className = "bahan-card";
        card.id = `bahan-${bahan.id}`;
        card.innerHTML = `
          <span class="ikon">${bahan.emoji}</span>
          <span class="nama">${bahan.nama}</span>
        `;
        card.onclick = () => toggleBahan(bahan.nama, card);
        grid.appendChild(card);
      });

      section.appendChild(grid);
      kontainer.appendChild(section);
    });

  } catch (err) {
    document.getElementById("daftarBahan").innerHTML =
      `<p style="color:red">Gagal memuat bahan: ${err.message}</p>`;
  }
}


// ============ Toggle pilih/hapus bahan ============
function toggleBahan(namaBahan, cardEl) {
  if (bahanDipilih.has(namaBahan)) {
    bahanDipilih.delete(namaBahan);
    cardEl.classList.remove("aktif");
  } else {
    bahanDipilih.add(namaBahan);
    cardEl.classList.add("aktif");
  }
  updateBarBahan();
}


// ============ Perbarui tampilan bar bahan yang dipilih ============
function updateBarBahan() {
  const tagsEl  = document.getElementById("bahanTags");
  const btnCari = document.getElementById("btnCari");

  tagsEl.innerHTML = "";

  if (bahanDipilih.size === 0) {
    tagsEl.innerHTML = `<span class="bahan-tag-empty">Belum ada bahan dipilih — klik ikon di bawah</span>`;
    btnCari.disabled = true;
    return;
  }

  btnCari.disabled = false;

  bahanDipilih.forEach(nama => {
    const tag = document.createElement("span");
    tag.className = "bahan-tag";
    tag.innerHTML = `
      ${nama}
      <button onclick="hapusBahan('${nama}')" title="Hapus">✕</button>
    `;
    tagsEl.appendChild(tag);
  });
}


// ── Hapus bahan dari pilihan ──
function hapusBahan(namaBahan) {
  bahanDipilih.delete(namaBahan);

  // Hilangkan highlight dari card
  document.querySelectorAll(".bahan-card").forEach(card => {
    const namaEl = card.querySelector(".nama");
    if (namaEl && namaEl.textContent === namaBahan) {
      card.classList.remove("aktif");
    }
  });

  updateBarBahan();
}


// ============ Reset semua pilihan ============
function resetBahan() {
  bahanDipilih.clear();
  document.querySelectorAll(".bahan-card.aktif").forEach(c => c.classList.remove("aktif"));
  updateBarBahan();

  // Sembunyikan hasil
  document.getElementById("hasilKonten").style.display = "none";
  document.getElementById("hasilPlaceholder").style.display = "block";
}


// ============ Kirim request ke API dan tampilkan hasil ============
async function cariResep() {
  const placeholder = document.getElementById("hasilPlaceholder");
  const konten      = document.getElementById("hasilKonten");

  placeholder.style.display = "none";
  konten.style.display = "block";
  konten.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <p>Mencari resep terbaik untukmu...</p>
    </div>
  `;

  try {
    const res = await fetch("/api/rekomendasi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bahan: Array.from(bahanDipilih) })
    });

    const json = await res.json();

    if (json.status !== "ok" || json.data.length === 0) {
      konten.innerHTML = `
        <div class="hasil-placeholder">
          <div class="placeholder-icon">😕</div>
          <h3>Resep tidak ditemukan</h3>
          <p>Coba tambah lebih banyak bahan</p>
        </div>
      `;
      return;
    }

    tampilkanHasil(json.data);

  } catch (err) {
    konten.innerHTML = `<p style="color:red;padding:20px">Error: ${err.message}</p>`;
  }
}


// ============ Render kartu resep ============
function tampilkanHasil(resepList) {
  const konten = document.getElementById("hasilKonten");

  const rankLabel = ["🥇 Terbaik", "🥈 Kedua", "🥉 Ketiga"];
  const rankClass = ["rank-1", "rank-2", "rank-3"];

  let html = `<div class="hasil-title">✨ ${resepList.length} Resep Direkomendasikan</div>`;

  resepList.forEach((resep, i) => {
    const rankText  = i < 3 ? rankLabel[i] : `#${i + 1}`;
    const rankCls   = i < 3 ? rankClass[i] : "";
    const persenBar = resep.persen_cocok;

    const badgeAda = resep.bahan_cocok
      .map(b => `<span class="badge badge-ada">✓ ${b}</span>`)
      .join("");

    const badgeKurang = resep.bahan_kurang.slice(0, 4)
      .map(b => `<span class="badge badge-kurang">+ ${b}</span>`)
      .join("");

    const lebih = resep.bahan_kurang.length > 4
      ? `<span class="badge badge-kurang">+${resep.bahan_kurang.length - 4} lagi</span>`
      : "";

    html += `
      <div class="resep-card" onclick="this.classList.toggle('expanded')">
        <span class="resep-ranking ${rankCls}">${rankText}</span>
        <div class="resep-header">
          <span class="resep-nama">${resep.nama_resep}</span>
          <span class="resep-kategori">${resep.kategori}</span>
        </div>
        <p class="resep-deskripsi">${resep.deskripsi}</p>
        <div class="resep-meta">
          <div class="skor-bar-wrap">
            <div class="skor-label">Kecocokan bahan</div>
            <div class="skor-bar">
              <div class="skor-bar-fill" style="width:${persenBar}%"></div>
            </div>
          </div>
          <span class="skor-persen">${persenBar}%</span>
        </div>
        <div class="bahan-badges">
          ${badgeAda}
          ${badgeKurang}
          ${lebih}
        </div>
      </div>
    `;
  });

  konten.innerHTML = html;

  // Animasi bar setelah render
  setTimeout(() => {
    document.querySelectorAll(".skor-bar-fill").forEach(el => {
      el.style.width = el.style.width;
    });
  }, 50);
}
