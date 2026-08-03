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

# ============================================================
# FUNCIONES DE FORMATO
# ============================================================
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
    if not items:
        # Mostrar 10 filas con N/A
        print("  No hay señales. Mostrando N/A:")
        df = pd.DataFrame([{
            'Pos': i+1,
            'Activo': 'N/A',
            'Score': 'N/A',
            'Confianza': 'N/A',
            'Régimen': 'N/A',
            'Precio': 'N/A',
            'SL': 'N/A',
            'TP': 'N/A',
        } for i in range(top_n)])
        print(df.to_string(index=False))
    else:
        df = pd.DataFrame([{
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
        } for i, s in enumerate(items[:top_n])])
        # Rellenar hasta 10 filas si faltan
        while len(df) < top_n:
            df = pd.concat([df, pd.DataFrame([{
                'Pos': len(df)+1,
                'Activo': 'N/A',
                'Score': 'N/A',
                'Confianza': 'N/A',
                'Régimen': 'N/A',
                'Precio': 'N/A',
                'SL': 'N/A',
                'TP': 'N/A',
                'Aprobado': 'N/A',
                'Tiempo estimado': 'N/A',
            }])], ignore_index=True)
        print(df.to_string(index=False))
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

def estimate_time_to_approval(signal):
    """
    Estima el tiempo hasta la aprobación basado en la distancia a los umbrales.
    """
    params = ASSET_PARAMS.get(signal.symbol, DEFAULT_PARAMS)
    min_score = params.get('min_score', DEFAULT_PARAMS['min_score'])
    adx_threshold = params.get('adx_threshold', DEFAULT_PARAMS['adx_threshold'])
    ker_threshold = params.get('ker_threshold', DEFAULT_PARAMS['ker_threshold'])

    # Distancia a cada umbral
    score_gap = max(0, min_score - abs(signal.score))
    adx_gap = max(0, adx_threshold - signal.adx)
    ker_gap = max(0, ker_threshold - signal.ker)

    # Normalizar (valores relativos)
    score_gap_norm = score_gap / min_score if min_score > 0 else 0
    adx_gap_norm = adx_gap / adx_threshold if adx_threshold > 0 else 0
    ker_gap_norm = ker_gap / ker_threshold if ker_threshold > 0 else 0

    # Heurística: cada unidad de gap equivale a ~30 minutos
    minutos = (score_gap_norm * 30 + adx_gap_norm * 20 + ker_gap_norm * 20)

    # Si ya está aprobado, tiempo = 0
    if signal.is_valid:
        return 0

    # Si el score es negativo (dirección Short), ajustar
    if signal.score < 0:
        minutos *= 0.8

    return max(1, minutos)

def main():
    print_header()
    try:
        de = DataEngine()
        universe = de.get_common_pairs()
        if not universe:
            print("⚠️ No se encontraron pares comunes. Usando lista de fallback.")
            universe = FALLBACK_SYMBOLS

        print(f"📊 Escaneando {len(universe)} activos...")
        data_dict = {}
        for sym in universe[:30]:  # Aumentamos a 30 para más cobertura
            df = de.fetch_ohlcv(sym, limit=200)
            if df is not None and not df.empty:
                data_dict[sym] = df

        if not data_dict:
            print("❌ No se pudieron obtener datos reales. Verifica conectividad.")
            sys.exit(1)

        signals = []
        for sym, df in data_dict.items():
            params = ASSET_PARAMS.get(sym, DEFAULT_PARAMS)
            s = Signal(sym, df, params)
            # Añadir tiempo estimado a la señal
            s.time_to_approval = estimate_time_to_approval(s)
            signals.append(s)

        # Ordenar por confianza (las aprobadas primero)
        signals.sort(key=lambda x: (x.is_valid, x.confidence), reverse=True)

        # Separar Long y Short (TODOS, incluso no aprobados)
        longs = [s for s in signals if s.direction == 'Long']
        shorts = [s for s in signals if s.direction == 'Short']

        # Mostrar siempre Top 10 (aunque no estén aprobados)
        if signals:
            # Mejor trade (el primero de la lista)
            best = signals[0]
            print_best_trade(best)
            print_ranking(longs, "LONG", "🟢", top_n=10)
            print_ranking(shorts, "SHORT", "🔴", top_n=10)
            print_summary(signals)
        else:
            print("⚠️ No hay señales (ni siquiera no aprobadas).")
            print_ranking([], "LONG", "🟢", top_n=10)
            print_ranking([], "SHORT", "🔴", top_n=10)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
