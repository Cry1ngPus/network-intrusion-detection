import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from imblearn.over_sampling import SMOTE

# Build paths relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'combined_dataset.csv')
MODEL_DIR = os.path.join(SCRIPT_DIR, '..', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, 'rf_smote.joblib')

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
print("Loading combined dataset...")
df = pd.read_csv(DATA_PATH)
df['Label'] = df['Label'].apply(simplify_label)
df = df[~df['Label'].isin(['Other'])]

# Balance majority classes first (max 30000 per class)
print("Balancing majority classes...")
sampled = []
for label, group in df.groupby('Label'):
    sampled.append(group.sample(min(len(group), 30000), random_state=42))
df = pd.concat(sampled, ignore_index=True)

print("\nLabel distribution before SMOTE:")
print(df['Label'].value_counts())

# Separate features and label
X = df.drop('Label', axis=1)
y = df['Label']

# Split first, then apply SMOTE only on training set
# (Important: never apply SMOTE to test set, it would leak synthetic data)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Apply SMOTE to oversample minority classes in training set
print("\nApplying SMOTE on training set...")
smote = SMOTE(random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

print("\nTraining set distribution after SMOTE:")
print(pd.Series(y_train_resampled).value_counts())

# Train Random Forest model
print("\nTraining model...")
model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train_resampled, y_train_resampled)

# Evaluate on original (non-SMOTE) test set
print("\nEvaluation results:")
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# Save trained model
joblib.dump(model, MODEL_PATH)
print(f"\nModel saved to {MODEL_PATH}")
