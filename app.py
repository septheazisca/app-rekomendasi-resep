import csv
import os
import sys
import uuid

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(BASE_DIR, "services"))
sys.path.insert(0, os.path.join(BASE_DIR, "model"))

from recommender import rekomendasikan  # noqa: E402
from vision_service import proses_foto  # noqa: E402
from fitur_klasifikasi import predict_ingredient  # noqa: E402

UPLOAD_FOLDER = os.path.join(BASE_DIR, "views", "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(
    __name__,
    template_folder="views/templates",
    static_folder="views/static",
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html", halaman="index")


@app.route("/scan")
def scan():
    return render_template("scan.html")


@app.route("/klasifikasi_bahan")
def scan_kalsifikasi():
    return render_template("klasifikasi_bahan.html")


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
    df        = pd.read_csv("data/resep.csv", sep=";")
    df_bahan  = pd.read_csv("data/resep_bahan.csv")
    df_sumber = pd.read_csv("data/sumber.csv")

    resep = df[df["id_resep"] == id_resep]
    if resep.empty:
        return "Resep tidak ditemukan", 404
    resep = resep.iloc[0]

    langkah_list = [l.strip() for l in resep["langkah"].split("|")]

    bahan_baris = df_bahan[df_bahan["id_resep"] == id_resep]
    if not bahan_baris.empty:
        bahan_list = [
            b.strip()
            for b in bahan_baris.iloc[0]["bahan_lengkap"].split(",")
        ]
    else:
        bahan_list = []

    sumber_baris = df_sumber[df_sumber["id_resep"] == id_resep]
    if not sumber_baris.empty:
        sumber = sumber_baris.iloc[0]["url"]
    else:
        sumber = "-"

    return render_template(
        "detail.html",
        id_resep=int(resep["id_resep"]),
        nama_resep=resep["nama_resep"],
        kategori=resep["kategori"],
        deskripsi=resep["deskripsi"],
        bahan=bahan_list,
        langkah=langkah_list,
        sumber=sumber,
        halaman="detail"
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


# --- FITUR TAMBAHAN BARU: API KLASIFIKASI MODEL H5 ---
@app.route("/api/klasifikasi", methods=["POST"])
def api_klasifikasi():
    if 'file' not in request.files:
        return jsonify({"status": "error", "pesan": "Tidak ada bagian file dalam request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "pesan": "Tidak ada file yang dipilih"}), 400
    
    if file and allowed_file(file.filename):
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        filename = f"h5_{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            bahan_info = predict_ingredient(filepath)
            
            if bahan_info:
                return jsonify({"status": "ok", "data": bahan_info})
            else:
                return jsonify({"status": "error", "pesan": "Gagal mengklasifikasi bahan makanan."}), 500
        except Exception as e:
            return jsonify({"status": "error", "pesan": f"Terjadi kesalahan model: {str(e)}"}), 500

    return jsonify({"status": "error", "pesan": "Format file tidak diizinkan."}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)