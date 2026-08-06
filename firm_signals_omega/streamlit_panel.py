# firm_signals_omega/streamlit_panel.py
"""
Panel de Streamlit para Firm Signals Ω
Muestra información contextual sobre la mejor señal actual y estimaciones.
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
from utils import format_currency

def render_firm_signals_panel():
    """Renderiza el panel de Firm Signals Ω"""

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

    # === ESTIMACIÓN DE TIEMPO ===
    estimation = estimate_next_opportunity(best, signal_history)

    # === SOPORTES Y RESISTENCIAS ===
    df = st.session_state.data_dict.get(symbol) if 'data_dict' in st.session_state else None
    sr = calculate_support_resistance(df, entry_price) if df is not None else {}

    # === APALANCAMIENTO SUGERIDO ===
    atr_pct = best.get('atr_pct', 0.01) / 100  # convertimos a decimal
    lev = suggest_leverage(atr_pct, confidence, max_leverage=10, min_leverage=1)

    # === VENTANA DE VALIDEZ ===
    validity_window = "15 - 25 minutos" if is_valid else "N/A"

    # === MOSTRAR PANEL ===

    # Estado general
    col1, col2, col3 = st.columns(3)
    col1.metric("📡 Estado", "PUBLICADA ✅" if is_valid else "ESPERAR ⏳")
    col2.metric("📊 Progreso", "100%" if is_valid else f"{estimation.get('remaining_minutes', 0):.0f}%")
    col3.metric("⏰ Próxima revisión", estimation.get('remaining_minutes', 0) < 1 and "Ahora" or f"{estimation.get('remaining_minutes', 0):.0f} min")

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

    # Estimación de tiempo
    st.markdown("---")
    st.subheader("⏳ Estimación de próximas oportunidades")
    cols = st.columns(4)
    probs = [
        ('15 min', estimation.get('probability_15min', 0)),
        ('30 min', estimation.get('probability_30min', 0)),
        ('1 h', estimation.get('probability_1h', 0)),
        ('3 h', estimation.get('probability_3h', 0)),
    ]
    for i, (label, prob) in enumerate(probs):
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
            "Volumen relativo": "N/A",
            "Trailing stop": f"{best.get('trailing_distance', 0)*100:.2f}%",
            "Break-even trigger": f"{best.get('break_even_trigger', 0)*100:.2f}%",
            "Tiempo máximo": f"{best.get('max_hold_minutes', 0)} min",
        })
