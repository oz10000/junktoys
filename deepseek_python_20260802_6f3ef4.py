# support_resistance.py
import numpy as np
import pandas as pd
from collections import defaultdict
from config import SR_WINDOW, SR_VOLUME_THRESHOLD, SR_CLUSTER_TOLERANCE, SR_MAX_LEVELS

def find_pivots(df, window=SR_WINDOW, volume_threshold=SR_VOLUME_THRESHOLD):
    if df.empty or len(df) < window * 2:
        return [], []
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    volume = df['volume'].values
    
    resistances = []
    supports = []
    
    # Máximos (resistencias)
    for i in range(window, len(high) - window):
        if high[i] == max(high[i-window:i+window+1]):
            vol_ratio = volume[i] / np.mean(volume[max(0,i-window):min(len(volume), i+window+1)])
            if vol_ratio > volume_threshold:
                quality = vol_ratio * (1 + (high[i] - close[i]) / high[i])
                resistances.append((high[i], quality, i))
    
    # Mínimos (soportes)
    for i in range(window, len(low) - window):
        if low[i] == min(low[i-window:i+window+1]):
            vol_ratio = volume[i] / np.mean(volume[max(0,i-window):min(len(volume), i+window+1)])
            if vol_ratio > volume_threshold:
                quality = vol_ratio * (1 + (close[i] - low[i]) / low[i])
                supports.append((low[i], quality, i))
    
    supports_clustered = _cluster_levels(supports, SR_CLUSTER_TOLERANCE)
    resistances_clustered = _cluster_levels(resistances, SR_CLUSTER_TOLERANCE)
    
    supports_clustered = sorted(supports_clustered, key=lambda x: x[1], reverse=True)[:SR_MAX_LEVELS]
    resistances_clustered = sorted(resistances_clustered, key=lambda x: x[1], reverse=True)[:SR_MAX_LEVELS]
    
    return supports_clustered, resistances_clustered

def _cluster_levels(levels, tolerance=SR_CLUSTER_TOLERANCE):
    if not levels:
        return []
    levels_sorted = sorted(levels, key=lambda x: x[0])
    clustered = []
    current_cluster = [levels_sorted[0]]
    for price, quality, idx in levels_sorted[1:]:
        if (price - current_cluster[-1][0]) / current_cluster[-1][0] < tolerance:
            current_cluster.append((price, quality, idx))
        else:
            avg_price = np.mean([p for p, q, i in current_cluster])
            avg_quality = np.mean([q for p, q, i in current_cluster])
            clustered.append((avg_price, avg_quality))
            current_cluster = [(price, quality, idx)]
    if current_cluster:
        avg_price = np.mean([p for p, q, i in current_cluster])
        avg_quality = np.mean([q for p, q, i in current_cluster])
        clustered.append((avg_price, avg_quality))
    return clustered

def compute_sr_strength(current_price, supports, resistances):
    nearest_support = None
    nearest_resistance = None
    
    for sup, quality in supports:
        if sup < current_price:
            if nearest_support is None or (current_price - sup) < (current_price - nearest_support[0]):
                nearest_support = (sup, quality)
    
    for res, quality in resistances:
        if res > current_price:
            if nearest_resistance is None or (res - current_price) < (nearest_resistance[0] - current_price):
                nearest_resistance = (res, quality)
    
    strength = 0.0
    if nearest_support:
        strength += nearest_support[1] * (1 - min((current_price - nearest_support[0]) / current_price, 0.1))
    if nearest_resistance:
        strength += nearest_resistance[1] * (1 - min((nearest_resistance[0] - current_price) / current_price, 0.1))
    
    return nearest_support, nearest_resistance, min(strength, 1.0)