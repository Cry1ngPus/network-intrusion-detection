"""
Real-time intrusion detection pipeline.

Workflow:
1. Generate or read packets (using Scapy)
2. Group packets into flows by 5-tuple
3. Extract 22 features per flow
4. Run XGBoost inference
5. Print color-coded alerts
"""

import os
import sys
import time
import random
import joblib
import numpy as np
from collections import defaultdict
from scapy.all import IP, TCP, UDP, Ether, Raw, rdpcap
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

# Make sure flow_extractor is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from flow_extractor import extract_flow_features, get_flow_key, FEATURE_NAMES

# Build paths
MODEL_PATH = os.path.join(SCRIPT_DIR, '..', 'models', 'xgb_realtime.joblib')
ENCODER_PATH = os.path.join(SCRIPT_DIR, '..', 'models', 'label_encoder.joblib')

# ANSI color codes for terminal output
class Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'


def colorize_label(label):
    """Return label with appropriate color based on threat level."""
    if label == 'BENIGN':
        return f"{Color.GREEN}{label}{Color.RESET}"
    elif label in ('DoS_DDoS', 'Web Attack'):
        return f"{Color.RED}{Color.BOLD}{label}{Color.RESET}"
    elif label == 'PortScan':
        return f"{Color.YELLOW}{label}{Color.RESET}"
    else:
        return label


# === Synthetic packet generators ===

def gen_benign_flow(src_ip="192.168.1.10", dst_ip="93.184.216.34", dst_port=443):
    """Generate a benign HTTPS-like flow (TCP handshake + data exchange)."""
    packets = []
    base_time = time.time()
    src_port = random.randint(40000, 60000)

    # SYN
    p = Ether()/IP(src=src_ip, dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags='S')
    p.time = base_time
    packets.append(p)
    # SYN-ACK
    p = Ether()/IP(src=dst_ip, dst=src_ip)/TCP(sport=dst_port, dport=src_port, flags='SA')
    p.time = base_time + 0.02
    packets.append(p)
    # ACK
    p = Ether()/IP(src=src_ip, dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags='A')
    p.time = base_time + 0.025
    packets.append(p)

    # Data exchange (15 packets back and forth, normal sizes)
    for i in range(15):
        size = random.randint(200, 1400)
        p = Ether()/IP(src=src_ip, dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags='PA')/Raw(b'X'*size)
        p.time = base_time + 0.1 + i * 0.05
        packets.append(p)
        p = Ether()/IP(src=dst_ip, dst=src_ip)/TCP(sport=dst_port, dport=src_port, flags='PA')/Raw(b'Y'*random.randint(500, 1400))
        p.time = base_time + 0.12 + i * 0.05
        packets.append(p)

    return packets


def gen_ddos_flow(src_ip="10.0.0.5", dst_ip="192.168.1.100", dst_port=80):
    """
    Generate a SYN flood DDoS pattern.

    Real-world DDoS traffic has some natural variation:
    - Packet rate fluctuates (not perfectly uniform)
    - Occasional retry packets (PSH/ACK variants)
    - Larger volume to clearly exceed legitimate burst patterns
    """
    packets = []
    base_time = time.time()
    total_packets = 2000  # Larger volume, more realistic

    for i in range(total_packets):
        src_port = random.randint(1024, 65535)

        # Most packets are pure SYN, but occasionally include PSH/ACK variants
        # (real attack tools sometimes mix flags to evade simple filters)
        if random.random() < 0.05:
            flags = 'SA'  # 5% SYN-ACK variants (spoofed response)
        elif random.random() < 0.02:
            flags = 'PA'  # 2% PSH-ACK variants
        else:
            flags = 'S'   # 93% pure SYN

        p = Ether()/IP(src=src_ip, dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags=flags)

        # Add natural timing jitter (not perfectly uniform)
        jitter = random.uniform(0.00005, 0.0002)
        p.time = base_time + i * 0.0001 + jitter
        packets.append(p)

    return packets

def gen_portscan_flow(src_ip="172.16.0.50", dst_ip="192.168.1.100"):
    """Generate a port scan pattern (one src probing many ports)."""
    packets = []
    base_time = time.time()

    # Scan 200 different ports rapidly
    for i, port in enumerate(random.sample(range(1, 65535), 200)):
        p = Ether()/IP(src=src_ip, dst=dst_ip)/TCP(sport=54321, dport=port, flags='S')
        p.time = base_time + i * 0.001
        packets.append(p)

    return packets


# === Detection pipeline ===

def group_into_flows(packets):
    """
    Group packets into flows by (src_ip, dst_ip, protocol).

    Note: We deliberately ignore source/destination ports here.
    For DDoS and PortScan, the attack signature is in the aggregate
    behavior of one host toward another (many SYNs, many ports scanned),
    not in individual port-level flows. This matches how the model was
    trained on CICIDS2017's labeled time windows.
    """
    flows = defaultdict(list)
    flow_keys = {}

    for pkt in packets:
        key = get_flow_key(pkt)
        if key is None:
            continue

        src_ip, dst_ip, src_port, dst_port, proto = key

        # Aggregation key: only by IP pair + protocol (ports collapsed)
        endpoint_a = src_ip
        endpoint_b = dst_ip
        canonical = (min(endpoint_a, endpoint_b), max(endpoint_a, endpoint_b), proto)

        # Use the first-seen full 5-tuple as the "representative" key
        # so feature extraction still knows the direction
        if canonical not in flow_keys:
            flow_keys[canonical] = key
        flows[canonical].append(pkt)

    return {flow_keys[c]: pkts for c, pkts in flows.items()}

def apply_heuristics(packets, pred_label, flow_key):
    """
    Apply post-classification heuristics (hybrid ML + rule-based detection).

    Real-world IDS often combines ML predictions with rule-based corrections
    to handle attack patterns that aggregate-level features may miss.
    """
    src_ip, dst_ip, src_port, dst_port, proto = flow_key

    # Count unique destination ports targeted by the source
    dst_ports = set()
    for pkt in packets:
        if TCP in pkt:
            dst_ports.add(pkt[TCP].dport)
        elif UDP in pkt:
            dst_ports.add(pkt[UDP].dport)

    # PortScan rule: many unique ports targeted from one source
    if len(dst_ports) >= 50 and pred_label != 'PortScan':
        return 'PortScan', f'heuristic: {len(dst_ports)} unique ports'

    return pred_label, None

def detect(packets, model, encoder, source_label=None):
    """Run detection on a list of packets, print results."""
    flows = group_into_flows(packets)
    print(f"  Detected {len(flows)} flow(s) from {len(packets)} packets")

    for key, pkts in flows.items():
        src_ip, dst_ip, src_port, dst_port, proto = key

        # Extract features
        features = extract_flow_features(pkts, key)
        features_2d = features.reshape(1, -1)

        # Inference
        start = time.time()
        pred_idx = model.predict(features_2d)[0]
        proba = model.predict_proba(features_2d)[0]
        latency_us = (time.time() - start) * 1_000_000
        pred_label = encoder.inverse_transform([pred_idx])[0]
        confidence = proba[pred_idx]
	# Apply hybrid post-processing rules
        original_pred = pred_label
        pred_label, override_reason = apply_heuristics(pkts, pred_label, key)

        # Verify correctness if ground truth is known
        if source_label is not None:
            mark = '✓' if pred_label == source_label else '✗'
        else:
            mark = ' '

        # Format output
        flow_str = f"{src_ip}:{src_port} -> {dst_ip}:{dst_port}"
        suffix = f" [{override_reason}]" if override_reason else ""
        print(f"  [{mark}] {flow_str:50s} | "
              f"Predicted: {colorize_label(pred_label):30s} "
              f"(conf {confidence:.2%}, {latency_us:.0f}μs){suffix}")

# === Main demo ===

def main():
    print(f"{Color.BOLD}Loading model...{Color.RESET}")
    model = joblib.load(MODEL_PATH)
    encoder = joblib.load(ENCODER_PATH)
    print(f"Model classes: {list(encoder.classes_)}\n")

    # Check if user wants to run PCAP mode
    DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

    pcap_scenarios = [
        ("Real-world BENIGN (live capture)",  "benign_capture.pcap",   "BENIGN"),
        ("Real-world PortScan (nmap capture)", "portscan_capture.pcap", "PortScan"),
    ]

    # Synthetic scenarios (always run)
    synthetic_scenarios = [
        ("Synthetic: Benign HTTPS traffic", gen_benign_flow,   "BENIGN"),
        ("Synthetic: DDoS SYN flood",       gen_ddos_flow,     "DoS_DDoS"),
        ("Synthetic: Port scan",            gen_portscan_flow, "PortScan"),
    ]

    # Run synthetic scenarios first
    print(f"{Color.BOLD}{Color.BLUE}{'='*60}{Color.RESET}")
    print(f"{Color.BOLD}{Color.BLUE}SYNTHETIC SCENARIOS{Color.RESET}")
    print(f"{Color.BOLD}{Color.BLUE}{'='*60}{Color.RESET}\n")
    for title, generator, expected in synthetic_scenarios:
        print(f"{Color.BOLD}--- {title} ---{Color.RESET}")
        print(f"  Expected: {colorize_label(expected)}")
        packets = generator()
        detect(packets, model, encoder, source_label=expected)
        print()

    # Then run real PCAP scenarios if files exist
    print(f"{Color.BOLD}{Color.BLUE}{'='*60}{Color.RESET}")
    print(f"{Color.BOLD}{Color.BLUE}REAL-WORLD PCAP SCENARIOS{Color.RESET}")
    print(f"{Color.BOLD}{Color.BLUE}{'='*60}{Color.RESET}\n")
    for title, pcap_file, expected in pcap_scenarios:
        pcap_path = os.path.join(DATA_DIR, pcap_file)
        if not os.path.exists(pcap_path):
            print(f"  [skip] {title}: {pcap_file} not found")
            continue
        print(f"{Color.BOLD}--- {title} ---{Color.RESET}")
        print(f"  Source: {pcap_file}")
        print(f"  Expected (dominant traffic): {colorize_label(expected)}")
        packets = rdpcap(pcap_path)
        detect(packets, model, encoder, source_label=expected)
        print()

if __name__ == '__main__':
    main()
