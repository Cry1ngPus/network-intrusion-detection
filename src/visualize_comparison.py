import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Build paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_PATH = os.path.join(SCRIPT_DIR, '..', 'models', 'model_comparison.csv')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, '..', 'models', 'model_comparison.png')

# Load comparison results
df = pd.read_csv(RESULTS_PATH)
print("Loaded results:")
print(df)

# Create 2x2 subplot
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
models = df['Model'].tolist()
colors = ['#4C72B0', '#DD8452', '#55A467', '#C44E52']

# Plot 1: Accuracy
axes[0, 0].bar(models, df['Accuracy'], color=colors)
axes[0, 0].set_title('Accuracy', fontsize=14, fontweight='bold')
axes[0, 0].set_ylim(0.97, 1.001)
axes[0, 0].set_ylabel('Accuracy')
axes[0, 0].tick_params(axis='x', rotation=15)
for i, v in enumerate(df['Accuracy']):
    axes[0, 0].text(i, v + 0.0003, f'{v:.4f}', ha='center', fontsize=10)

# Plot 2: Training Time
axes[0, 1].bar(models, df['Train Time (s)'], color=colors)
axes[0, 1].set_title('Training Time (seconds)', fontsize=14, fontweight='bold')
axes[0, 1].set_ylabel('Seconds')
axes[0, 1].tick_params(axis='x', rotation=15)
for i, v in enumerate(df['Train Time (s)']):
    axes[0, 1].text(i, v + 0.15, f'{v:.2f}s', ha='center', fontsize=10)

# Plot 3: Per-sample Inference Time
axes[1, 0].bar(models, df['Per-sample (μs)'], color=colors)
axes[1, 0].set_title('Per-sample Inference Time (μs)', fontsize=14, fontweight='bold')
axes[1, 0].set_ylabel('Microseconds')
axes[1, 0].tick_params(axis='x', rotation=15)
for i, v in enumerate(df['Per-sample (μs)']):
    axes[1, 0].text(i, v + 0.1, f'{v:.2f}', ha='center', fontsize=10)

# Plot 4: Accuracy vs Inference Time (scatter)
axes[1, 1].scatter(df['Per-sample (μs)'], df['Accuracy'],
                   s=200, c=colors, edgecolors='black', linewidth=1.5)
for i, name in enumerate(models):
    axes[1, 1].annotate(name, (df['Per-sample (μs)'][i], df['Accuracy'][i]),
                        xytext=(8, 8), textcoords='offset points', fontsize=10)
axes[1, 1].set_xlabel('Inference Time per Sample (μs)')
axes[1, 1].set_ylabel('Accuracy')
axes[1, 1].set_title('Accuracy vs Inference Speed Trade-off', fontsize=14, fontweight='bold')
axes[1, 1].grid(True, alpha=0.3)

plt.suptitle('Model Comparison: Random Forest vs XGBoost vs LightGBM vs Logistic Regression',
             fontsize=15, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(OUTPUT_PATH, dpi=100, bbox_inches='tight')
plt.close()
print(f"\nSaved: {OUTPUT_PATH}")
