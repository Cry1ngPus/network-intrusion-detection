import pandas as pd
import numpy as np

# List of all CSV files to merge
files = [
    'Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv',
    'Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv',
    'Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv',
    'Wednesday-workingHours.pcap_ISCX.csv'
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
combined.to_csv('combined_dataset.csv', index=False)
print("\nSaved to combined_dataset.csv")
