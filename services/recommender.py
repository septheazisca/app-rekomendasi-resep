import pandas as pd # Membaca file CSV
from sklearn.feature_extraction.text import TfidfVectorizer # Tools scikit-learn, mengubah teks bahan menjadi angka (vector)
from sklearn.metrics.pairwise import cosine_similarity # Tools scikit-learn, menghitung kemiripan antara bahan pilihan user dengan resep


# ============ Membaca dataset CVS ============ #
# Baca fiel resep.csv & resep.cvs
df_resep = pd.read_csv("data/resep.csv")
df_bahan = pd.read_csv("data/resep_bahan.csv")
# Gabungkan kedua tabel menjadi satu tabel berdasarkan id_resep dan nama_resep
df = pd.merge(df_resep, df_bahan, on=["id_resep", "nama_resep"])


# ============ Buat model TF-IDF ============ #
# TF-IDF mengubah teks bahan menjadi angka agar bisa dihitung kemiripannya
vectorizer = TfidfVectorizer(tokenizer=lambda x: [b.strip() for b in x.split(",")])
tfidf_matrix = vectorizer.fit_transform(df["bahan_utama"])


# ============ Fungsi rekomendasi ============ #
def rekomendasikan(bahan_dipilih: list, top_n: int = 5) -> list:
    if not bahan_dipilih:
        return []

    # Ubah bahan pilihan user menjadi satu string
    query = ", ".join([b.lower().strip() for b in bahan_dipilih])

    # Ubah query ke vektor TF-IDF yang sama dengan dataset
    query_vec = vectorizer.transform([query])

    # Hitung cosine similarity antara query dan semua resep
    skor = cosine_similarity(query_vec, tfidf_matrix).flatten()

    # Ambil indeks resep dengan skor tertinggi
    indeks_terbaik = skor.argsort()[::-1][:top_n]

    hasil = []
    for idx in indeks_terbaik:
        if skor[idx] == 0:
            continue # Lewati resep yang sama sekali tidak cocok

        resep = df.iloc[idx]
        bahan_list = [b.strip() for b in resep["bahan_utama"].split(",")]
        
        # Hitung berapa bahan yang dimiliki user cocok dengan resep ini
        bahan_cocok  = [b for b in bahan_list if b.lower() in [x.lower() for x in bahan_dipilih]]
        bahan_kurang = [b for b in bahan_list if b.lower() not in [x.lower() for x in bahan_dipilih]]

        hasil.append({
            "id_resep"     : int(resep["id_resep"]),
            "nama_resep"   : resep["nama_resep"],
            "kategori"     : resep["kategori"],
            "deskripsi"    : resep["deskripsi"],
            "skor"         : round(float(skor[idx]), 4),
            "persen_cocok" : round(len(bahan_cocok) / len(bahan_list) * 100),
            "bahan_cocok"  : bahan_cocok,
            "bahan_kurang" : bahan_kurang,
            "total_bahan"  : len(bahan_list),
        })

    return hasil