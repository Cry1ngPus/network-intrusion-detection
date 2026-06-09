import pandas as pd
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# List of all CSV files to merge
files = [
    os.path.join(DATA_DIR, 'Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv'),
    os.path.join(DATA_DIR, 'Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv'),
    os.path.join(DATA_DIR, 'Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv'),
    os.path.join(DATA_DIR, 'Wednesday-workingHours.pcap_ISCX.csv'),
]

dfs = []

# Load and clean each file
for f in files:
    print(f"Loading {f}...")
    df = pd.read_csv(f)
    df.columns = df.columns.str.strip()
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    dfs.append(df)

# Merge all dataframes
combined = pd.concat(dfs, ignore_index=True)

# Show label distribution
print("\nCombined dataset shape:", combined.shape)
print("\nLabel distribution:")
print(combined['Label'].value_counts())

# Save merged dataset
combined.to_csv(os.path.join(DATA_DIR, 'combined_dataset.csv'), index=False)
print("\nSaved to combined_dataset.csv")
