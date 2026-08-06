# firm_signals_omega/streamlit_panel.py
"""
Panel de Streamlit para Firm Signals Ω
Muestra información contextual sobre la mejor señal actual y estimaciones dinámicas.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from .config import FIRM_SIGNALS_CONFIG
from .helpers import (
    estimate_next_opportunity,
    calculate_support_resistance,
    suggest_leverage,
    format_signal_reason
)
from .next_trade_engine import NextTradeEngine
from utils import format_currency

def render_firm_signals_panel():
    """Renderiza el panel de Firm Signals Ω con estimación de tiempo dinámica."""

    st.header("🧸 Firm Signals Ω — Panel de Ejecución")

    # Verificar que existan datos en session_state
    if 'all_rankings' not in st.session_state or not st.session_state.all_rankings:
        st.info("⏳ No hay señales disponibles. Actualiza el ranking principal.")
        if st.button("🔄 Actualizar Ranking", type="secondary"):
            st.session_state.last_refresh = None
            st.rerun()
        return

    # Tomar la mejor señal (la primera del ranking)
    all_rankings = st.session_state.all_rankings
    best = all_rankings[0] if all_rankings else None

    # Obtener historial de señales
    signal_history = st.session_state.get('signal_history', [])
    # Obtener historial de Firm Signals (si existe)
    firm_history = st.session_state.get('firm_signal_history', [])

    if not best:
        st.warning("No hay señales disponibles en el ranking.")
        return

    # === INFORMACIÓN DE LA SEÑAL ===
    is_valid = best.get('is_valid', False)
    symbol = best.get('symbol', 'N/A')
    direction = best.get('direction', 'N/A')
    score = best.get('score', 0)
    confidence = best.get('confidence', 0)
    regime = best.get('regime', 'N/A')
    entry_price = best.get('entry_price', 0)
    sl_price = best.get('sl_price', 0)
    tp_price = best.get('tp_price', 0)

    # === ESTIMACIÓN DE TIEMPO CON NEXT TRADE ENGINE ===
    # Inicializar motor
    engine = NextTradeEngine({})
    engine.update_history(signal_history, firm_history)

    # Obtener variables actuales
    adx = best.get('adx', 20)
    atr_pct = best.get('atr_pct', 0.1)
    now = datetime.now()
    current_minute = (now.minute % 5)  # minutos dentro de la vela de 5m
    last_signal_time = signal_history[-1]['timestamp'] if signal_history else None

    # Estimar para Trade Óptimo y Firm Signals
    result_opt = engine.estimate(regime, adx, atr_pct, current_minute, last_signal_time, is_firm=False)
    result_firm = engine.estimate(regime, adx, atr_pct, current_minute, last_signal_time, is_firm=True)

    # === SOPORTES Y RESISTENCIAS ===
    df = st.session_state.data_dict.get(symbol) if 'data_dict' in st.session_state else None
    sr = calculate_support_resistance(df, entry_price) if df is not None else {}

    # === APALANCAMIENTO SUGERIDO ===
    atr_pct_decimal = best.get('atr_pct', 0.01) / 100
    lev = suggest_leverage(atr_pct_decimal, confidence, max_leverage=10, min_leverage=1)

    # === MOSTRAR PANEL ===

    # Estado general con semáforo
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if is_valid:
            st.metric("📡 Estado", "PUBLICADA ✅")
        else:
            st.metric("📡 Estado", f"ESPERAR ⏳ ({result_opt['status']})")
    with col2:
        st.metric("📊 Progreso", "100%" if is_valid else f"{min(100, int(1/result_opt['expected_time_minutes']*100))}%")
    with col3:
        countdown = engine.get_countdown(result_opt['expected_time_minutes'])
        st.metric("⏰ Próxima señal", countdown)

    # Semáforo grande
    status_colors = {
        'VERDE': '🟢',
        'AMARILLO': '🟡',
        'NARANJA': '🟠',
        'ROJO': '🔴',
        'AZUL': '🔵'
    }
    st.markdown(f"## {status_colors.get(result_opt['status'], '⚪')} Estado: {result_opt['status']}")
    st.caption(result_opt.get('recommendation', ''))

    # Señal actual
    st.markdown("---")
    st.subheader("🎯 Señal Actual")

    if is_valid:
        st.success(f"**{symbol} — {direction}** (Score: {score:.3f})")
    else:
        st.warning(f"⚠️ No hay señal válida. La mejor candidata es {symbol} (Score: {score:.3f})")

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Precio entrada", format_currency(entry_price))
        st.metric("Stop Loss", format_currency(sl_price) + f" ({(sl_price/entry_price-1)*100:.2f}%)" if entry_price else "N/A")
        st.metric("Take Profit", format_currency(tp_price) + f" ({(tp_price/entry_price-1)*100:.2f}%)" if entry_price else "N/A")
    with col_b:
        st.metric("Confianza", f"{confidence*100:.1f}%" if confidence else "N/A")
        st.metric("Régimen", regime)
        st.metric("Apalancamiento sugerido", f"{lev['recommended']}x", delta=f"Máx: {lev['max_allowed']}x")

    # Soportes / Resistencias
    if sr.get('support') or sr.get('resistance'):
        st.markdown("---")
        st.subheader("📊 Soportes y Resistencias")
        col_s, col_r = st.columns(2)
        with col_s:
            st.metric("Soporte", format_currency(sr['support']) if sr['support'] else "N/A",
                     delta=f"{sr['distance_support']:.2f}% por debajo" if sr['distance_support'] else None)
        with col_r:
            st.metric("Resistencia", format_currency(sr['resistance']) if sr['resistance'] else "N/A",
                     delta=f"{sr['distance_resistance']:.2f}% por encima" if sr['distance_resistance'] else None)

    # Razón de aprobación
    if is_valid:
        st.markdown("---")
        st.subheader("📋 Razón de aprobación")
        reason = format_signal_reason(best)
        st.info(reason)

    # Estimación de tiempo detallada
    st.markdown("---")
    st.subheader("⏳ Estimación de próximas oportunidades")
    cols = st.columns(4)
    probs_opt = [
        ('15 min', result_opt.get('probability_15min', 0)),
        ('30 min', result_opt.get('probability_30min', 0)),
        ('1 h', result_opt.get('probability_60min', 0)),
        ('3 h', result_opt.get('probability_180min', 0)),
    ]
    for i, (label, prob) in enumerate(probs_opt):
        with cols[i]:
            st.metric(label, f"{prob*100:.0f}%")

    # Detalles avanzados (expander)
    with st.expander("📈 Detalles avanzados"):
        st.json({
            "Score": score,
            "ADX": best.get('adx', 0),
            "KER": best.get('ker', 0),
            "ATR%": best.get('atr_pct', 0),
            "Amplitud": best.get('amplitude_pct', 0),
            "Tasa de llegada (señales/min)": f"{result_opt['rate_per_minute']:.4f}",
            "Confianza de estimación": f"{result_opt['confidence']*100:.0f}%",
            "Estado semáforo": result_opt['status'],
            "Próxima señal estimada": result_opt['expected_time_minutes'],
        })
