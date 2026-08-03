#!/usr/bin/env python3
# scripts/console_ranking.py
import sys
import os
# Asegurar que la raíz del proyecto esté en el PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import logging
from datetime import datetime
import pandas as pd
import numpy as np

from data_engine import DataEngine
from signal_engine import Signal
from config import (
    ASSET_PARAMS, DEFAULT_PARAMS, INITIAL_CAPITAL, VERSION, EXCHANGE_PRIORITY
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def print_header():
    print("="*80)
    print(f"  🧸 JUNK TOYS — RANKING EN CONSOLA v{VERSION}")
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
    print(f"  🔌 Exchanges activos: {', '.join(EXCHANGE_PRIORITY)}")
    print("="*80)
    print()

def print_best_trade(best):
    print("🏆 MEJOR TRADE")
    print("-"*80)
    print(f"  Activo:     {best.symbol}")
    print(f"  Dirección:  {best.direction}")
    print(f"  Score:      {best.score:.2%}")
    print(f"  Confianza:  {best.confidence:.2%}")
    print(f"  Régimen:    {best.regime}")
    print(f"  Precio:     ${best.entry_price:.2f}")
    sl_pct = (best.entry_price - best.sl_price) / best.entry_price * 100
    tp_pct = (best.tp_price - best.entry_price) / best.entry_price * 100
    print(f"  SL:         ${best.sl_price:.2f} ({sl_pct:.2f}%)")
    print(f"  TP:         ${best.tp_price:.2f} ({tp_pct:.2f}%)")
    print(f"  Trailing:   Act. {best.trailing_activation*100:.1f}% | Dist. {best.trailing_distance*100:.1f}%")
    print(f"  BE Trigger: {best.break_even_trigger*100:.1f}%")
    print("-"*80)
    print()

def print_ranking(longs, shorts, top_n=10):
    print("🟢 TOP 10 LONG")
    if longs:
        df = pd.DataFrame([{
            'Pos': i+1,
            'Activo': s.symbol,
            'Score': f"{s.score:.2%}",
            'Confianza': f"{s.confidence:.2%}",
            'Régimen': s.regime,
            'Precio': f"${s.entry_price:.2f}",
            'SL': f"${s.sl_price:.2f}",
            'TP': f"${s.tp_price:.2f}",
        } for i, s in enumerate(longs[:top_n])])
        print(df.to_string(index=False))
    else:
        print("  No hay señales Long.")
    print()

    print("🔴 TOP 10 SHORT")
    if shorts:
        df = pd.DataFrame([{
            'Pos': i+1,
            'Activo': s.symbol,
            'Score': f"{s.score:.2%}",
            'Confianza': f"{s.confidence:.2%}",
            'Régimen': s.regime,
            'Precio': f"${s.entry_price:.2f}",
            'SL': f"${s.sl_price:.2f}",
            'TP': f"${s.tp_price:.2f}",
        } for i, s in enumerate(shorts[:top_n])])
        print(df.to_string(index=False))
    else:
        print("  No hay señales Short.")
    print()

def print_summary(signals):
    if not signals:
        print("⚠️ No hay señales válidas en este momento.")
        return
    longs = [s for s in signals if s.direction == 'Long']
    shorts = [s for s in signals if s.direction == 'Short']
    print("📊 RESUMEN")
    print("-"*80)
    print(f"  Total señales:  {len(signals)}")
    print(f"  Long:           {len(longs)}")
    print(f"  Short:          {len(shorts)}")
    if signals:
        avg_score = np.mean([s.score for s in signals])
        avg_conf = np.mean([s.confidence for s in signals])
        print(f"  Score promedio: {avg_score:.2%}")
        print(f"  Confianza promedio: {avg_conf:.2%}")
    print("="*80)

def main():
    print_header()
    try:
        de = DataEngine()
        universe = de.get_common_pairs()
        if not universe:
            print("⚠️ No se encontraron pares comunes. Verifica conectividad.")
            sys.exit(1)

        print(f"📊 Escaneando {len(universe)} activos...")
        data_dict = {}
        for sym in universe[:20]:
            df = de.fetch_ohlcv(sym, limit=200)
            if df is not None and not df.empty:
                data_dict[sym] = df

        if not data_dict:
            print("❌ No se pudieron obtener datos reales.")
            sys.exit(1)

        signals = []
        for sym, df in data_dict.items():
            params = ASSET_PARAMS.get(sym, DEFAULT_PARAMS)
            s = Signal(sym, df, params)
            if s.is_valid:
                signals.append(s)

        signals.sort(key=lambda x: x.confidence, reverse=True)
        longs = [s for s in signals if s.direction == 'Long']
        shorts = [s for s in signals if s.direction == 'Short']

        if signals:
            best = signals[0]
            print_best_trade(best)
            print_ranking(longs, shorts, top_n=10)
            print_summary(signals)
        else:
            print("⚠️ No hay señales válidas en este momento.")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
