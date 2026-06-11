import os
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix

# Build paths relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'combined_dataset.csv')
MODEL_BASE = os.path.join(SCRIPT_DIR, '..', 'models', 'rf_multiclass.joblib')
MODEL_SMOTE = os.path.join(SCRIPT_DIR, '..', 'models', 'rf_smote.joblib')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', 'models')

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

# Load and prepare data (must match training split)
print("Loading dataset...")
df = pd.read_csv(DATA_PATH)
df['Label'] = df['Label'].apply(simplify_label)
df = df[~df['Label'].isin(['Other'])]

sampled = []
for label, group in df.groupby('Label'):
    sampled.append(group.sample(min(len(group), 30000), random_state=42))
df = pd.concat(sampled, ignore_index=True)

X = df.drop('Label', axis=1)
y = df['Label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Load both models
print("Loading models...")
model_base = joblib.load(MODEL_BASE)
model_smote = joblib.load(MODEL_SMOTE)

# Get predictions
y_pred_base = model_base.predict(X_test)
y_pred_smote = model_smote.predict(X_test)

labels = sorted(y.unique())
cm_base = confusion_matrix(y_test, y_pred_base, labels=labels)
cm_smote = confusion_matrix(y_test, y_pred_smote, labels=labels)

# Plot side-by-side comparison
print("Plotting comparison...")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

sns.heatmap(cm_base, annot=True, fmt='d', cmap='Blues',
            xticklabels=labels, yticklabels=labels, ax=axes[0], cbar=False)
axes[0].set_title('Baseline (No SMOTE)')
axes[0].set_xlabel('Predicted Label')
axes[0].set_ylabel('True Label')

sns.heatmap(cm_smote, annot=True, fmt='d', cmap='Greens',
            xticklabels=labels, yticklabels=labels, ax=axes[1], cbar=False)
axes[1].set_title('With SMOTE Oversampling')
axes[1].set_xlabel('Predicted Label')
axes[1].set_ylabel('True Label')

plt.tight_layout()
output_path = os.path.join(OUTPUT_DIR, 'confusion_matrix_comparison.png')
plt.savefig(output_path, dpi=100)
plt.close()
print(f"Saved: {output_path}")
