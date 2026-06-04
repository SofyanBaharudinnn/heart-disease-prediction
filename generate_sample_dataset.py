"""
generate_sample_dataset.py
Jalankan script ini untuk membuat dataset contoh jika belum punya heart.csv dari Kaggle.
Gunakan: python generate_sample_dataset.py
"""

import os
# pyrefly: ignore [missing-import]
import numpy as np
import pandas as pd

np.random.seed(42)
n = 303

data = {
    'age':      np.random.randint(29, 77, n),
    'sex':      np.random.randint(0, 2, n),
    'cp':       np.random.randint(0, 4, n),
    'trestbps': np.random.randint(94, 200, n),
    'chol':     np.random.randint(126, 564, n),
    'fbs':      np.random.randint(0, 2, n),
    'restecg':  np.random.randint(0, 3, n),
    'thalach':  np.random.randint(71, 202, n),
    'exang':    np.random.randint(0, 2, n),
    'oldpeak':  np.round(np.random.uniform(0, 6.2, n), 1),
    'slope':    np.random.randint(0, 3, n),
    'ca':       np.random.randint(0, 5, n),
    'thal':     np.random.randint(0, 4, n),
}

# Generate target dengan aturan sederhana
target = []
for i in range(n):
    score = 0
    if data['age'][i] > 55:       score += 1
    if data['sex'][i] == 1:       score += 1
    if data['cp'][i] == 3:        score += 2
    if data['trestbps'][i] > 140: score += 1
    if data['chol'][i] > 240:     score += 1
    if data['thalach'][i] < 120:  score += 2
    if data['exang'][i] == 1:     score += 2
    if data['oldpeak'][i] > 2:    score += 1
    if data['ca'][i] > 0:         score += 2
    target.append(1 if score >= 5 else 0)

data['target'] = target
df = pd.DataFrame(data)

out_path = os.path.join(os.path.dirname(__file__), 'dataset', 'heart.csv')
os.makedirs(os.path.dirname(out_path), exist_ok=True)
df.to_csv(out_path, index=False)

print(f"✅ Dataset contoh berhasil dibuat: {out_path}")
print(f"   Total sampel: {len(df)}")
print(f"   Kelas positif: {df['target'].sum()} ({df['target'].mean()*100:.1f}%)")
print(f"   Kelas negatif: {len(df)-df['target'].sum()}")
