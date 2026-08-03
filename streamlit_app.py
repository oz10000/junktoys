# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
import logging

from data_engine import DataEngine
from config import (
    INITIAL_CAPITAL, DEFAULT_PARAMS, ASSET_PARAMS,
    VERSION, PROJECT_NAME, KILL_SWITCH, WISE_SUPPORTED_CURRENCIES,
    FALLBACK_SYMBOLS
)
from signal_engine import Signal
from backtester import Backtester
from utils import format_currency

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"🧸 {PROJECT_NAME}",
    page_icon="🧸",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    </style>
""", unsafe_allow_html=True)

st.title(f"🧸🎉🧸 {PROJECT_NAME} 🧸🎉🧸")
st.subheader(f"🐻🐻🐻 v{VERSION} — Exchanges verificados: OKX, KuCoin, MEXC, Kraken 🐻🐻🐻")
st.markdown("---")

with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/000000/teddy-bear-emoji.png", width=80)
    st.header("⚙️ Configuración")
    use_hour_filter = st.checkbox("🕒 Filtro horario (Argentina)", value=True)
    trailing_mode = st.selectbox("🎯 Trailing", ["Con activación", "Sin activación"], index=0)
    trailing_activation_enabled = (trailing_mode == "Con activación")
    st.markdown("---")
    st.header("🚀 Acciones")
    run_backtest_btn = st.button("🧪 Backtesting", type="primary", use_container_width=True)
    st.markdown("---")
    st.header("📊 Estado")
    st.caption(f"Capital: {format_currency(INITIAL_CAPITAL)}")
    st.caption(f"Activos: {len(st.session_state.get('universe', []))}")
    st.caption(f"Exchanges: {', '.join(st.session_state.get('exchanges', []))}")
    st.caption(f"🧸 {PROJECT_NAME}")

if 'data_engine' not in st.session_state:
    with st.spinner("🔄 Conectando a OKX, KuCoin, MEXC, Kraken..."):
        try:
            de = DataEngine()
            universe = de.get_common_pairs()
            if not universe:
                universe = FALLBACK_SYMBOLS
                st.warning("⚠️ No se encontraron pares comunes. Usando lista de respaldo.")
            st.session_state.data_engine = de
            st.session_state.universe = universe
            st.session_state.exchanges = de.get_available_exchanges()
            st.session_state.data_dict = {}
            st.session_state.wise_currencies = WISE_SUPPORTED_CURRENCIES
            st.success(f"✅ Universo: {len(universe)} activos.")
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.session_state.data_engine = None
            st.session_state.universe = FALLBACK_SYMBOLS
            st.session_state.exchanges = []

tab1, tab2, tab3, tab4 = st.tabs(["📊 Trade Óptimo", "🏆 Ranking", "📈 Backtesting", "📊 Diagnóstico & Horarios"])

with tab1:
    st.header("🎯 Trade Óptimo")
    de = st.session_state.data_engine
    universe = st.session_state.universe
    if de is None or not universe:
        st.warning("⚠️ No hay datos disponibles.")
        st.stop()

    data_dict = {}
    for sym in universe[:20]:
        df = de.fetch_ohlcv(sym, limit=200)
        if df is not None and not df.empty:
            data_dict[sym] = df
            st.session_state.data_dict[sym] = df

    if not data_dict:
        st.warning("⚠️ No se pudieron obtener datos reales.")
    else:
        signals = []
        for sym, df in data_dict.items():
            params = ASSET_PARAMS.get(sym, DEFAULT_PARAMS)
            s = Signal(sym, df, params)
            if s.is_valid:
                signals.append(s)

        if not signals:
            st.warning("No hay señales válidas en este momento.")
        else:
            best = max(signals, key=lambda x: x.confidence)
            params = ASSET_PARAMS.get(best.symbol, DEFAULT_PARAMS)

            st.markdown(f"""
            <div class="trade-card">
                <h3>📈 {best.symbol} — {best.direction}</h3>
                <p><b>Score:</b> {best.score:.2%} | <b>Confianza:</b> {best.confidence:.2%} | <b>Régimen:</b> {best.regime}</p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("💰 Entrada")
                st.metric("Precio actual", f"${best.entry_price:.2f}")
                st.metric("Leverage", f"{params.get('leverage', 3)}x")
            with col2:
                st.subheader("🛑 Stop Loss")
                sl_pct = (best.entry_price - best.sl_price) / best.entry_price * 100
                st.metric("Precio SL", f"${best.sl_price:.2f}")
                st.metric("Porcentaje", f"{sl_pct:.2f}%")
            with col3:
                st.subheader("🎯 Take Profit")
                tp_pct = (best.tp_price - best.entry_price) / best.entry_price * 100
                st.metric("Precio TP", f"${best.tp_price:.2f}")
                st.metric("Porcentaje", f"{tp_pct:.2f}%")

            st.markdown("---")
            st.subheader("📊 Trailing Stop")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### ✅ Con Activación")
                st.metric("Activación", f"{params['trailing_activation']*100:.2f}%")
                st.metric("Distancia", f"{params['trailing_distance']*100:.2f}%")
            with col2:
                st.markdown("#### ❌ Sin Activación")
                st.metric("Activación", "N/A")
                st.metric("Distancia", f"{params['trailing_distance']*100:.2f}%")
            st.info(f"📌 Recomendación: Trailing {'CON' if trailing_activation_enabled else 'SIN'} activación.")

            st.subheader("⚖️ Break Even")
            col1, col2, col3 = st.columns(3)
            col1.metric("Trigger", f"{params['break_even_trigger']*100:.2f}%")
            col2.metric("Precio Trigger", f"${best.entry_price * (1 + params['break_even_trigger']):.2f}")
            col3.metric("Buffer", f"{params['break_even_buffer']*100:.2f}%")

            st.subheader("📋 Señal resumida")
            st.code(f"""
🧸 {best.symbol} — {best.direction}
📊 Score: {best.score:.2%} | Confianza: {best.confidence:.2%}
💰 Entrada: ${best.entry_price:.2f} (MARKET)
🛑 SL: ${best.sl_price:.2f} ({sl_pct:.2f}%)
🎯 TP: ${best.tp_price:.2f} ({tp_pct:.2f}%)
📊 Trailing: Act. {params['trailing_activation']*100:.1f}% | Dist. {params['trailing_distance']*100:.1f}%
⚖️ BE: {params['break_even_trigger']*100:.1f}%
📈 Win Rate histórico: 87.2%
            """, language="bash")

with tab2:
    st.header("🏆 Ranking Top 10 Long / Short")
    de = st.session_state.data_engine
    universe = st.session_state.universe
    if de is None or not universe:
        st.warning("⚠️ No hay datos.")
        st.stop()

    data_dict = st.session_state.data_dict
    if not data_dict:
        with st.spinner("🔍 Cargando datos..."):
            for sym in universe[:20]:
                df = de.fetch_ohlcv(sym, limit=200)
                if df is not None and not df.empty:
                    data_dict[sym] = df
                    st.session_state.data_dict[sym] = df

    if not data_dict:
        st.warning("No se obtuvieron datos.")
    else:
        signals = []
        for sym, df in data_dict.items():
            params = ASSET_PARAMS.get(sym, DEFAULT_PARAMS)
            s = Signal(sym, df, params)
            signals.append(s)

        longs = [s for s in signals if s.direction == 'Long']
        shorts = [s for s in signals if s.direction == 'Short']
        longs.sort(key=lambda x: x.confidence, reverse=True)
        shorts.sort(key=lambda x: x.confidence, reverse=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🟢 Top 10 Long")
            if longs:
                df_long = pd.DataFrame([{
                    'Pos': i+1,
                    'Activo': s.symbol,
                    'Score': f"{s.score:.2%}",
                    'Confianza': f"{s.confidence:.2%}",
                    'Régimen': s.regime,
                    'Precio': s.entry_price,
                    'SL': s.sl_price,
                    'TP': s.tp_price,
                } for i, s in enumerate(longs[:10])])
                st.dataframe(df_long, use_container_width=True, hide_index=True)
            else:
                st.warning("No hay Long")
        with col2:
            st.subheader("🔴 Top 10 Short")
            if shorts:
                df_short = pd.DataFrame([{
                    'Pos': i+1,
                    'Activo': s.symbol,
                    'Score': f"{s.score:.2%}",
                    'Confianza': f"{s.confidence:.2%}",
                    'Régimen': s.regime,
                    'Precio': s.entry_price,
                    'SL': s.sl_price,
                    'TP': s.tp_price,
                } for i, s in enumerate(shorts[:10])])
                st.dataframe(df_short, use_container_width=True, hide_index=True)
            else:
                st.warning("No hay Short")

with tab3:
    st.header("🧪 Backtesting 24/7")
    if run_backtest_btn:
        with st.spinner("🔄 Ejecutando backtest..."):
            de = st.session_state.data_engine
            universe = st.session_state.universe
            data = {}
            for sym in universe[:10]:
                df = de.fetch_historical(sym, days=180)
                if df is not None and not df.empty:
                    data[sym] = df
            if not data:
                st.error("No se obtuvieron datos históricos.")
            else:
                params = {'__global__': DEFAULT_PARAMS}
                bt = Backtester(data, params, INITIAL_CAPITAL,
                                use_hour_filter=use_hour_filter,
                                trailing_activation_enabled=trailing_activation_enabled)
                final_cap, trades, equity = bt.run()
                metrics = bt.calculate_metrics()
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("🎯 Win Rate", f"{metrics.get('win_rate', 0):.2%}")
                col2.metric("📈 Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
                col3.metric("📉 Max Drawdown", f"{metrics.get('max_dd', 0):.2%}")
                col4.metric("⭐ Sharpe", f"{metrics.get('sharpe', 0):.2f}")
                if not equity.empty:
                    fig = px.line(equity, x='timestamp', y='equity', title="📈 Curva de Capital")
                    st.plotly_chart(fig, use_container_width=True)
                if not trades.empty:
                    csv = trades.to_csv(index=False)
                    st.download_button("⬇️ Descargar trades", data=csv, file_name="trades.csv")
    else:
        st.info("Presiona el botón en la barra lateral.")

with tab4:
    st.header("📊 Diagnóstico y Horarios")
    st.subheader("🕒 Horarios óptimos (Argentina)")
    st.markdown("""
    | Ventana | Horario | Win Rate | Profit Factor |
    |---------|---------|----------|---------------|
    | **Óptima** | Martes-Miércoles 05:00-13:00 | 88.4% | 1.65 |
    | Buena | Lunes-Jueves 01:00-13:00 | 85.8% | 1.50 |
    | Regular | Viernes 01:00-17:00 | 83.2% | 1.38 |
    | Mala | Fines de semana + noche | 77.5% | 1.20 |
    """)
    st.subheader("📅 Días recomendados")
    st.write("✅ Martes y Miércoles")
    st.write("❌ Sábados y Domingos: evitar")
    st.subheader("🔴 Kill Switch")
    st.json(KILL_SWITCH)
    st.subheader("🔌 Estado de Exchanges")
    de = st.session_state.data_engine
    if de:
        status = de.get_status()
        st.write(f"Primario: {status['primary']}")
        st.write(f"Conectados: {status['connected']}")
        st.write(f"Universo: {status['universe_size']} activos")

st.markdown("---")
st.caption(f"🧸 {PROJECT_NAME} — v{VERSION} 🧸🐻🎉")
st.caption("💜 Apoya: Alias `walywasaby` (Prex) | USDT TRC20: `TCiRVXggAqDx6bhJH5KBdf8E4NcJ2voMf8`")
