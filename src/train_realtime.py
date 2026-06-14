"""
Train XGBoost model using only the features that can be extracted in real-time
from raw packets (matching flow_extractor.py).
"""

import os
import time
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
from xgboost import XGBClassifier

# Build paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'combined_dataset.csv')
MODEL_DIR = os.path.join(SCRIPT_DIR, '..', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, 'xgb_realtime.joblib')
ENCODER_PATH = os.path.join(MODEL_DIR, 'label_encoder.joblib')

# Subset of features matching flow_extractor.py
# These must match the column names in CICIDS2017 (with leading spaces stripped)
REALTIME_FEATURES = [
    'Destination Port',
    'Flow Duration',
    'Total Fwd Packets',
    'Total Backward Packets',
    'Total Length of Fwd Packets',
    'Total Length of Bwd Packets',
    'Fwd Packet Length Max',
    'Fwd Packet Length Min',
    'Fwd Packet Length Mean',
    'Fwd Packet Length Std',
    'Bwd Packet Length Max',
    'Bwd Packet Length Min',
    'Bwd Packet Length Mean',
    'Bwd Packet Length Std',
    'Flow Bytes/s',
    'Flow Packets/s',
    'Flow IAT Mean',
    'Flow IAT Std',
    'Flow IAT Max',
    'Flow IAT Min',
    'SYN Flag Count',
    'ACK Flag Count',
]


def simplify_label(label):
    if label == 'BENIGN':
        return 'BENIGN'
    elif 'DoS' in label or 'DDoS' in label:
        return 'DoS_DDoS'
    elif 'PortScan' in label:
        return 'PortScan'
    elif 'Web Attack' in label:
        return 'Web Attack'
    else:
        return 'Other'


# Load and prepare data
print("Loading dataset...")
df = pd.read_csv(DATA_PATH)
df['Label'] = df['Label'].apply(simplify_label)
df = df[~df['Label'].isin(['Other'])]

# Verify all required features exist
missing = [f for f in REALTIME_FEATURES if f not in df.columns]
if missing:
    raise ValueError(f"Missing features in dataset: {missing}")

# Balance classes
print("Balancing classes...")
sampled = []
for label, group in df.groupby('Label'):
    sampled.append(group.sample(min(len(group), 30000), random_state=42))
df = pd.concat(sampled, ignore_index=True)

print(f"\nUsing {len(REALTIME_FEATURES)} features (vs 78 in full dataset)")
print("Label distribution:")
print(df['Label'].value_counts())

# Use only the realtime-computable features
X = df[REALTIME_FEATURES]
y = df['Label']

# Encode labels for XGBoost
le = LabelEncoder()
y_encoded = le.fit_transform(y)

X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42
)

# Train XGBoost
print("\nTraining XGBoost...")
start = time.time()
model = XGBClassifier(n_estimators=100, random_state=42, n_jobs=-1, verbosity=0)
model.fit(X_train, y_train)
train_time = time.time() - start
print(f"Training time: {train_time:.2f}s")

# Evaluate
print("\nEvaluation:")
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}")
print(classification_report(y_test, y_pred, target_names=le.classes_))

# Save model and label encoder
joblib.dump(model, MODEL_PATH)
joblib.dump(le, ENCODER_PATH)
print(f"\nModel saved to {MODEL_PATH}")
print(f"Encoder saved to {ENCODER_PATH}")
