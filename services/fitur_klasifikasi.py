import os
import json
import csv
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# --- LOAD MODEL DAN LABEL ---
MODEL_PATH = 'model/model_bahan_makanan.h5' 
model = load_model(MODEL_PATH)

with open('model/class_labels.json', 'r') as f:
    class_labels = json.load(f)

# --- FUNGSI MEMBACA DATASET CSV TERBARU ---
def get_bahan_info(nama_bahan_json):
    # Menggunakan nama file target: klasifikasi_bahan.csv
    csv_path = os.path.join('data', 'klasifikasi_bahan.csv')
    
    # Standarisasi nama dari JSON (contoh: 'bawang_bombay' -> 'bawang bombay')
    nama_cari = nama_bahan_json.lower().replace('_', ' ').strip()
    
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'nama_bahan' not in row:
                    continue
                
                # Standarisasi nama dari CSV (contoh: 'Bawang Bombay' -> 'bawang bombay')
                nama_csv = row['nama_bahan'].lower().replace('_', ' ').strip()
                
                if nama_csv == nama_cari:
                    return {
                        'nama': row.get('nama_bahan', '-'),
                        'kategori': row.get('kategori', '-'),
                        'deskripsi': row.get('deskripsi', '-'),
                        'cara_menyimpan': row.get('cara_menyimpan_yang_baik', '-'),
                        'masa_simpan': row.get('masa_simpan', '-'),
                        'masakan_populer': row.get('masakan_paling_populer', '-'),
                        'asal_bahan': row.get('asal_bahan', '-'),
                        'gizi': row.get('kandungan_gizi_utama', '-'),
                        'alergi': row.get('efek_alergi', 'Tidak'),
                        'kemudahan_busuk': row.get('tingkat_kemudahan_busuk', '-'),
                        'tips': row.get('tips_tambahan', '-')
                    }
                    
    # Jika tidak ditemukan di CSV, berikan nilai default berdasarkan nama dari JSON
    return {
        'nama': nama_bahan_json.replace('_', ' ').title(),
        'kategori': '-',
        'deskripsi': 'Informasi deskripsi tidak ditemukan.',
        'cara_menyimpan': 'Tidak tersedia.',
        'masa_simpan': '-',
        'masakan_populer': 'Tidak tersedia.',
        'asal_bahan': '-',
        'gizi': '-',
        'alergi': 'Tidak',
        'kemudahan_busuk': '-',
        'tips': 'Tidak ada tips tambahan.'
    }

# --- FUNGSI PREDIKSI ---
def predict_ingredient(image_path):
    img_width, img_height = 224, 224 
    img = image.load_img(image_path, target_size=(img_width, img_height))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = img_array / 255.0

    predictions = model.predict(img_array)
    predicted_class_idx = np.argmax(predictions[0])
    class_str = str(predicted_class_idx)
    
    if class_str in class_labels:
        nama_bahan_json = class_labels[class_str]
        return get_bahan_info(nama_bahan_json)
    
    return None