# Network Intrusion Detection System

A machine learning-based network intrusion detection system trained on the CICIDS2017 dataset, classifying network traffic into BENIGN, DoS/DDoS, PortScan, and Web Attack categories using Random Forest.

---

## Overview

This project detects four types of network behavior:
- **BENIGN** — Normal network traffic
- **DoS / DDoS** — Distributed/volumetric attacks overwhelming the target
- **PortScan** — Reconnaissance attacks scanning for open ports
- **Web Attack** — Brute force, XSS, and SQL injection attacks

---

## Dataset

[CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) by the Canadian Institute for Cybersecurity.
- 1,373,444 total records across 4 attack scenarios
- 78 network flow features extracted by CICFlowMeter

See [`data/README.md`](data/README.md) for download instructions.

---

## Results

| Class | Precision | Recall | F1-Score |
|-------|-----------|--------|----------|
| BENIGN | 1.00 | 1.00 | 1.00 |
| DoS/DDoS | 1.00 | 1.00 | 1.00 |
| PortScan | 1.00 | 1.00 | 1.00 |
| Web Attack | 1.00 | 0.98 | 0.99 |
| **Overall Accuracy** | | | **1.00** |

### Confusion Matrix
![Confusion Matrix](models/confusion_matrix.png)

Only 10 misclassifications out of 18,436 test samples. The 8 Web Attack samples misclassified as BENIGN represent **false negatives**—a critical concern in security applications where missing attacks is more costly than false alarms.

### Top 15 Feature Importance
![Feature Importance](models/feature_importance.png)

The most discriminative features include backward packet rate, initial TCP window size, and packet length statistics—all consistent with known network attack signatures.

---

## Project Structure

```
network-intrusion-detection/
├── data/
│   └── README.md              # Dataset download instructions
├── models/
│   ├── rf_multiclass.joblib   # Trained Random Forest model
│   ├── confusion_matrix.png
│   └── feature_importance.png
├── src/
│   ├── explore.py             # Data exploration and cleaning
│   ├── merge.py               # Merge all CSV files
│   ├── train.py               # Binary classification (DDoS vs BENIGN)
│   ├── train_multiclass.py    # Multiclass detection (current)
│   └── visualize.py           # Generate result plots
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Usage

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Download dataset
Follow instructions in [`data/README.md`](data/README.md).

### 3. Merge datasets
```bash
python3 src/merge.py
```

### 4. Train model
```bash
python3 src/train_multiclass.py
```

### 5. Generate visualizations
```bash
python3 src/visualize.py
```

---

## Development Notes

Four iterations of the multiclass model were developed to address dataset and resource constraints:

| Version | Approach | Outcome |
|---------|----------|---------|
| v1 | Load full 1.37M records | Killed by OOM |
| v2 | `nrows=50000` per file | Sampling bias (PortScan: 234 samples) |
| v3 | Random sampling per file | PortScan improved to 16,577 samples |
| v4 | Read from combined dataset, balanced sampling | Web Attack improved to 2,180 samples |

---

## Limitations

- Web Attack has only 2,180 samples, leading to slightly lower recall (0.98)
- Single-model evaluation (Random Forest only); no comparison with XGBoost / LightGBM yet
- Currently offline analysis only; no real-time packet capture

---

## Future Work

- [ ] Apply SMOTE oversampling to improve minority class performance
- [ ] Benchmark against XGBoost, LightGBM, and simple MLP
- [ ] Integrate Scapy for real-time packet capture and live detection
- [ ] Web dashboard for visualizing detection results

---

## Tech Stack

- Python 3.13
- scikit-learn, pandas, numpy
- matplotlib, seaborn
- joblib
