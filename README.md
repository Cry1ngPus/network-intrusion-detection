# Network Intrusion Detection System

> A machine learning-based intrusion detection system that combines offline model evaluation on the CICIDS2017 dataset with a real-time detection pipeline built on Scapy. The system benchmarks four classifiers, applies SMOTE to address class imbalance, and uses hybrid ML + rule-based detection to identify DoS/DDoS, PortScan, and Web Attacks from live packet streams.

---

## Highlights

- **99.96% accuracy** on the CICIDS2017 multiclass benchmark (XGBoost)
- **22-feature subset** for real-time inference, retaining 99.77% accuracy from the full 78-feature model
- **~1.4 μs per-sample inference**, capable of ~700,000 flows/sec
- **Hybrid ML + rule-based pipeline** with three working demo scenarios (BENIGN, DDoS, PortScan)
- Iterative engineering: 4 model versions, 4 classifier benchmarks, full SMOTE trade-off analysis

---

## System Architecture

```
┌────────────────────┐
│  Packet Source     │  Synthetic packets / PCAP file / live interface
│  (Scapy)           │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Flow Aggregation  │  Group by (src_ip, dst_ip, protocol)
│  (IP-pair level)   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Feature Extractor │  22 features: packet stats, IAT, TCP flags
│  (flow_extractor)  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  XGBoost Inference │  Multiclass: BENIGN / DoS_DDoS / PortScan / Web Attack
│  (xgb_realtime)    │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Heuristic Layer   │  Rule-based corrections for edge cases
│  (PortScan rule)   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Alert Output      │  Color-coded terminal output with confidence + latency
└────────────────────┘
```

---

## Overview

Modern network attacks are increasingly difficult to detect with signature-based methods alone. This project explores a machine learning approach to intrusion detection, with a focus on:

1. **Methodological rigor** — proper handling of class imbalance, evaluation leakage, and model selection trade-offs
2. **Engineering for deployment** — feature subset design, latency benchmarking, and real-time pipeline integration
3. **Hybrid detection strategy** — combining ML predictions with rule-based heuristics, mirroring how production IDS systems (Snort, Suricata) operate

The system detects four traffic categories:

| Category | Description |
|----------|-------------|
| **BENIGN** | Normal network traffic |
| **DoS / DDoS** | Volumetric attacks (SYN flood, Hulk, GoldenEye, Slowloris, Slowhttptest) |
| **PortScan** | Reconnaissance attacks scanning for open ports |
| **Web Attack** | Brute force, XSS, and SQL injection |

---

## Dataset

[**CICIDS2017**](https://www.unb.ca/cic/datasets/ids-2017.html) by the Canadian Institute for Cybersecurity.

- 1,373,444 labeled network flows across 4 attack scenarios
- 78 features per flow, extracted by CICFlowMeter
- Includes both benign background traffic and modern attack patterns

See [`data/README.md`](data/README.md) for download instructions.

---

## Methodology

### 1. Data Preparation
- Merged 4 CSV files (DDoS, PortScan, WebAttacks, DoS variants)
- Cleaned `inf` and `NaN` values from 30+ rows
- Consolidated 11 fine-grained labels into 4 coarse classes
- Balanced classes via random sampling (≤30,000 per class)

### 2. Baseline Modeling
- Random Forest as the initial multiclass classifier
- 80/20 train/test split with stratified sampling
- Per-class precision/recall/F1 evaluation

### 3. Addressing Class Imbalance (SMOTE)
- Web Attack has only 2,180 samples vs. 30,000 in other classes
- Applied SMOTE oversampling **on training set only** (avoiding evaluation leakage)
- Quantified the trade-off: fewer false negatives at the cost of slightly more false positives elsewhere

### 4. Model Selection
- Benchmarked 4 classifiers (Random Forest, XGBoost, LightGBM, Logistic Regression)
- Measured both accuracy and per-sample inference latency
- Selected XGBoost based on the best accuracy-latency trade-off

### 5. Real-Time Inference
- Selected a 22-feature subset computable from raw packets in real time
- Retrained XGBoost on the subset (acc: 99.77%, vs 99.96% with 78 features)
- Implemented Scapy-based packet capture and flow aggregation
- Added rule-based heuristics for edge cases not captured by aggregate features

---

## Results

### Baseline: Random Forest (78 features)

| Class | Precision | Recall | F1-Score |
|-------|-----------|--------|----------|
| BENIGN | 1.00 | 1.00 | 1.00 |
| DoS/DDoS | 1.00 | 1.00 | 1.00 |
| PortScan | 1.00 | 1.00 | 1.00 |
| Web Attack | 1.00 | 0.98 | 0.99 |
| **Overall Accuracy** | | | **99.89%** |

![Feature Importance](models/feature_importance.png)

The most discriminative features are *backward packet rate*, *initial TCP window size*, and *packet length statistics*—all consistent with known network attack signatures.

---

### SMOTE Trade-off Analysis

To address class imbalance, SMOTE was applied to the training set only. The aggregate `classification_report` shows both models at 1.00 due to rounding, but the confusion matrices reveal the actual differences:

![Confusion Matrix Comparison](models/confusion_matrix_comparison.png)

| | Baseline | With SMOTE | Change |
|---|---|---|---|
| Web Attack → BENIGN (false negatives) | 6 | 2 | **−4** ✓ |
| Other-class misclassifications | 13 | 16 | +3 |
| **Total misclassifications** | **20** | **19** | **−1** |

**Interpretation.** In security applications, false negatives (missed attacks) are far more costly than false positives (false alarms). SMOTE reduces Web Attack false negatives by 67% (from 6 to 2), at the cost of 3 additional misclassifications elsewhere. For a security application, this is a **favorable trade-off**.

---

### Model Comparison

To select the best classifier for real-time deployment, four models were benchmarked on accuracy, training time, and **per-sample inference latency**:

![Model Comparison](models/model_comparison.png)

| Model | Accuracy | Train Time | Inference per Sample |
|-------|----------|-----------|---------------------|
| Random Forest | 99.89% | 2.26s | 2.80 μs |
| **XGBoost** | **99.96%** | **1.80s** | **1.42 μs** |
| LightGBM | 99.96% | 1.84s | 4.37 μs |
| Logistic Regression | 98.03% | 8.34s | 0.41 μs |

**Key findings:**
1. **XGBoost dominates the accuracy-speed Pareto frontier.** Highest accuracy and second-fastest inference.
2. **XGBoost achieves 1.00 Web Attack recall *without* SMOTE.** Gradient boosting inherently handles class imbalance better than Random Forest on this dataset.
3. **LightGBM is unexpectedly slow** on this dataset size—its optimizations favor larger data.
4. **Logistic Regression** is fastest but trades 2% accuracy, unsuitable for security.

At 1.42 μs/sample, XGBoost can process ~700,000 flows/sec, providing significant headroom for real-time deployment.

---

### Real-Time Detection Demo

The real-time pipeline (`src/detect.py`) processes synthetic traffic representing three scenarios:

```
=== Scenario 1: Benign HTTPS traffic ===
  Expected: BENIGN
  Detected 1 flow(s) from 33 packets
  [✓] 192.168.1.10:50468 -> 93.184.216.34:443  | Predicted: BENIGN     (conf 100.00%, 1477μs)

=== Scenario 2: DDoS SYN flood ===
  Expected: DoS_DDoS
  Detected 1 flow(s) from 2000 packets
  [✓] 10.0.0.5:41769 -> 192.168.1.100:80       | Predicted: DoS_DDoS   (conf 96.34%, 887μs)

=== Scenario 3: Port scan ===
  Expected: PortScan
  Detected 1 flow(s) from 200 packets
  [✓] 172.16.0.50:54321 -> 192.168.1.100:17996 | Predicted: PortScan   (conf 99.96%, 879μs)
                                                  [heuristic: 200 unique ports]
```

**Design notes:**

- **IP-pair flow aggregation** — DDoS and PortScan attacks deliberately use randomized source/destination ports to evade per-flow detection. The pipeline aggregates packets at the (source IP, destination IP) level to expose this attack-level behavior.
- **Hybrid ML + rule layer** — Once aggregated, PortScan's defining signal (many unique destination ports from one source) is lost in the 22-feature vector. A simple rule (`if unique_dst_ports >= 50: override to PortScan`) recovers this signal. This mirrors how Snort and Suricata combine ML predictions with handcrafted rules.
- **22-feature subset** — Of the 78 CICIDS2017 features, many require post-hoc flow statistics (subflow, bulk transfer) that cannot be computed in real time. The 22 selected features are all directly computable from raw packets.

---

## Project Structure

```
network-intrusion-detection/
├── data/
│   └── README.md                       # Dataset download instructions
├── models/
│   ├── rf_multiclass.joblib            # Baseline Random Forest (full 78 features)
│   ├── rf_smote.joblib                 # SMOTE-enhanced Random Forest
│   ├── xgb_realtime.joblib             # XGBoost trained on 22-feature subset
│   ├── label_encoder.joblib            # LabelEncoder for inference
│   ├── confusion_matrix.png
│   ├── confusion_matrix_comparison.png # Baseline vs SMOTE comparison
│   ├── feature_importance.png
│   ├── model_comparison.png            # 4-classifier benchmark plot
│   └── model_comparison.csv            # Benchmark raw data
├── src/
│   ├── explore.py                      # Data exploration and cleaning
│   ├── merge.py                        # Merge all CSV files into one dataset
│   ├── train.py                        # Binary classification (DDoS vs BENIGN)
│   ├── train_multiclass.py             # Multiclass detection baseline
│   ├── train_smote.py                  # Multiclass detection with SMOTE
│   ├── train_realtime.py               # XGBoost on 22-feature subset
│   ├── compare_models.py               # Benchmark RF / XGBoost / LightGBM / LR
│   ├── flow_extractor.py               # 22-feature extraction from packets
│   ├── detect.py                       # Real-time detection pipeline
│   ├── visualize.py                    # Baseline plots
│   ├── visualize_smote.py              # SMOTE comparison plot
│   └── visualize_comparison.py         # Model comparison plot
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

### 4. Train and evaluate models
```bash
python3 src/train_multiclass.py      # Baseline Random Forest
python3 src/train_smote.py           # Random Forest with SMOTE
python3 src/train_realtime.py        # XGBoost on 22-feature subset
python3 src/compare_models.py        # Benchmark 4 classifiers
```

### 5. Generate visualizations
```bash
python3 src/visualize.py             # Baseline plots
python3 src/visualize_smote.py       # SMOTE comparison
python3 src/visualize_comparison.py  # Model comparison
```

### 6. Run real-time detection demo
```bash
python3 src/detect.py
```

---

## Development History

The multiclass model went through four versions, each addressing a specific issue discovered during development:

| Version | Approach | Outcome |
|---------|----------|---------|
| v1 | Load full 1.37M records | Killed by OOM |
| v2 | `nrows=50000` per file | Sampling bias (PortScan: 234 samples) |
| v3 | Random sampling per file | PortScan improved to 16,577 samples |
| v4 | Read from combined dataset, balanced sampling | Web Attack improved to 2,180 samples |

This iterative process is documented in commit history.

---

## Limitations

- **Synthetic samples from SMOTE may not reflect real-world Web Attack variations.** Production deployment should monitor for distribution shift.
- **The 22-feature subset is a deliberate simplification.** Some discriminative features (e.g., subflow statistics, bulk transfer rates) require complex stateful tracking incompatible with real-time inference.
- **Test set was sampled from the same distribution as training.** No out-of-distribution evaluation was performed; transfer to new networks may degrade accuracy.
- **Inference latency was measured in batch mode.** Per-packet streaming latency in a production pipeline may be higher due to per-call overhead.
- **The hybrid heuristic layer uses fixed thresholds.** A more adaptive approach (e.g., learned thresholds, anomaly scores) would be more robust.

---

## Future Work

- [x] ~~Apply SMOTE oversampling to improve minority class performance~~
- [x] ~~Benchmark against XGBoost, LightGBM, and Logistic Regression~~
- [x] ~~Integrate Scapy for packet processing and live detection pipeline~~
- [ ] Replace synthetic demo with PCAP-file evaluation (e.g., CICIDS2017 PCAP samples)
- [ ] Live network interface capture (requires elevated privileges)
- [ ] Web dashboard for streaming detection results
- [ ] Out-of-distribution evaluation on a different dataset (e.g., UNSW-NB15)
- [ ] Adversarial robustness testing

---

## Tech Stack

| Component | Library |
|-----------|---------|
| Data processing | pandas, numpy |
| Modeling | scikit-learn, xgboost, lightgbm |
| Imbalanced data | imbalanced-learn (SMOTE) |
| Packet processing | scapy |
| Visualization | matplotlib, seaborn |
| Persistence | joblib |

Built and tested on Python 3.13, Kali Linux (VMware).

---

## References

1. Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). *Toward generating a new intrusion detection dataset and intrusion traffic characterization.* ICISSP.
2. Chawla, N. V., Bowyer, K. W., Hall, L. O., & Kegelmeyer, W. P. (2002). *SMOTE: Synthetic Minority Over-sampling Technique.* JAIR.
3. Chen, T., & Guestrin, C. (2016). *XGBoost: A Scalable Tree Boosting System.* KDD.
