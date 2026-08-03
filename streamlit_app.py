# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import logging

from data_engine import DataEngine
from config import (
    INITIAL_CAPITAL, DEFAULT_PARAMS, VERSION, PROJECT_NAME,
    TIMEFRAME, KILL_SWITCH, ENTRY_ZONES, FALLBACK_SYMBOLS
)
from signal_engine import Signal
from core_engine import compute_atr, compute_adx, compute_ker
from utils import format_currency

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="🧸 Junk Toys v6.2.1 — Estabilización",
    page_icon="🧸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# ESTILOS (colorido y juguetón)
# ============================================================
st.markdown("""
    <style>
        .reportview-container .main .block-container {
            background: linear-gradient(145deg, #fdf6e3 0%, #fce8b2 100%);
        }
        .sidebar .sidebar-content { background: #ffd700; }
        .stButton button {
            background-color: #ff6b6b;
            color: white;
            border-radius: 20px;
            border: 3px solid #ffd93d;
            font-weight: bold;
            font-size: 1.2rem;
            padding: 0.5rem 1.5rem;
        }
        .stButton button:hover {
            background-color: #ff4757;
            transform: scale(1.02);
        }
        .trade-card {
            background: #ffffff;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin: 10px 0;
            border-left: 5px solid #ffd700;
        }
        .approved { color: green; font-weight: bold; }
        .rejected { color: red; font-weight: bold; }
        .zone-a { border-left-color: #4CAF50; }
        .zone-b { border-left-color: #FF9800; }
        .zone-c { border-left-color: #F44336; }
        .trailing-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 5px 0;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# TÍTULO
# ============================================================
st.title(f"🧸🎉🧸 {PROJECT_NAME} 🧸🎉🧸")
st.subheader(f"🐻🐻🐻 v{VERSION} — Asistente de Ejecución Manual 🐻🐻🐻")
st.markdown("---")

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/000000/teddy-bear-emoji.png", width=80)
    st.header("⚙️ Configuración")
    use_hour_filter = st.checkbox("🕒 Filtro horario (Argentina)", value=True)
    trailing_mode = st.selectbox("🎯 Trailing", ["Con activación", "Sin activación"], index=0)
    trailing_activation_enabled = (trailing_mode == "Con activación")
    st.markdown("---")
    st.header("🚀 Acciones")
    refresh_btn = st.button("🔄 Actualizar Ranking", type="primary", use_container_width=True)
    run_backtest_btn = st.button("🧪 Backtesting", type="secondary", use_container_width=True)
    st.markdown("---")
    st.header("📊 Estado")
    st.caption(f"Capital: {format_currency(INITIAL_CAPITAL)}")
    st.caption(f"Timeframe: {TIMEFRAME}")
    st.caption(f"Activos certificados: {len(st.session_state.get('certified_symbols', FALLBACK_SYMBOLS[:10]))}")
    st.caption(f"🧸 Junk Toys v{VERSION}")

# ============================================================
# INICIALIZACIÓN
# ============================================================
if 'data_engine' not in st.session_state:
    st.session_state.data_engine = DataEngine()
    # Intentar obtener activos certificados
    with st.spinner("🔄 Certificando activos..."):
        try:
            st.session_state.certified_symbols = st.session_state.data_engine.get_certified_assets()
        except Exception as e:
            st.warning(f"Error en certificación: {e}. Usando fallback.")
            st.session_state.certified_symbols = FALLBACK_SYMBOLS[:10]
        if not st.session_state.certified_symbols:
            st.session_state.certified_symbols = FALLBACK_SYMBOLS[:10]
        st.session_state.symbols = st.session_state.certified_symbols
        st.session_state.data_dict = {}
        st.session_state.last_refresh = None
        st.session_state.signal_history = []

# ============================================================
# FUNCIÓN PARA ESCANEAR Y RANKEAR
# ============================================================
def scan_and_rank():
    de = st.session_state.data_engine
    symbols = st.session_state.certified_symbols
    data_dict = {}

    # Descargar datos para los activos certificados
    for sym in symbols[:30]:
        df = de.fetch_ohlcv(sym, limit=300)
        if df is not None and not df.empty:
            data_dict[sym] = df
        else:
            # Intentar con otro exchange
            for alt_ex in ['kucoin', 'mexc', 'kraken']:
                df = de.fetch_ohlcv(sym, limit=300, exchange_id=alt_ex)
                if df is not None and not df.empty:
                    data_dict[sym] = df
                    break

    if not data_dict:
        logger.warning("No se obtuvieron datos, usando fallback")
        for sym in symbols[:10]:
            df = de.fetch_ohlcv(sym, limit=100)
            if df is not None and not df.empty:
                data_dict[sym] = df

    st.session_state.data_dict = data_dict
    st.session_state.last_refresh = datetime.now()

    # Generar señales para todos los activos (aprobados o no)
    all_rankings = []
    valid_signals = []

    for sym, df in data_dict.items():
        s = Signal(sym, df, DEFAULT_PARAMS)
        adx_val = compute_adx(df).iloc[-1] if not compute_adx(df).empty else 0
        ker_val = compute_ker(df, 10).iloc[-1] if not compute_ker(df).empty else 0
        atr_val = compute_atr(df).iloc[-1] if not compute_atr(df).empty else 0
        atr_pct = atr_val / s.entry_price * 100 if s.entry_price > 0 else 0

        rank_entry = {
            'symbol': sym,
            'signal': s,
            'score': s.score,
            'adx': adx_val,
            'ker': ker_val,
            'atr_pct': atr_pct,
            'direction': s.direction if s.is_valid else 'N/A',
            'is_valid': s.is_valid,
            'reason': s.reason if not s.is_valid else '✅ Aprobado',
            'entry_price': s.entry_price if s.is_valid else 0,
            'sl_price': s.sl_price if s.is_valid else 0,
            'tp_price': s.tp_price if s.is_valid else 0,
            'confidence': s.confidence if s.is_valid else 0,
            'regime': s.regime,
            'trailing_activation': s.trailing_activation if s.is_valid else 0,
            'trailing_distance': s.trailing_distance if s.is_valid else 0,
            'break_even_trigger': s.break_even_trigger if s.is_valid else 0,
            'break_even_buffer': s.break_even_buffer if s.is_valid else 0,
            'max_hold_minutes': s.max_hold_minutes if s.is_valid else 0,
        }
        all_rankings.append(rank_entry)
        if s.is_valid:
            valid_signals.append(s)

    all_rankings.sort(key=lambda x: abs(x['score']), reverse=True)
    return all_rankings, valid_signals

# ============================================================
# ESTIMACIÓN DE TIEMPO HASTA PRÓXIMA SEÑAL
# ============================================================
def estimate_next_signal(signal_history):
    if len(signal_history) < 3:
        return None
    valid_times = [s['timestamp'] for s in signal_history if s.get('is_valid', False)]
    if len(valid_times) < 2:
        return None
    intervals = [(valid_times[i+1] - valid_times[i]).total_seconds() / 60 for i in range(len(valid_times)-1)]
    avg_interval = np.mean(intervals)
    std_interval = np.std(intervals)
    last_time = valid_times[-1]
    now = datetime.now()
    elapsed = (now - last_time).total_seconds() / 60
    remaining = max(0, avg_interval - elapsed)
    return {
        'avg_minutes': avg_interval,
        'remaining_minutes': remaining,
        'std_minutes': std_interval,
        'confidence': 1 - (std_interval / avg_interval) if avg_interval > 0 else 0
    }

# ============================================================
# FUNCIÓN PARA MOSTRAR DETALLES COMPLETOS DE UNA SEÑAL
# ============================================================
def display_signal_details(r, with_trailing=True):
    if not r['is_valid']:
        st.json({
            "Activo": r['symbol'],
            "Score": r['score'],
            "ADX": r['adx'],
            "KER": r['ker'],
            "ATR%": r['atr_pct'],
            "Régimen": r['regime'],
            "Estado": "❌ RECHAZADO",
            "Motivo": r['reason']
        })
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📊 Entrada**")
        st.write(f"Precio: ${r['entry_price']:.4f}")
        st.write(f"Dirección: {r['direction']}")
        st.write(f"Score: {r['score']:.3f}")
        st.write(f"Confianza: {r['confidence']:.2%}")
        st.write(f"Régimen: {r['regime']}")

    with col2:
        st.markdown("**🛑 Gestión de Riesgo**")
        st.write(f"SL: ${r['sl_price']:.4f} ({r['sl_price']/r['entry_price']-1:.2%})")
        st.write(f"TP: ${r['tp_price']:.4f} ({r['tp_price']/r['entry_price']-1:.2%})")
        st.write(f"Break Even Trigger: {r['break_even_trigger']:.2%}")
        st.write(f"Tiempo máx: {r['max_hold_minutes']} min")

    if with_trailing:
        st.markdown("---")
        st.markdown("#### 📊 Trailing Stop")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**✅ Con Activación**")
            activation_price = r['entry_price'] * (1 + r['trailing_activation']) if r['direction'] == 'Long' else r['entry_price'] * (1 - r['trailing_activation'])
            st.write(f"Activación: {r['trailing_activation']:.2%} (${activation_price:.4f})")
            st.write(f"Distancia: {r['trailing_distance']:.2%}")
            st.write(f"SL trailing: ${r['entry_price'] * (1 - r['trailing_distance']):.4f}")
        with col_b:
            st.markdown("**❌ Sin Activación**")
            st.write(f"Activación: N/A")
            st.write(f"Distancia: {r['trailing_distance']:.2%}")
            st.write(f"SL trailing: ${r['entry_price'] * (1 - r['trailing_distance']):.4f}")

# ============================================================
# TAB PRINCIPAL: RANKING
# ============================================================
st.header("🏆 Ranking de Oportunidades (Activos Certificados)")

if refresh_btn or st.session_state.last_refresh is None:
    with st.spinner("🔍 Escaneando el mercado..."):
        all_rankings, valid_signals = scan_and_rank()
        st.session_state.all_rankings = all_rankings
        st.session_state.valid_signals = valid_signals

        for r in all_rankings:
            if r['is_valid']:
                st.session_state.signal_history.append({
                    'timestamp': datetime.now(),
                    'symbol': r['symbol'],
                    'direction': r['direction'],
                    'score': r['score'],
                    'is_valid': True
                })
        if len(st.session_state.signal_history) > 100:
            st.session_state.signal_history = st.session_state.signal_history[-100:]

if 'all_rankings' in st.session_state:
    all_rankings = st.session_state.all_rankings

    if not all_rankings:
        st.warning("No se encontraron señales. Intenta actualizar.")
    else:
        # Separar Long y Short
        longs = [r for r in all_rankings if r['direction'] == 'Long' or (r['direction'] == 'N/A' and r['score'] > 0)]
        shorts = [r for r in all_rankings if r['direction'] == 'Short' or (r['direction'] == 'N/A' and r['score'] < 0)]

        if not longs:
            longs = sorted([r for r in all_rankings if r['score'] > 0], key=lambda x: abs(x['score']), reverse=True)
        if not shorts:
            shorts = sorted([r for r in all_rankings if r['score'] < 0], key=lambda x: abs(x['score']), reverse=True)

        def pad_list(items, target=10):
            result = items[:target]
            while len(result) < target:
                result.append(None)
            return result

        longs_padded = pad_list(longs, 10)
        shorts_padded = pad_list(shorts, 10)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🟢 Top 10 Long")
            data_long = []
            for i, r in enumerate(longs_padded):
                if r is None:
                    data_long.append({'Pos': i+1, 'Activo': 'N/A', 'Score': 'N/A', 'ADX': 'N/A', 'KER': 'N/A', 'Aprobado': 'N/A', 'Motivo': 'No hay suficientes longs'})
                else:
                    data_long.append({
                        'Pos': i+1,
                        'Activo': r['symbol'],
                        'Score': f"{r['score']:.3f}",
                        'ADX': f"{r['adx']:.1f}",
                        'KER': f"{r['ker']:.2f}",
                        'Aprobado': "✅" if r['is_valid'] else "❌",
                        'Motivo': r['reason'] if not r['is_valid'] else "✅ Aprobado"
                    })
            df_long = pd.DataFrame(data_long)
            st.dataframe(df_long, width='stretch', hide_index=True)

        with col2:
            st.subheader("🔴 Top 10 Short")
            data_short = []
            for i, r in enumerate(shorts_padded):
                if r is None:
                    data_short.append({'Pos': i+1, 'Activo': 'N/A', 'Score': 'N/A', 'ADX': 'N/A', 'KER': 'N/A', 'Aprobado': 'N/A', 'Motivo': 'No hay suficientes shorts'})
                else:
                    data_short.append({
                        'Pos': i+1,
                        'Activo': r['symbol'],
                        'Score': f"{r['score']:.3f}",
                        'ADX': f"{r['adx']:.1f}",
                        'KER': f"{r['ker']:.2f}",
                        'Aprobado': "✅" if r['is_valid'] else "❌",
                        'Motivo': r['reason'] if not r['is_valid'] else "✅ Aprobado"
                    })
            df_short = pd.DataFrame(data_short)
            st.dataframe(df_short, width='stretch', hide_index=True)

        st.markdown("---")
        st.subheader("📋 Detalles completos de todas las señales (aprobadas y rechazadas)")

        for r in all_rankings[:20]:
            estado = "✅ APROBADO" if r['is_valid'] else "❌ RECHAZADO"
            with st.expander(f"{estado} — {r['symbol']} (Score: {r['score']:.3f})"):
                display_signal_details(r, with_trailing=True)

        st.markdown("---")
        st.subheader("⏳ Tiempo estimado hasta la próxima señal (Long / Short)")

        long_history = [s for s in st.session_state.signal_history if s['direction'] == 'Long' and s['is_valid']]
        short_history = [s for s in st.session_state.signal_history if s['direction'] == 'Short' and s['is_valid']]

        col1, col2 = st.columns(2)
        with col1:
            est_long = estimate_next_signal(long_history)
            if est_long:
                st.metric("⏱️ Próxima señal LONG",
                          f"{est_long['remaining_minutes']:.0f} min",
                          delta=f"Promedio: {est_long['avg_minutes']:.0f} min")
                st.caption(f"Confianza: {est_long['confidence']:.0%}")
            else:
                st.info("No hay suficientes datos para estimar Long")

        with col2:
            est_short = estimate_next_signal(short_history)
            if est_short:
                st.metric("⏱️ Próxima señal SHORT",
                          f"{est_short['remaining_minutes']:.0f} min",
                          delta=f"Promedio: {est_short['avg_minutes']:.0f} min")
                st.caption(f"Confianza: {est_short['confidence']:.0%}")
            else:
                st.info("No hay suficientes datos para estimar Short")

        valid_signals = [r for r in all_rankings if r['is_valid']]
        if valid_signals:
            best = max(valid_signals, key=lambda x: abs(x['score']))
            st.success(f"🧸 **Mejor señal actual:** {best['symbol']} ({best['direction']}) — Score: {best['score']:.3f}")
            with st.expander("📋 Detalles de la mejor señal", expanded=True):
                display_signal_details(best, with_trailing=True)
        else:
            st.warning("No hay señales aprobadas en este momento.")

else:
    st.info("Presiona 'Actualizar Ranking' para comenzar")

# ============================================================
# BACKTESTING (ejecución rápida)
# ============================================================
if run_backtest_btn:
    st.header("🧪 Backtesting Rápido")
    with st.spinner("Ejecutando backtesting..."):
        from backtester import Backtester
        de = st.session_state.data_engine
        symbols = st.session_state.certified_symbols[:10]
        data_dict = {}
        for sym in symbols:
            df = de.fetch_historical(sym, days=90)
            if df is not None and not df.empty:
                data_dict[sym] = df
        if data_dict:
            bt = Backtester(data_dict, {'__global__': DEFAULT_PARAMS}, INITIAL_CAPITAL)
            _, trades, equity = bt.run()
            metrics = bt.calculate_metrics()
            st.json(metrics)
            if not equity.empty:
                fig = px.line(equity, x='timestamp', y='equity', title="Curva de Capital (Backtest)")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos para backtest")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(f"🧸 {PROJECT_NAME} — v{VERSION} 🧸🐻🎉")
st.caption("💜 Apoya el proyecto: Alias `walywasaby` (Prex) | USDT TRC20: `TCiRVXggAqDx6bhJH5KBdf8E4NcJ2voMf8`")
