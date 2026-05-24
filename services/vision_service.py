"""
vision_service.py
=================
Layer 1: Gemini Vision — deteksi semua bahan dari 1 foto
Layer 2: CNN Validator — konfirmasi tiap bahan dengan model kustom

Taruh file ini di: services/vision_service.py
"""

import os
import json
import base64
import numpy as np
from pathlib import Path
from PIL import Image
import io

# ── Load environment variables ──
from dotenv import load_dotenv

# Cari .env dari folder root proyek (satu level di atas services/)
_env_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(dotenv_path=_env_path)

# DEBUG — hapus setelah beres
print("DEBUG KEY 1:", os.getenv("GEMINI_API_KEY_1"))

# ── Gemini ──
from google import genai
from google.genai import types

# ── TensorFlow / Keras ──
import tensorflow as tf


# ============================================================
# KONFIGURASI
# ============================================================

MODEL_PATH  = os.path.join(os.path.dirname(__file__), "../model/model_bahan_makanan.h5")
LABELS_PATH = os.path.join(os.path.dirname(__file__), "../model/class_labels.json")
CNN_THRESHOLD = 0.50   # confidence minimum agar bahan dinyatakan valid

# Load daftar label CNN
with open(LABELS_PATH, encoding="utf-8") as f:
    IDX_TO_CLASS = json.load(f)   # {"0": "ayam", "1": "bawang_merah", ...}

# Balik mapping: nama → index (untuk lookup cepat)
CLASS_TO_IDX = {v: k for k, v in IDX_TO_CLASS.items()}

# ── Load model CNN sekali saja saat modul diimport ──
print("[vision_service] Loading CNN model...")
cnn_model = tf.keras.models.load_model(MODEL_PATH)
print(f"[vision_service] Model loaded. Classes: {len(IDX_TO_CLASS)}")


# ============================================================
# HELPER: Multi-key Gemini API (FIXED TUPLE BUG)
# ============================================================

def _get_gemini_client():
    """
    Coba API key satu per satu dari .env.
    Format .env: GEMINI_API_KEY_1, GEMINI_API_KEY_2, dst.
    """
    for i in range(1, 6):
        key = os.getenv(f"GEMINI_API_KEY_{i}")
        if key:
            try:
                # Memastikan inisialisasi bersih tanpa koma di akhir baris
                gemini_client = genai.Client(api_key=key.strip())
                
                # Validasi ekstra untuk memastikan objek benar dan memiliki method/attribute yang dicari
                if hasattr(gemini_client, "models"):
                    return gemini_client
                else:
                    print(f"[Warning] Key ke-{i} mengembalikan objek non-client, mencoba key berikutnya...")
                    continue
            except Exception as e:
                print(f"[Warning] Key ke-{i} gagal di-load: {e}")
                continue
                
    raise RuntimeError("Tidak ada Gemini API key yang valid di file .env!")


# ============================================================
# LAYER 1: Gemini Vision — Deteksi Bahan + Bounding Box
# ============================================================

GEMINI_PROMPT = """
Kamu adalah sistem deteksi bahan masakan Indonesia.
Analisa gambar ini dan identifikasi SEMUA bahan makanan mentah yang terlihat.

Kembalikan HANYA JSON array seperti ini (tanpa teks lain):
[
  {
    "nama": "tomat",
    "confidence": 0.95,
    "bbox": {"x1": 10, "y1": 20, "x2": 150, "y2": 180}
  },
  {
    "nama": "bawang_merah",
    "confidence": 0.88,
    "bbox": {"x1": 200, "y1": 50, "x2": 320, "y2": 160}
  }
]

Aturan:
- nama: gunakan huruf kecil, spasi diganti underscore
- confidence: nilai 0.0 sampai 1.0
- bbox: koordinat pixel kotak deteksi (x1,y1 = pojok kiri atas, x2,y2 = pojok kanan bawah)
- Hanya sertakan bahan makanan mentah, abaikan peralatan/wadah
- Jika tidak ada bahan terdeteksi, kembalikan array kosong: []
"""

def deteksi_gemini(image_bytes: bytes) -> list[dict]:
    """
    Layer 1: Kirim foto ke Gemini, dapatkan list bahan + bounding box.
    """
    try:
        client = _get_gemini_client()
        
        # Deteksi tipe gambar
        img = Image.open(io.BytesIO(image_bytes))
        fmt = img.format or "JPEG"
        mime_map = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
        mime_type = mime_map.get(fmt, "image/jpeg")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",  # Menggunakan versi model terbaru yang didukung SDK
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                GEMINI_PROMPT
            ]
        )
        
        # Parse JSON dari response
        raw = response.text.strip()
        
        # Bersihkan markdown fence jika ada
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        
        hasil = json.loads(raw)
        print(f"[Gemini] Terdeteksi {len(hasil)} bahan: {[h['nama'] for h in hasil]}")
        return hasil if isinstance(hasil, list) else []
        
    except json.JSONDecodeError as e:
        print(f"[Gemini] Gagal parse JSON. Response mentah: {response.text if 'response' in locals() else 'None'}")
        print(f"[Gemini] Error info: {e}")
        return []
    except Exception as e:
        print(f"[Gemini] Error pada Layer 1: {e}")
        return []


# ============================================================
# LAYER 2: CNN Validator — Validasi tiap bahan
# ============================================================

def _crop_bahan(image_bytes: bytes, bbox: dict, padding: int = 10) -> np.ndarray:
    """
    Crop foto utama berdasarkan koordinat bounding box dari Gemini.
    Tambah padding agar tidak terlalu mepet.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    
    x1 = max(0, bbox["x1"] - padding)
    y1 = max(0, bbox["y1"] - padding)
    x2 = min(w, bbox["x2"] + padding)
    y2 = min(h, bbox["y2"] + padding)
    
    crop = img.crop((x1, y1, x2, y2))
    crop = crop.resize((224, 224))
    arr  = np.array(crop, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)   # shape: (1, 224, 224, 3)


def validasi_cnn(image_bytes: bytes, nama_gemini: str, bbox: dict) -> dict:
    """
    Layer 2: Crop bahan dari foto, masukkan ke CNN, dapatkan confidence.
    """
    try:
        # Crop berdasarkan bounding box
        arr = _crop_bahan(image_bytes, bbox)
        
        # Prediksi dengan CNN
        pred   = cnn_model.predict(arr, verbose=0)[0]
        top_idx = int(np.argmax(pred))
        nama_cnn   = IDX_TO_CLASS.get(str(top_idx), "tidak_dikenal")
        
        # Cek apakah nama Gemini ada di 47 kelas CNN
        nama_gemini_clean = nama_gemini.lower().replace(" ", "_")
        ada_di_kelas = nama_gemini_clean in CLASS_TO_IDX
        
        # Logika validasi:
        # - Kalau ada di kelas CNN → pakai confidence CNN langsung
        # - Kalau tidak ada di kelas CNN → percaya Gemini, tapi tandai
        if ada_di_kelas:
            # Ambil confidence spesifik untuk kelas yang dimaksud Gemini
            idx_gemini    = int(CLASS_TO_IDX[nama_gemini_clean])
            conf_gemini_class = float(pred[idx_gemini])
            is_valid = conf_gemini_class >= CNN_THRESHOLD
            return {
                "valid"          : is_valid,
                "nama_cnn"       : nama_cnn,
                "nama_gemini"    : nama_gemini,
                "confidence_cnn" : round(conf_gemini_class * 100, 1),
                "ada_di_kelas"   : True,
                "status"         : "valid" if is_valid else "ragu"
            }
        else:
            # Bahan di luar 47 kelas CNN → percaya Gemini
            return {
                "valid"          : True,
                "nama_cnn"       : nama_gemini_clean,
                "nama_gemini"    : nama_gemini,
                "confidence_cnn" : None,
                "ada_di_kelas"   : False,
                "status"         : "gemini_only"
            }
            
    except Exception as e:
        print(f"[CNN] Error validasi '{nama_gemini}': {e}")
        return {
            "valid"          : False,
            "nama_cnn"       : nama_gemini,
            "nama_gemini"    : nama_gemini,
            "confidence_cnn" : None,
            "ada_di_kelas"   : False,
            "status"         : "error"
        }


# ============================================================
# FUNGSI UTAMA — Gabungkan Layer 1 + Layer 2
# ============================================================

def proses_foto(image_bytes: bytes) -> dict:
    """
    Fungsi utama yang dipanggil oleh Flask route.
    Jalankan Layer 1 (Gemini) → Layer 2 (CNN) secara otomatis.
    """
    # ── Layer 1: Gemini deteksi ──
    hasil_gemini = deteksi_gemini(image_bytes)
    
    if not hasil_gemini:
        return {
            "bahan_valid"      : [],
            "bahan_ragu"       : [],
            "bahan_gemini_only": [],
            "total_terdeteksi" : 0,
            "bbox_data"        : [],
            "pesan"            : "Tidak ada bahan terdeteksi. Pastikan foto jelas dan cukup terang."
        }
    
    # ── Layer 2: CNN validasi tiap bahan ──
    bahan_valid       = []
    bahan_ragu        = []
    bahan_gemini_only = []
    bbox_data         = []
    
    for item in hasil_gemini:
        nama   = item.get("nama", "")
        bbox   = item.get("bbox", {"x1": 0, "y1": 0, "x2": 100, "y2": 100})
        conf_g = item.get("confidence", 0)
        
        hasil_cnn = validasi_cnn(image_bytes, nama, bbox)
        
        # Siapkan data untuk bounding box di frontend
        bbox_entry = {
            "nama"      : nama,
            "bbox"      : bbox,
            "status"    : hasil_cnn["status"],
            "confidence": hasil_cnn["confidence_cnn"]
        }
        bbox_data.append(bbox_entry)
        
        if hasil_cnn["status"] == "gemini_only":
            bahan_gemini_only.append(nama.replace("_", " "))
            bahan_valid.append({
                "nama"      : nama.replace("_", " "),
                "confidence": round(conf_g * 100, 1),
                "sumber"    : "gemini"
            })
        elif hasil_cnn["valid"]:
            bahan_valid.append({
                "nama"      : hasil_cnn["nama_cnn"].replace("_", " "),
                "confidence": hasil_cnn["confidence_cnn"],
                "sumber"    : "cnn"
            })
        else:
            bahan_ragu.append({
                "nama"      : nama.replace("_", " "),
                "confidence": hasil_cnn["confidence_cnn"],
                "sumber"    : "cnn"
            })
    
    print(f"[proses_foto] Valid: {len(bahan_valid)}, Ragu: {len(bahan_ragu)}")
    
    return {
        "bahan_valid"      : bahan_valid,
        "bahan_ragu"       : bahan_ragu,
        "bahan_gemini_only": bahan_gemini_only,
        "total_terdeteksi" : len(hasil_gemini),
        "bbox_data"        : bbox_data,
        "pesan"            : f"{len(bahan_valid)} bahan terdeteksi dan tervalidasi"
    }