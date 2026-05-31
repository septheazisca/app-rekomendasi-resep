import csv
import os
import sys
import uuid

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from recommender import rekomendasikan  # noqa: E402
from vision_service import proses_foto  # noqa: E402

UPLOAD_FOLDER = os.path.join(BASE_DIR, "views", "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(
    __name__,
    template_folder="views/templates",
    static_folder="views/static",
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


@app.route("/")
def index():
    return render_template("index.html", halaman="index")


@app.route("/scan")
def scan():
    return render_template("scan.html")


@app.route("/jelajahi")
def jelajahi():
    df = pd.read_csv("data/resep.csv", sep=";")
    daftar_resep = df.to_dict(orient="records")
    daftar_kategori = sorted(df["kategori"].dropna().unique().tolist())

    return render_template(
        "jelajahi.html",
        daftar_resep=daftar_resep,
        daftar_kategori=daftar_kategori,
        halaman="jelajah",
    )


@app.route("/resep/<int:id_resep>")
def detail_resep(id_resep):
    df       = pd.read_csv("data/resep.csv", sep=";")
    df_bahan = pd.read_csv("data/resep_bahan.csv")

    resep = df[df["id_resep"] == id_resep]
    if resep.empty:
        return "Resep tidak ditemukan", 404
    resep = resep.iloc[0]

    langkah_list = [l.strip() for l in resep["langkah"].split("|")]

    bahan_baris = df_bahan[df_bahan["id_resep"] == id_resep]
    if not bahan_baris.empty:
        # ← Pakai bahan_lengkap (dengan takaran) untuk tampil di halaman detail
        bahan_list = [b.strip() for b in bahan_baris.iloc[0]["bahan_lengkap"].split(",")]
    else:
        bahan_list = []

    return render_template("detail.html",
        id_resep   = int(resep["id_resep"]),
        nama_resep = resep["nama_resep"],
        kategori   = resep["kategori"],
        deskripsi  = resep["deskripsi"],
        bahan      = bahan_list,
        langkah    = langkah_list,
        halaman    = "detail"
    )

@app.route("/api/bahan")
def get_bahan():
    bahan_list = []
    with open("data/bahan.csv", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter=";")
        for row in reader:
            bahan_list.append({
                "id": int(row["id"]),
                "nama": row["nama"],
                "kategori": row["kategori"],
            })

    kategori_dict = {}
    for bahan in bahan_list:
        kategori_dict.setdefault(bahan["kategori"], []).append(bahan)

    return jsonify({"status": "ok", "data": kategori_dict})


@app.route("/api/rekomendasi", methods=["POST"])
def get_rekomendasi():
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
            "data": [],
        })

    return jsonify({
        "status": "ok",
        "bahan_dipilih": bahan_dipilih,
        "jumlah_hasil": len(hasil),
        "data": hasil,
    })


@app.route("/api/scan", methods=["POST"])
def api_scan():
    if "foto" not in request.files:
        return jsonify({"status": "error", "pesan": "Tidak ada file foto"}), 400

    file = request.files["foto"]
    if file.filename == "":
        return jsonify({"status": "error", "pesan": "File kosong"}), 400

    image_bytes = file.read()
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    nama_file = f"{uuid.uuid4().hex}{ext}"
    path_file = os.path.join(UPLOAD_FOLDER, nama_file)

    with open(path_file, "wb") as output:
        output.write(image_bytes)

    hasil = proses_foto(image_bytes)
    hasil["foto_url"] = f"/static/uploads/{nama_file}"

    return jsonify({"status": "ok", **hasil})


@app.route("/api/scan-result", methods=["POST"])
def api_scan_result():
    if "foto" not in request.files:
        return jsonify({"status": "error", "pesan": "Tidak ada file foto"}), 400

    image_bytes = request.files["foto"].read()
    hasil_scan = proses_foto(image_bytes)
    bahan_valid = [bahan["nama"] for bahan in hasil_scan.get("bahan_valid", [])]
    rekomendasi = rekomendasikan(bahan_valid, top_n=6) if bahan_valid else []

    return jsonify({
        "status": "ok",
        "scan": hasil_scan,
        "rekomendasi": rekomendasi,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
