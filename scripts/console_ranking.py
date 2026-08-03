#!/usr/bin/env python3
# scripts/console_ranking.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
import logging

from data_engine import DataEngine
from signal_engine import Signal
from config import (
    INITIAL_CAPITAL, DEFAULT_PARAMS,  # <--- ASSET_PARAMS eliminado
    VERSION, PROJECT_NAME, KILL_SWITCH
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("🧸🐻 JUNK TOYS BAND PROJECT — TOP 10 LONG / SHORT 🐻🧸")
    print("=" * 60)
    print(f"📊 Versión: {VERSION} | {PROJECT_NAME}")
    print("=" * 60)

    # Inicializar DataEngine
    de = DataEngine()
    symbols = de.get_certified_assets()  # Solo activos certificados

    if not symbols:
        print("❌ No se obtuvieron símbolos certificados. Usando lista de fallback.")
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT']
        print(f"📌 Fallback: {len(symbols)} símbolos")

    print(f"📊 Símbolos evaluados: {len(symbols)}")

    # Descargar datos
    data = {}
    for sym in symbols[:20]:
        df = de.fetch_ohlcv(sym, limit=300)
        if df is not None and not df.empty:
            data[sym] = df
        else:
            for alt_ex in ['kucoin', 'kraken']:
                df = de.fetch_ohlcv(sym, limit=300, exchange_id=alt_ex)
                if df is not None and not df.empty:
                    data[sym] = df
                    break

    if not data:
        print("❌ No se obtuvieron datos reales.")
        return

    # Generar señales
    all_signals = []
    for sym, df in data.items():
        s = Signal(sym, df, DEFAULT_PARAMS)
        all_signals.append(s)

    longs = [s for s in all_signals if s.direction == 'Long' and s.is_valid]
    shorts = [s for s in all_signals if s.direction == 'Short' and s.is_valid]

    # Si no hay válidos, mostrar por score (aunque no aprueben)
    if not longs:
        longs = sorted([s for s in all_signals if s.score > 0], key=lambda x: abs(x.score), reverse=True)
    if not shorts:
        shorts = sorted([s for s in all_signals if s.score < 0], key=lambda x: abs(x.score), reverse=True)

    def pad_list(items, target=10):
        result = items[:target]
        while len(result) < target:
            result.append(None)
        return result

    longs_padded = pad_list(longs, 10)
    shorts_padded = pad_list(shorts, 10)

    # Mostrar Top 10 Long
    print("\n🟢 TOP 10 LONG")
    if longs_padded:
        data_long = []
        for i, s in enumerate(longs_padded):
            if s is None:
                data_long.append({'Pos': i+1, 'Activo': 'N/A', 'Score': 'N/A', 'ADX': 'N/A', 'KER': 'N/A', 'Aprobado': 'N/A', 'Motivo': 'No hay suficientes longs'})
            else:
                data_long.append({
                    'Pos': i+1,
                    'Activo': s.symbol,
                    'Score': round(s.score, 3),
                    'ADX': round(s.adx, 1),
                    'KER': round(s.ker, 2),
                    'Aprobado': '✅' if s.is_valid else '❌',
                    'Motivo': s.reason if not s.is_valid else ''
                })
        df_long = pd.DataFrame(data_long)
        print(df_long.to_string(index=False))
    else:
        print("   No hay señales Long.")

    # Mostrar Top 10 Short
    print("\n🔴 TOP 10 SHORT")
    if shorts_padded:
        data_short = []
        for i, s in enumerate(shorts_padded):
            if s is None:
                data_short.append({'Pos': i+1, 'Activo': 'N/A', 'Score': 'N/A', 'ADX': 'N/A', 'KER': 'N/A', 'Aprobado': 'N/A', 'Motivo': 'No hay suficientes shorts'})
            else:
                data_short.append({
                    'Pos': i+1,
                    'Activo': s.symbol,
                    'Score': round(s.score, 3),
                    'ADX': round(s.adx, 1),
                    'KER': round(s.ker, 2),
                    'Aprobado': '✅' if s.is_valid else '❌',
                    'Motivo': s.reason if not s.is_valid else ''
                })
        df_short = pd.DataFrame(data_short)
        print(df_short.to_string(index=False))
    else:
        print("   No hay señales Short.")

    print("\n" + "=" * 60)
    print("🧸 Fin del ranking. ¡A operar con cuidado!")

if __name__ == '__main__':
    main()
