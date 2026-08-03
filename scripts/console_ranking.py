#!/usr/bin/env python3
# scripts/console_ranking.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import logging
from datetime import datetime
import pandas as pd
import numpy as np

from data_engine import DataEngine
from signal_engine import Signal
from config import (
    ASSET_PARAMS, DEFAULT_PARAMS, INITIAL_CAPITAL, VERSION,
    EXCHANGE_PRIORITY, FALLBACK_SYMBOLS
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
    if hasattr(best, 'time_to_approval'):
        print(f"  ⏱️ Tiempo estimado para aprobación: {best.time_to_approval:.0f} min")
    print("-"*80)
    print()

def print_ranking(items, title, emoji, top_n=10):
    print(f"{emoji} TOP {top_n} {title}")
    # Rellenar hasta top_n con None
    display_items = items[:top_n]
    while len(display_items) < top_n:
        display_items.append(None)

    rows = []
    for i, s in enumerate(display_items):
        if s is None:
            rows.append({
                'Pos': i+1,
                'Activo': 'N/A',
                'Score': 'N/A',
                'Confianza': 'N/A',
                'Régimen': 'N/A',
                'Precio': 'N/A',
                'SL': 'N/A',
                'TP': 'N/A',
                'Aprobado': 'N/A',
                'Tiempo estimado': 'N/A',
            })
        else:
            rows.append({
                'Pos': i+1,
                'Activo': s.symbol,
                'Score': f"{s.score:.2%}" if hasattr(s, 'score') else 'N/A',
                'Confianza': f"{s.confidence:.2%}" if hasattr(s, 'confidence') else 'N/A',
                'Régimen': s.regime if hasattr(s, 'regime') else 'N/A',
                'Precio': f"${s.entry_price:.2f}" if hasattr(s, 'entry_price') else 'N/A',
                'SL': f"${s.sl_price:.2f}" if hasattr(s, 'sl_price') else 'N/A',
                'TP': f"${s.tp_price:.2f}" if hasattr(s, 'tp_price') else 'N/A',
                'Aprobado': '✅' if (hasattr(s, 'is_valid') and s.is_valid) else '❌',
                'Tiempo estimado': f"{s.time_to_approval:.0f} min" if hasattr(s, 'time_to_approval') else 'N/A',
            })
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    print()

def print_summary(signals):
    if not signals:
        print("⚠️ No hay señales (ni siquiera no aprobadas).")
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

def estimate_time_to_approval(signal):
    params = ASSET_PARAMS.get(signal.symbol, DEFAULT_PARAMS)
    min_score = params.get('min_score', DEFAULT_PARAMS['min_score'])
    adx_threshold = params.get('adx_threshold', DEFAULT_PARAMS['adx_threshold'])
    ker_threshold = params.get('ker_threshold', DEFAULT_PARAMS['ker_threshold'])

    score_gap = max(0, min_score - abs(signal.score))
    adx_gap = max(0, adx_threshold - signal.adx)
    ker_gap = max(0, ker_threshold - signal.ker)

    score_gap_norm = score_gap / min_score if min_score > 0 else 0
    adx_gap_norm = adx_gap / adx_threshold if adx_threshold > 0 else 0
    ker_gap_norm = ker_gap / ker_threshold if ker_threshold > 0 else 0

    minutos = (score_gap_norm * 30 + adx_gap_norm * 20 + ker_gap_norm * 20)
    if signal.is_valid:
        return 0
    if signal.score < 0:
        minutos *= 0.8
    return max(1, minutos)

def main():
    print_header()

    # 1. Obtener universo
    de = DataEngine()
    universe = de.get_common_pairs()
    if not universe:
        print("⚠️ No se encontraron pares comunes. Usando lista de fallback.")
        universe = FALLBACK_SYMBOLS

    print(f"📊 Escaneando {len(universe)} activos...")
    data_dict = {}

    # 2. Descargar datos para cada símbolo
    for sym in universe[:30]:
        df = de.fetch_ohlcv(sym, limit=200)
        if df is not None and not df.empty:
            data_dict[sym] = df

    # 3. Si no se obtuvieron datos reales, generar datos de muestra
    if not data_dict:
        print("❌ No se pudieron obtener datos reales. Generando datos de muestra...")
        for sym in universe[:10]:
            np.random.seed(42)
            periods = 300
            base_price = 50000 if 'BTC' in sym else 3000 if 'ETH' in sym else 100
            trend = np.cumsum(np.random.randn(periods) * 0.001) + 1
            close = base_price * trend
            high = close * (1 + np.random.rand(periods) * 0.01)
            low = close * (1 - np.random.rand(periods) * 0.01)
            open_price = close * (1 + np.random.randn(periods) * 0.002)
            volume = np.random.rand(periods) * 1000000
            dates = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
            df = pd.DataFrame({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            }, index=dates)
            data_dict[sym] = df
            print(f"📌 Datos de muestra generados para {sym}")

    # 4. Generar señales
    signals = []
    for sym, df in data_dict.items():
        params = ASSET_PARAMS.get(sym, DEFAULT_PARAMS)
        s = Signal(sym, df, params)
        s.time_to_approval = estimate_time_to_approval(s)
        signals.append(s)

    # 5. Ordenar por confianza (aprobadas primero)
    signals.sort(key=lambda x: (x.is_valid, x.confidence), reverse=True)

    longs = [s for s in signals if s.direction == 'Long']
    shorts = [s for s in signals if s.direction == 'Short']

    # 6. Mostrar resultados
    if signals:
        best = signals[0]
        print_best_trade(best)
        print_ranking(longs, "LONG", "🟢", top_n=10)
        print_ranking(shorts, "SHORT", "🔴", top_n=10)
        print_summary(signals)
    else:
        print("⚠️ No hay señales (ni siquiera no aprobadas).")
        print_ranking([], "LONG", "🟢", top_n=10)
        print_ranking([], "SHORT", "🔴", top_n=10)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
