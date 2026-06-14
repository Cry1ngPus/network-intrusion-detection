# Data Directory

This directory holds the CICIDS2017 dataset (for training) and optional live-captured PCAP files (for real-world testing).

---

## CICIDS2017 Dataset

The training data comes from the [CICIDS2017 dataset](https://www.unb.ca/cic/datasets/ids-2017.html) by the Canadian Institute for Cybersecurity.

### Download

1. Go to https://cicresearch.ca/CICDataset/CIC-IDS-2017/browse.php?p=CIC-IDS-2017%2FCSVs
2. Download `MachineLearningCSV.zip`
3. Extract the CSV files directly into this directory

### Required CSV files

- `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`
- `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`
- `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`
- `Wednesday-workingHours.pcap_ISCX.csv`

After downloading, run `python3 src/merge.py` to generate `combined_dataset.csv`.

---

## Live PCAP Captures (Optional)

The real-time detection demo (`src/detect.py`) can additionally evaluate on PCAP files captured from a live test environment. PCAPs are **not committed** to the repo (they may contain sensitive network identifiers and are environment-specific). To reproduce:

### Capture BENIGN traffic

Open two terminals.

**Terminal 1** — start capture for 10 seconds:
```bash
sudo tcpdump -i eth0 -w /tmp/benign_capture.pcap -G 10 -W 1
```

**Terminal 2** — generate normal traffic immediately:
```bash
curl -s https://www.google.com > /dev/null
curl -s https://www.github.com > /dev/null
curl -s https://www.wikipedia.org > /dev/null
ping -c 5 8.8.8.8
```

Move the result:
```bash
sudo mv /tmp/benign_capture.pcap ~/Desktop/MachineLearningCVE/data/
sudo chown $USER ~/Desktop/MachineLearningCVE/data/benign_capture.pcap
```

### Capture PortScan traffic

**Terminal 1** — capture on loopback:
```bash
sudo tcpdump -i lo -w /tmp/portscan_capture.pcap -G 10 -W 1
```

**Terminal 2** — run port scan against localhost:
```bash
sudo nmap -sS -p 1-1000 127.0.0.1
```

Move the result:
```bash
sudo mv /tmp/portscan_capture.pcap ~/Desktop/MachineLearningCVE/data/
sudo chown $USER ~/Desktop/MachineLearningCVE/data/portscan_capture.pcap
```

### Run detection on the captures

```bash
python3 src/detect.py
```

If the PCAP files are present, the detection pipeline will run both synthetic and real-world scenarios.

---

## Notes

- The network interface name (`eth0` in examples) may differ depending on your system. Check with `ip link show`.
- PCAP captures require root/sudo privileges.
- All `*.csv` and `*.pcap` files in this directory are git-ignored.
