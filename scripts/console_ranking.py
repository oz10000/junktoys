#!/usr/bin/env python3
# scripts/console_ranking.py
"""
JUNK TOYS — Ranking en consola (ASCII)
Muestra el Top 10 Long/Short, el mejor trade y estadísticas.
Se ejecuta sin Streamlit, ideal para GitHub Actions.
"""

import sys
import os
import time
import logging
from datetime import datetime
import pandas as pd
import numpy as np

# Añadir el directorio raíz al path para importar módulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_engine import DataEngine
from signal_engine import Signal
from config import (
    ASSET_PARAMS, DEFAULT_PARAMS, UNIVERSE,
    EXCHANGE_PRIORITY, INITIAL_CAPITAL, VERSION
)
from utils import format_currency

# Configurar logging para que sea menos verboso
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ============================================================
# FUNCIONES DE FORMATO
# ============================================================
def print_header():
    """Muestra el encabezado del ranking."""
    print("="*80)
    print(f"  🧸 JUNK TOYS — RANKING EN CONSOLA v{VERSION}")
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
    print(f"  🔌 Exchanges activos: {', '.join(EXCHANGE_PRIORITY)}")
    print("="*80)
    print()

def print_best_trade(best):
    """Muestra los detalles del mejor trade."""
    print("🏆 MEJOR TRADE")
    print("-"*80)
    print(f"  Activo:     {best.symbol}")
    print(f"  Dirección:  {best.direction}")
    print(f"  Score:      {best.score:.2%}")
    print(f"  Confianza:  {best.confidence:.2%}")
    print(f"  Régimen:    {best.regime}")
    print(f"  Precio:     ${best.entry_price:.2f}")
    print(f"  SL:         ${best.sl_price:.2f} ({((best.entry_price - best.sl_price) / best.entry_price * 100):.2f}%)")
    print(f"  TP:         ${best.tp_price:.2f} ({((best.tp_price - best.entry_price) / best.entry_price * 100):.2f}%)")
    print(f"  Trailing:   Act. {best.trailing_activation*100:.1f}% | Dist. {best.trailing_distance*100:.1f}%")
    print(f"  BE Trigger: {best.break_even_trigger*100:.1f}%")
    print("-"*80)
    print()

def print_ranking(longs, shorts, top_n=10):
    """Muestra el Top 10 Long y Top 10 Short en tablas ASCII."""
    # Top Long
    print("🟢 TOP 10 LONG")
    if longs:
        df_long = pd.DataFrame([{
            'Pos': i+1,
            'Activo': s.symbol,
            'Score': f"{s.score:.2%}",
            'Confianza': f"{s.confidence:.2%}",
            'Régimen': s.regime,
            'Precio': f"${s.entry_price:.2f}",
            'SL': f"${s.sl_price:.2f}",
            'TP': f"${s.tp_price:.2f}",
        } for i, s in enumerate(longs[:top_n])])
        print(df_long.to_string(index=False))
    else:
        print("  No hay señales Long.")
    print()

    # Top Short
    print("🔴 TOP 10 SHORT")
    if shorts:
        df_short = pd.DataFrame([{
            'Pos': i+1,
            'Activo': s.symbol,
            'Score': f"{s.score:.2%}",
            'Confianza': f"{s.confidence:.2%}",
            'Régimen': s.regime,
            'Precio': f"${s.entry_price:.2f}",
            'SL': f"${s.sl_price:.2f}",
            'TP': f"${s.tp_price:.2f}",
        } for i, s in enumerate(shorts[:top_n])])
        print(df_short.to_string(index=False))
    else:
        print("  No hay señales Short.")
    print()

def print_summary(signals):
    """Muestra estadísticas resumidas."""
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
    """Función principal."""
    print_header()

    # Inicializar DataEngine
    try:
        de = DataEngine()
        universe = de.get_common_pairs()
        if not universe:
            print("⚠️ No se encontraron pares comunes. Verifica conectividad.")
            sys.exit(1)

        print(f"📊 Escaneando {len(universe)} activos...")
        data_dict = {}
        for sym in universe[:20]:  # Limitamos a 20 para rapidez
            df = de.fetch_ohlcv(sym, limit=200)
            if df is not None and not df.empty:
                data_dict[sym] = df

        if not data_dict:
            print("❌ No se pudieron obtener datos reales.")
            sys.exit(1)

        # Generar señales
        signals = []
        for sym, df in data_dict.items():
            params = ASSET_PARAMS.get(sym, DEFAULT_PARAMS)
            s = Signal(sym, df, params)
            if s.is_valid:
                signals.append(s)

        # Ordenar por confianza
        signals.sort(key=lambda x: x.confidence, reverse=True)

        # Separar Long y Short
        longs = [s for s in signals if s.direction == 'Long']
        shorts = [s for s in signals if s.direction == 'Short']

        if signals:
            # Mejor trade
            best = signals[0]
            print_best_trade(best)

            # Ranking
            print_ranking(longs, shorts, top_n=10)
            print_summary(signals)
        else:
            print("⚠️ No hay señales válidas en este momento.")
            print("   Puede deberse a que el mercado está en rango o los filtros son muy estrictos.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
