import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

df_resep = pd.read_csv("data/resep.csv", sep=";")
df_bahan = pd.read_csv("data/resep_bahan.csv")
df = pd.merge(df_resep, df_bahan, on=["id_resep", "nama_resep"])

vectorizer = TfidfVectorizer(
    tokenizer=lambda x: [bahan.strip().lower() for bahan in x.split(",")],
    lowercase=True,
    token_pattern=None,
)
tfidf_matrix = vectorizer.fit_transform(df["bahan_utama"])


def _hitung_skor_gabungan(
    cosine: float,
    persen_cocok: float,
    bobot_cosine: float = 0.4,
    bobot_persen: float = 0.6,
) -> float:
    return round((cosine * bobot_cosine) + (persen_cocok / 100 * bobot_persen), 4)


def _bangun_hasil(resep, cosine: float, bahan_dipilih: list) -> dict:
    bahan_dipilih_lower = [bahan.lower() for bahan in bahan_dipilih]
    bahan_list = [bahan.strip() for bahan in resep["bahan_utama"].split(",")]

    bahan_cocok = [bahan for bahan in bahan_list if bahan.lower() in bahan_dipilih_lower]
    bahan_kurang = [bahan for bahan in bahan_list if bahan.lower() not in bahan_dipilih_lower]
    persen_cocok = round(len(bahan_cocok) / len(bahan_list) * 100)

    return {
        "id_resep": int(resep["id_resep"]),
        "nama_resep": resep["nama_resep"],
        "kategori": resep["kategori"],
        "deskripsi": resep["deskripsi"],
        "skor_cosine": round(float(cosine), 4),
        "persen_cocok": persen_cocok,
        "skor_gabungan": _hitung_skor_gabungan(cosine, persen_cocok),
        "bahan_cocok": bahan_cocok,
        "bahan_kurang": bahan_kurang,
        "total_bahan": len(bahan_list),
    }


def rekomendasikan(bahan_dipilih: list, top_n: int = 5) -> list:
    if not bahan_dipilih:
        return []

    query = ", ".join([bahan.lower() for bahan in bahan_dipilih])
    query_vec = vectorizer.transform([query])
    skor_cosine = cosine_similarity(query_vec, tfidf_matrix).flatten()

    pool_size = min(top_n * 2, len(df))
    indeks_kandidat = skor_cosine.argsort()[::-1][:pool_size]
    indeks_valid = [i for i in indeks_kandidat if skor_cosine[i] > 0]

    kandidat = [
        _bangun_hasil(df.iloc[i], skor_cosine[i], bahan_dipilih)
        for i in indeks_valid
    ]
    kandidat.sort(key=lambda x: x["skor_gabungan"], reverse=True)

    return kandidat[:top_n]
