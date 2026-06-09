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
MODEL_PATH = os.path.join(SCRIPT_DIR, '..', 'models', 'rf_multiclass.joblib')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', 'models')

# Label simplification (same as training)
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

# Load and prepare data (same logic as training)
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
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Load trained model
print("Loading model...")
model = joblib.load(MODEL_PATH)
y_pred = model.predict(X_test)

# === Plot 1: Confusion Matrix ===
print("Plotting confusion matrix...")
labels = sorted(y.unique())
cm = confusion_matrix(y_test, y_pred, labels=labels)

plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=labels, yticklabels=labels)
plt.xlabel('Predicted Label')
plt.ylabel('True Label')
plt.title('Confusion Matrix - Random Forest Multiclass')
plt.tight_layout()
cm_path = os.path.join(OUTPUT_DIR, 'confusion_matrix.png')
plt.savefig(cm_path, dpi=100)
plt.close()
print(f"Saved: {cm_path}")

# === Plot 2: Feature Importance (Top 15) ===
print("Plotting feature importance...")
importances = pd.Series(model.feature_importances_, index=X.columns)
top15 = importances.sort_values(ascending=True).tail(15)

plt.figure(figsize=(8, 6))
top15.plot(kind='barh', color='steelblue')
plt.xlabel('Importance')
plt.title('Top 15 Most Important Features')
plt.tight_layout()
fi_path = os.path.join(OUTPUT_DIR, 'feature_importance.png')
plt.savefig(fi_path, dpi=100)
plt.close()
print(f"Saved: {fi_path}")

print("\nDone!")
