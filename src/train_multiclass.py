import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Define label simplification function
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

# Load combined dataset
print("Loading combined dataset...")
df = pd.read_csv('combined_dataset.csv')

# Apply label simplification
df['Label'] = df['Label'].apply(simplify_label)

# Drop Heartbleed and Other (too few samples)
df = df[~df['Label'].isin(['Other'])]

# Balance classes: max 30000 per class
print("Balancing classes...")
sampled = []
for label, group in df.groupby('Label'):
    sampled.append(group.sample(min(len(group), 30000), random_state=42))
df = pd.concat(sampled, ignore_index=True)

print("\nLabel distribution:")
print(df['Label'].value_counts())

# Separate features and label
X = df.drop('Label', axis=1)
y = df['Label']

# Split into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train Random Forest model
print("\nTraining model...")
model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

# Evaluate model
print("\nEvaluation results:")
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
