import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1. Load Data
df_resep = pd.read_csv("data/resep.csv", sep=";")
df_bahan = pd.read_csv("data/resep_bahan.csv")
df = pd.merge(df_resep, df_bahan, on=["id_resep", "nama_resep"])

# 2. Inisialisasi TF-IDF Vectorizer
vectorizer = TfidfVectorizer(
    tokenizer=lambda x: [bahan.strip().lower() for bahan in x.split(",")],
    lowercase=True,
    token_pattern=None,
)
tfidf_matrix = vectorizer.fit_transform(df["bahan_utama"])


def _hitung_skor_gabungan(cosine, persen_cocok, bobot_cosine=0.4, bobot_persen=0.6):
    """Menghitung nilai kombinasi antara Cosine Similarity dan Persentase Kecocokan Bahan"""
    return round(float(cosine * bobot_cosine) + float(persen_cocok / 100 * bobot_persen), 4)


def _bangun_hasil(resep, cosine, bahan_dipilih):
    bahan_dipilih_lower = [b.lower() for b in bahan_dipilih]

    bahan_list   = [b.strip() for b in resep["bahan_utama"].split(",")]
    bahan_cocok  = [b for b in bahan_list if b.lower() in bahan_dipilih_lower]
    bahan_kurang = [b for b in bahan_list if b.lower() not in bahan_dipilih_lower]
    
    # Persentase murni berdasarkan rasio jumlah bahan
    persen_cocok = round(len(bahan_cocok) / len(bahan_list) * 100)

    # Hitung skor gabungan terlebih dahulu
    skor_gabungan = _hitung_skor_gabungan(cosine, persen_cocok)

    # Mengubah skor gabungan menjadi skala persen (0-100) untuk ditampilkan di UI aplikasi
    persen_tampilan = int(skor_gabungan * 100)

    bahan_lengkap_list = [b.strip() for b in str(resep["bahan_lengkap"]).split(",")]

    return {
        "id_resep"        : int(resep["id_resep"]),
        "nama_resep"      : str(resep["nama_resep"]),
        "kategori"        : str(resep["kategori"]),
        "deskripsi"       : str(resep["deskripsi"]),
        "skor_cosine"     : round(float(cosine), 4),
        "persen_cocok"    : int(persen_cocok),     # Persen rasio bahan (tetap disimpan untuk kebutuhan data)
        "persen_tampilan" : persen_tampilan,       # Gunakan KEY INI di UI/FE kamu agar urutan angkanya logis
        "skor_gabungan"   : skor_gabungan,
        "bahan_cocok"     : bahan_cocok,
        "bahan_kurang"    : bahan_kurang,
        "bahan_lengkap"   : bahan_lengkap_list,
        "total_bahan"     : len(bahan_list),
    }


def rekomendasikan(bahan_dipilih: list, top_n: int = 5) -> list:
    if not bahan_dipilih:
        return []

    bahan_lower = [b.lower() for b in bahan_dipilih]

    # Layer 1: TF-IDF cosine similarity 
    query     = ", ".join(bahan_lower)
    query_vec = vectorizer.transform([query])
    skor      = cosine_similarity(query_vec, tfidf_matrix).flatten()

    # Layer 2: Fallback — exact match minimal 1 bahan 
    def ada_bahan_cocok(bahan_utama_str):
        bahan_resep = [b.strip().lower() for b in bahan_utama_str.split(",")]
        return any(b in bahan_resep for b in bahan_lower)

    mask_cocok = df["bahan_utama"].apply(ada_bahan_cocok)

    # Gabungkan indeks yang lolos TF-IDF (skor > 0) ATAU exact match
    indeks_tfidf = set(i for i in range(len(skor)) if skor[i] > 0)
    indeks_exact = set(df[mask_cocok].index.tolist())
    indeks_valid  = indeks_tfidf | indeks_exact

    if not indeks_valid:
        return []

    # Membangun objek data hasil rekomendasi
    kandidat = [_bangun_hasil(df.iloc[i], skor[i], bahan_dipilih) for i in indeks_valid]
    
    # Tetap diurutkan berdasarkan skor_gabungan (bobot algoritma yang akurat)
    kandidat.sort(key=lambda x: x["skor_gabungan"], reverse=True)
    
    return kandidat[:top_n]


# === CONTOH PENGGUNAAN ===
if __name__ == "__main__":
    # Misal bahan yang dipunyai user
    bahan_saya = ["Udang", "Cabai Merah", "Tomat"]
    
    hasil_rekomendasi = rekomendasikan(bahan_saya, top_n=3)
    
    for idx, r in enumerate(hasil_rekomendasi, 1):
        print(f"Peringkat {idx}: {r['nama_resep']}")
        print(f"  -> Persen Bahan Asli : {r['persen_cocok']}%")
        print(f"  -> Persen Tampilan UI: {r['persen_tampilan']}%")
        print(f"  -> Skor Gabungan     : {r['skor_gabungan']}")
        print("-" * 40)