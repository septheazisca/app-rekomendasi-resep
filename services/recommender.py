import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============ Data Loader — Baca & gabungkan dataset CSV ============
df_resep = pd.read_csv("data/resep.csv", sep=";")
df_bahan = pd.read_csv("data/resep_bahan.csv")
df       = pd.merge(df_resep, df_bahan, on=["id_resep", "nama_resep"])


# ============ Model Builder — Buat model TF-IDF dari kolom bahan_utama ============
vectorizer  = TfidfVectorizer(tokenizer=lambda x: [b.strip() for b in x.split(",")])
tfidf_matrix = vectorizer.fit_transform(df["bahan_utama"])


# ============ Score Calculator — Hitung skor gabungan cosine + persen cocok ============
def _hitung_skor_gabungan(cosine: float, persen_cocok: float,
                           bobot_cosine: float = 0.4,
                           bobot_persen: float  = 0.6) -> float:
    return round((cosine * bobot_cosine) + (persen_cocok / 100 * bobot_persen), 4)


# ============ Result Builder — Susun dict hasil untuk satu resep ============
def _bangun_hasil(resep, cosine: float, bahan_dipilih: list) -> dict:
    bahan_dipilih_lower = [b.lower() for b in bahan_dipilih]
    bahan_list  = [b.strip() for b in resep["bahan_utama"].split(",")]

    bahan_cocok  = [b for b in bahan_list if b.lower() in bahan_dipilih_lower]
    bahan_kurang = [b for b in bahan_list if b.lower() not in bahan_dipilih_lower]

    persen_cocok = round(len(bahan_cocok) / len(bahan_list) * 100)
    skor_gabungan = _hitung_skor_gabungan(cosine, persen_cocok)

    return {
        "id_resep"      : int(resep["id_resep"]),
        "nama_resep"    : resep["nama_resep"],
        "kategori"      : resep["kategori"],
        "deskripsi"     : resep["deskripsi"],
        "skor_cosine"   : round(float(cosine), 4),
        "persen_cocok"  : persen_cocok,
        "skor_gabungan" : skor_gabungan,          # skor final untuk sorting
        "bahan_cocok"   : bahan_cocok,
        "bahan_kurang"  : bahan_kurang,
        "total_bahan"   : len(bahan_list),
    }


# ============ Main Recommender — Fungsi utama yang dipanggil oleh API ============
def rekomendasikan(bahan_dipilih: list, top_n: int = 5) -> list:
    if not bahan_dipilih:
        return []

    # 1. Query → vektor TF-IDF
    query     = ", ".join([b.lower().strip() for b in bahan_dipilih])
    query_vec = vectorizer.transform([query])

    # 2. Cosine similarity semua resep
    skor_cosine = cosine_similarity(query_vec, tfidf_matrix).flatten()

    # 3. Kandidat awal (pool 2× top_n, buang skor 0)
    pool_size      = min(top_n * 2, len(df))
    indeks_kandidat = skor_cosine.argsort()[::-1][:pool_size]
    indeks_valid    = [i for i in indeks_kandidat if skor_cosine[i] > 0]

    # 4. Bangun hasil & hitung skor gabungan
    kandidat = [
        _bangun_hasil(df.iloc[i], skor_cosine[i], bahan_dipilih)
        for i in indeks_valid
    ]

    # 5. Sort ulang berdasarkan skor_gabungan, ambil top_n
    kandidat.sort(key=lambda x: x["skor_gabungan"], reverse=True)
    return kandidat[:top_n]