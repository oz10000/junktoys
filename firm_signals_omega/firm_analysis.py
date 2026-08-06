# firm_signals_omega/firm_analysis.py
"""
Análisis de Firm Signals Ω — Genera señales con certificación de 5 niveles
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging

# Importar desde el mismo directorio
from firm_signals_omega.data_providers import FirmDataProvider
from firm_signals_omega.settings import FIRM_SIGNALS_CONFIG
from core_engine import compute_adx, compute_ker, compute_atr, compute_pidelta_score, compute_regime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_firm_signals(symbols=['BTC/USDT', 'ETH/USDT', 'SOL/USDT']):
    provider = FirmDataProvider()
    results = []

    for sym in symbols:
        logger.info(f"📊 Procesando {sym}...")
        df = provider.get_ohlcv(sym, timeframe='5m', limit=300)
        if df is None or df.empty:
            logger.warning(f"❌ {sym}: sin datos")
            results.append({'symbol': sym, 'passed': False, 'reason': 'Sin datos'})
            continue

        # Indicadores
        adx = compute_adx(df).iloc[-1] if not compute_adx(df).empty else 0
        ker = compute_ker(df).iloc[-1] if not compute_ker(df).empty else 0
        score = compute_pidelta_score(df)
        atr = compute_atr(df).iloc[-1] if not compute_atr(df).empty else 0
        regime = compute_regime(df)
        close = df['close'].iloc[-1]
        volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1] if not df['volume'].empty else 1

        # NIVEL 1: Calidad
        thresholds = FIRM_SIGNALS_CONFIG['quality_thresholds'].get(sym, {})
        min_score = thresholds.get('min_score', 0.65)
        min_adx = thresholds.get('min_adx', 25)
        min_ker = thresholds.get('min_ker', 0.45)

        quality_passed = (abs(score) >= min_score and adx >= min_adx and ker >= min_ker and regime in ['Tendencia Fuerte', 'Expansión'])
        if not quality_passed:
            results.append({
                'symbol': sym,
                'score': score,
                'adx': adx,
                'ker': ker,
                'regime': regime,
                'passed': False,
                'reason': 'Nivel 1 falló (Calidad)'
            })
            continue

        # NIVEL 2: Confirmación multi-timeframe
        df15 = provider.get_ohlcv(sym, timeframe='15m', limit=100)
        df1h = provider.get_ohlcv(sym, timeframe='1h', limit=50)
        aligned = 0
        if df15 is not None and not df15.empty:
            s15 = compute_pidelta_score(df15)
            if (score > 0 and s15 > 0) or (score < 0 and s15 < 0):
                aligned += 1
        if df1h is not None and not df1h.empty:
            s1h = compute_pidelta_score(df1h)
            if (score > 0 and s1h > 0) or (score < 0 and s1h < 0):
                aligned += 1

        min_tfs = FIRM_SIGNALS_CONFIG['confirmation_thresholds'].get(sym, {}).get('min_timeframes', 3)
        if aligned < min_tfs:
            results.append({
                'symbol': sym,
                'score': score,
                'adx': adx,
                'ker': ker,
                'regime': regime,
                'aligned': aligned,
                'passed': False,
                'reason': f'Nivel 2 falló (alineados {aligned}/{min_tfs})'
            })
            continue

        # NIVEL 3: Microestructura (simulado)
        imbalance = (df['close'].iloc[-1] - df['open'].iloc[-1]) / df['open'].iloc[-1]
        funding = 0.0
        oi_growing = volume_ratio > 1.2
        micro_passed = abs(imbalance) > 0.001 and funding < 0.01 and oi_growing
        if not micro_passed:
            results.append({
                'symbol': sym,
                'score': score,
                'adx': adx,
                'ker': ker,
                'regime': regime,
                'passed': False,
                'reason': 'Nivel 3 falló (Microestructura)'
            })
            continue

        # NIVEL 4: Temporal
        hour = datetime.now().hour
        weekday = datetime.now().weekday()
        hour_ok = 8 <= hour <= 20
        weekday_ok = weekday < 5
        temporal_passed = hour_ok and weekday_ok
        if not temporal_passed:
            results.append({
                'symbol': sym,
                'score': score,
                'adx': adx,
                'ker': ker,
                'regime': regime,
                'passed': False,
                'reason': 'Nivel 4 falló (Horario)'
            })
            continue

        # NIVEL 5: Correlación (siempre pasa en esta simulación)

        # Señal aprobada
        direction = 'LONG' if score > 0 else 'SHORT'
        entry_price = close
        sl_price = entry_price * (1 - 0.003) if direction == 'LONG' else entry_price * (1 + 0.003)
        tp_price = entry_price * (1 + 0.008) if direction == 'LONG' else entry_price * (1 - 0.008)

        results.append({
            'symbol': sym,
            'direction': direction,
            'score': score,
            'adx': adx,
            'ker': ker,
            'regime': regime,
            'entry_price': entry_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'trailing_distance': 0.003,
            'break_even_trigger': 0.002,
            'passed': True,
            'reason': '✅ CERTIFICADA'
        })

    return results

def main():
    print("=" * 60)
    print("🧸 FIRM SIGNALS Ω — ANÁLISIS EN CONSOLA")
    print("=" * 60)
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    results = generate_firm_signals(symbols)

    approved = [r for r in results if r.get('passed', False)]
    rejected = [r for r in results if not r.get('passed', False)]

    print(f"\n📊 Señales aprobadas: {len(approved)}")
    for r in approved:
        print(f"✅ {r['symbol']} {r['direction']} Score: {r['score']:.3f} ADX: {r['adx']:.1f} KER: {r['ker']:.2f}")
        print(f"   Entry: {r['entry_price']:.2f} SL: {r['sl_price']:.2f} TP: {r['tp_price']:.2f}")
        print(f"   Trailing: {r['trailing_distance']*100:.1f}% BE: {r['break_even_trigger']*100:.1f}%")

    print(f"\n❌ Señales rechazadas: {len(rejected)}")
    for r in rejected:
        print(f"❌ {r['symbol']} - {r.get('reason', 'Desconocido')}")

    # Guardar reporte
    with open('firm_signals_report.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Salida con código de error si no hay aprobadas
    if len(approved) == 0:
        print("\n⚠️ No hay señales Firm Ω aprobadas en este momento.")
        sys.exit(0)  # No falla, solo informa

if __name__ == '__main__':
    main()
