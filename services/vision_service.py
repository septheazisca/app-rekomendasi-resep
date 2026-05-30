import base64
import os

import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "P7bVT2jsgG70IbhqrCll")
MODEL_ID = os.getenv("MODEL_ID", "vegetables-el4g6/1")
ROBOFLOW_URL = f"https://detect.roboflow.com/{MODEL_ID}"
YOLO_THRESHOLD = 0.40

YOLO_TO_BAHAN = {
    "tomato": "Tomat",
    "carrot": "Wortel",
    "broccoli": "Brokoli",
    "potato": "Kentang",
    "onion": "Bawang Bombay",
    "cucumber": "Timun",
    "corn": "Jagung",
    "cabbage": "Sawi",
    "avocado": None,
    "eggplant": "Terong",
    "garlic": "Bawang Putih",
    "pumpkin": "Labu Siam",
    "bell pepper": "Cabai Hijau",
    "beans": "Kacang Polong",
    "cauliflower": "Kembang Kol",
    "celery": None,
    "hot pepper": "Cabai Merah",
    "peas": "Kacang Polong",
    "salad": "Bayam",
    "beet": None,
    "brus capusta": None,
    "fasol": "Kacang Polong",
    "rediska": None,
    "redka": None,
    "squash-patisson": "Labu Siam",
    "vegetable marrow": "Labu Siam",
}


def proses_foto(image_bytes: bytes) -> dict:
    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = requests.post(
            ROBOFLOW_URL,
            params={"api_key": ROBOFLOW_API_KEY},
            data=img_b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )

        if response.status_code != 200:
            print(f"[Roboflow] Error {response.status_code}: {response.text}")
            return _empty_result(f"Gagal menghubungi Roboflow (status {response.status_code}).")

        result = response.json()
        print(f"[Roboflow] Raw predictions: {result.get('predictions', [])}")
        return _parse_result(result.get("predictions", []))

    except requests.exceptions.Timeout:
        print("[Roboflow] Request timeout.")
        return _empty_result("Koneksi ke Roboflow timeout. Coba lagi.")
    except Exception as exc:
        print(f"[Roboflow] Error tidak terduga: {exc}")
        return _empty_result("Terjadi error saat memproses foto.")


def _parse_result(predictions: list) -> dict:
    bahan_valid = []
    bahan_ragu = []
    bbox_data = []
    seen = set()

    for pred in predictions:
        label = pred.get("class", "").lower().strip()
        confidence = float(pred.get("confidence", 0))

        x = pred.get("x", 0)
        y = pred.get("y", 0)
        width = pred.get("width", 50)
        height = pred.get("height", 50)
        bbox = {
            "x1": int(x - width / 2),
            "y1": int(y - height / 2),
            "x2": int(x + width / 2),
            "y2": int(y + height / 2),
        }

        conf_persen = round(confidence * 100, 1)

        if confidence < YOLO_THRESHOLD:
            bahan_ragu.append({
                "nama": label,
                "confidence": conf_persen,
                "sumber": "yolo",
            })
            bbox_data.append({
                "nama": label,
                "bbox": bbox,
                "status": "ragu",
                "confidence": conf_persen,
            })
            continue

        nama_indo = YOLO_TO_BAHAN.get(label)
        if nama_indo is None:
            print(f"[Parse] Skip '{label}' karena tidak ada di data bahan")
            continue

        if nama_indo in seen:
            continue

        seen.add(nama_indo)
        bahan_valid.append({
            "nama": nama_indo,
            "confidence": conf_persen,
            "sumber": "yolo",
        })
        bbox_data.append({
            "nama": nama_indo,
            "bbox": bbox,
            "status": "valid",
            "confidence": conf_persen,
        })

    print(f"[proses_foto] Valid: {len(bahan_valid)}, Ragu: {len(bahan_ragu)}")

    if not bahan_valid and not bahan_ragu:
        return _empty_result(
            "Tidak ada bahan terdeteksi. Coba foto sayuran lebih dekat dan pastikan cahaya cukup."
        )

    return {
        "bahan_valid": bahan_valid,
        "bahan_ragu": bahan_ragu,
        "total_terdeteksi": len(bahan_valid) + len(bahan_ragu),
        "bbox_data": bbox_data,
        "pesan": f"{len(bahan_valid)} bahan terdeteksi",
    }


def _empty_result(pesan: str) -> dict:
    return {
        "bahan_valid": [],
        "bahan_ragu": [],
        "total_terdeteksi": 0,
        "bbox_data": [],
        "pesan": pesan,
    }
