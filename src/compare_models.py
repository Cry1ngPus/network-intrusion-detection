import os
import time
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# Build paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'combined_dataset.csv')
MODEL_DIR = os.path.join(SCRIPT_DIR, '..', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

# Label simplification
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

# Balance classes
sampled = []
for label, group in df.groupby('Label'):
    sampled.append(group.sample(min(len(group), 30000), random_state=42))
df = pd.concat(sampled, ignore_index=True)

X = df.drop('Label', axis=1)
y = df['Label']

# Encode labels (XGBoost requires numeric labels)
le = LabelEncoder()
y_encoded = le.fit_transform(y)

X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42
)

# Scale features (needed for Logistic Regression)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Define models to compare
models = {
    'Random Forest': (RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1), False),
    'XGBoost': (XGBClassifier(n_estimators=100, random_state=42, n_jobs=-1, verbosity=0), False),
    'LightGBM': (LGBMClassifier(n_estimators=100, random_state=42, n_jobs=-1, verbose=-1), False),
    'Logistic Regression': (LogisticRegression(max_iter=1000, random_state=42, n_jobs=-1), True),
}

results = []

# Train and evaluate each model
for name, (model, needs_scaling) in models.items():
    print(f"\n{'='*60}")
    print(f"Training {name}...")

    X_tr = X_train_scaled if needs_scaling else X_train
    X_te = X_test_scaled if needs_scaling else X_test

    # Measure training time
    start = time.time()
    model.fit(X_tr, y_train)
    train_time = time.time() - start

    # Measure inference time
    start = time.time()
    y_pred = model.predict(X_te)
    inference_time = time.time() - start

    # Calculate accuracy
    accuracy = accuracy_score(y_test, y_pred)

    # Per-sample inference time (microseconds)
    per_sample_us = (inference_time / len(X_te)) * 1e6

    results.append({
        'Model': name,
        'Accuracy': accuracy,
        'Train Time (s)': train_time,
        'Inference Time (s)': inference_time,
        'Per-sample (μs)': per_sample_us,
    })

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Train time: {train_time:.2f}s")
    print(f"Inference time: {inference_time:.4f}s ({per_sample_us:.2f} μs/sample)")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

# Summary table
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))

# Save results to CSV
results_path = os.path.join(MODEL_DIR, 'model_comparison.csv')
results_df.to_csv(results_path, index=False)
print(f"\nResults saved to {results_path}")
