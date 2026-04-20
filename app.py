from flask import Flask, request, jsonify, render_template
import sys
import os

# Tambahkan folder backend ke path agar bisa import recommender
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services"))
from recommender import rekomendasikan, df_bahan, df_resep

app = Flask(
    __name__,
    template_folder="views/templates",
    static_folder="views/static"
)


# ── Halaman Utama ──
@app.route("/")
def index():
    return render_template("index.html")


# ── API: Ambil semua bahan berdasarkan kategori ──
@app.route("/api/bahan")
def get_bahan():
    """
    Mengembalikan semua bahan yang tersedia, dikelompokkan per kategori.
    Dibaca dinamis dari data/bahan.csv — tinggal edit CSV untuk tambah/ubah bahan.
    """
    import csv

    bahan_list = []
    with open("data/bahan.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bahan_list.append({
                "id"      : int(row["id"]),
                "nama"    : row["nama"],
                "kategori": row["kategori"],
                "emoji"   : row["emoji"],
            })

    # Kelompokkan berdasarkan kategori
    kategori_dict = {}
    for b in bahan_list:
        kat = b["kategori"]
        if kat not in kategori_dict:
            kategori_dict[kat] = []
        kategori_dict[kat].append(b)

    return jsonify({"status": "ok", "data": kategori_dict})


# ── API: Rekomendasikan resep berdasarkan bahan dipilih ──
@app.route("/api/rekomendasi", methods=["POST"])
def get_rekomendasi():
    """
    Menerima POST JSON: {"bahan": ["ayam", "bawang putih", "kecap manis"]}
    Mengembalikan daftar resep yang direkomendasikan.
    """
    data = request.get_json()

    if not data or "bahan" not in data:
        return jsonify({"status": "error", "pesan": "Kirim data JSON dengan key 'bahan'"}), 400

    bahan_dipilih = data["bahan"]

    if len(bahan_dipilih) == 0:
        return jsonify({"status": "error", "pesan": "Pilih minimal 1 bahan"}), 400

    hasil = rekomendasikan(bahan_dipilih, top_n=6)

    if not hasil:
        return jsonify({
            "status": "ok",
            "pesan": "Tidak ada resep yang cocok dengan bahan tersebut",
            "data": []
        })

    return jsonify({
        "status": "ok",
        "bahan_dipilih": bahan_dipilih,
        "jumlah_hasil": len(hasil),
        "data": hasil
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
