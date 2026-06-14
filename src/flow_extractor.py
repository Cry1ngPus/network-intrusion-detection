"""
Flow feature extractor for real-time intrusion detection.
Extracts 22 features from a list of packets belonging to the same flow.
Features are chosen to be efficiently computable from raw packets.
"""

import numpy as np
from scapy.all import IP, TCP, UDP


# Feature names (must match the order returned by extract_flow_features)
FEATURE_NAMES = [
    'Destination Port',
    'Flow Duration',
    'Total Fwd Packets',
    'Total Backward Packets',
    'Total Length of Fwd Packets',
    'Total Length of Bwd Packets',
    'Fwd Packet Length Max',
    'Fwd Packet Length Min',
    'Fwd Packet Length Mean',
    'Fwd Packet Length Std',
    'Bwd Packet Length Max',
    'Bwd Packet Length Min',
    'Bwd Packet Length Mean',
    'Bwd Packet Length Std',
    'Flow Bytes/s',
    'Flow Packets/s',
    'Flow IAT Mean',
    'Flow IAT Std',
    'Flow IAT Max',
    'Flow IAT Min',
    'SYN Flag Count',
    'ACK Flag Count',
]


def _safe_stat(values, func, default=0.0):
    """Run a statistic function safely on a possibly empty list."""
    if len(values) == 0:
        return default
    return float(func(values))


def extract_flow_features(packets, flow_key):
    """
    Extract features from a list of scapy packets belonging to one flow.

    Args:
        packets: list of scapy packets (must contain IP layer)
        flow_key: tuple (src_ip, dst_ip, src_port, dst_port, protocol)
                  used to determine forward vs backward direction

    Returns:
        numpy array of 22 features in FEATURE_NAMES order
    """
    src_ip, dst_ip, src_port, dst_port, proto = flow_key

    # Separate forward and backward packets
    # Forward: from src_ip to dst_ip (initiator direction)
    fwd_packets = []
    bwd_packets = []
    timestamps = []

    for pkt in packets:
        if IP not in pkt:
            continue
        timestamps.append(float(pkt.time))
        if pkt[IP].src == src_ip:
            fwd_packets.append(pkt)
        else:
            bwd_packets.append(pkt)

    # Packet length statistics
    fwd_lengths = [len(p) for p in fwd_packets]
    bwd_lengths = [len(p) for p in bwd_packets]

    # Flow duration (microseconds)
    if len(timestamps) >= 2:
        flow_duration = (max(timestamps) - min(timestamps)) * 1_000_000
    else:
        flow_duration = 0.0

    # Inter-arrival times (IAT)
    sorted_times = sorted(timestamps)
    iats = [sorted_times[i+1] - sorted_times[i] for i in range(len(sorted_times)-1)]
    iats_us = [iat * 1_000_000 for iat in iats]

    # Flow rates (per second)
    total_bytes = sum(fwd_lengths) + sum(bwd_lengths)
    total_packets = len(fwd_packets) + len(bwd_packets)
    duration_sec = flow_duration / 1_000_000 if flow_duration > 0 else 1e-6

    flow_bytes_per_sec = total_bytes / duration_sec
    flow_packets_per_sec = total_packets / duration_sec

    # TCP flag counts (only meaningful for TCP)
    syn_count = 0
    ack_count = 0
    for pkt in packets:
        if TCP in pkt:
            flags = pkt[TCP].flags
            if flags & 0x02:  # SYN flag
                syn_count += 1
            if flags & 0x10:  # ACK flag
                ack_count += 1

    # Assemble feature vector (must match FEATURE_NAMES order)
    features = np.array([
        dst_port,                                       # Destination Port
        flow_duration,                                  # Flow Duration
        len(fwd_packets),                               # Total Fwd Packets
        len(bwd_packets),                               # Total Backward Packets
        sum(fwd_lengths),                               # Total Length of Fwd Packets
        sum(bwd_lengths),                               # Total Length of Bwd Packets
        _safe_stat(fwd_lengths, max),                   # Fwd Packet Length Max
        _safe_stat(fwd_lengths, min),                   # Fwd Packet Length Min
        _safe_stat(fwd_lengths, np.mean),               # Fwd Packet Length Mean
        _safe_stat(fwd_lengths, np.std),                # Fwd Packet Length Std
        _safe_stat(bwd_lengths, max),                   # Bwd Packet Length Max
        _safe_stat(bwd_lengths, min),                   # Bwd Packet Length Min
        _safe_stat(bwd_lengths, np.mean),               # Bwd Packet Length Mean
        _safe_stat(bwd_lengths, np.std),                # Bwd Packet Length Std
        flow_bytes_per_sec,                             # Flow Bytes/s
        flow_packets_per_sec,                           # Flow Packets/s
        _safe_stat(iats_us, np.mean),                   # Flow IAT Mean
        _safe_stat(iats_us, np.std),                    # Flow IAT Std
        _safe_stat(iats_us, max),                       # Flow IAT Max
        _safe_stat(iats_us, min),                       # Flow IAT Min
        syn_count,                                      # SYN Flag Count
        ack_count,                                      # ACK Flag Count
    ], dtype=np.float64)

    return features


def get_flow_key(pkt):
    """
    Generate a canonical flow key from a packet.
    Returns: (src_ip, dst_ip, src_port, dst_port, protocol)
    Returns None if the packet has no IP layer or unsupported protocol.
    """
    if IP not in pkt:
        return None

    src_ip = pkt[IP].src
    dst_ip = pkt[IP].dst
    proto = pkt[IP].proto

    if TCP in pkt:
        src_port = pkt[TCP].sport
        dst_port = pkt[TCP].dport
    elif UDP in pkt:
        src_port = pkt[UDP].sport
        dst_port = pkt[UDP].dport
    else:
        return None

    return (src_ip, dst_ip, src_port, dst_port, proto)


if __name__ == '__main__':
    # Quick self-test: extract features from a known PCAP file
    import os
    from scapy.all import rdpcap

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PCAP_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

    # Try to find any pcap file for testing
    pcap_files = [f for f in os.listdir(PCAP_DIR) if f.endswith('.pcap')]
    if not pcap_files:
        print("No PCAP file found in data/ for testing.")
        print("This module is ready to be imported by detect.py.")
    else:
        print(f"Testing with: {pcap_files[0]}")
        packets = rdpcap(os.path.join(PCAP_DIR, pcap_files[0]))[:1000]
        print(f"Loaded {len(packets)} packets")

        # Group by flow
        flows = {}
        for pkt in packets:
            key = get_flow_key(pkt)
            if key is not None:
                flows.setdefault(key, []).append(pkt)

        print(f"Identified {len(flows)} unique flows")
        if flows:
            sample_key = list(flows.keys())[0]
            sample_packets = flows[sample_key]
            features = extract_flow_features(sample_packets, sample_key)
            print(f"\nSample flow {sample_key}: {len(sample_packets)} packets")
            for name, val in zip(FEATURE_NAMES, features):
                print(f"  {name:35s} = {val:.4f}")
