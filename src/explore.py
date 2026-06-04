import pandas as pd
import numpy as np

# Load dataset
df = pd.read_csv('Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv')

# Strip whitespace from column names
df.columns = df.columns.str.strip()

# Basic info
print("Dataset shape:", df.shape)
print("\nLabel distribution:")
print(df['Label'].value_counts())

# Remove inf and NaN values
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(inplace=True)
print("\nShape after cleaning:", df.shape)

