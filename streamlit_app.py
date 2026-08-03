# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import time
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# IMPORTS DEL SISTEMA (modificados para usar el nuevo motor)
# ============================================================
from data_engine import DataEngine
from config import (
    INITIAL_CAPITAL, DEFAULT_PARAMS, VERSION, PROJECT_NAME,
    EXCHANGE_PRIORITY, UNIVERSE, UNIVERSE_BY_EXCHANGE
)
from signal_engine import Signal
from backtester import Backtester
from utils import format_currency

# Importar módulos opcionales (si existen)
try:
    from trade_summary import TradeSummary
    from market_diagnosis import MarketDiagnosis
    from btc_eth_sol_analysis import BTC_ETH_SOL_Analyzer
    from wise_integration import WiseIntegration
except ImportError as e:
    logger.warning(f"Módulo opcional no encontrado: {e}")
    TradeSummary = None
    MarketDiagnosis = None
    BTC_ETH_SOL_Analyzer = None
    WiseIntegration = None

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title=f"🧸 {PROJECT_NAME}",
    page_icon="🧸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# ESTILOS
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
        .metric-good { color: green; font-weight: bold; }
        .metric-bad { color: red; font-weight: bold; }
        .metric-neutral { color: orange; font-weight: bold; }
        .zone-a { border-left-color: #4CAF50; }
        .zone-b { border-left-color: #FF9800; }
        .zone-c { border-left-color: #F44336; }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# TÍTULO
# ============================================================
st.title(f"🧸🎉🧸 {PROJECT_NAME} 🧸🎉🧸")
st.subheader(f"🐻🐻🐻 v{VERSION} — Motor Multi-Exchange (OKX, KuCoin, MEXC, Kraken) 🐻🐻🐻")
st.markdown("---")

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/000000/teddy-bear-emoji.png", width=80)
    st.header("⚙️ Configuración")
    use_hour_filter = st.checkbox("🕒 Filtro horario (Argentina)", value=True)
    trailing_mode = st.selectbox("🎯 Trailing recomendado", ["Con activación", "Sin activación"], index=0)
    trailing_activation_enabled = (trailing_mode == "Con activación")
    st.markdown("---")
    st.header("🚀 Acciones")
    run_backtest_btn = st.button("🧪 Backtesting", type="primary", use_container_width=True)
    st.markdown("---")
    st.header("📊 Estado")
    st.caption(f"Capital: {format_currency(INITIAL_CAPITAL)}")
    st.caption(f"Activos: {len(st.session_state.get('symbols', []))}")
    st.caption(f"Exchanges: {', '.join(st.session_state.get('exchanges', []))}")
    st.caption(f"🧸 {PROJECT_NAME} v{VERSION}")

# ============================================================
# INICIALIZACIÓN DE SESIÓN CON EL NUEVO DATAENGINE
# ============================================================
if 'data_engine' not in st.session_state:
    with st.spinner("🔄 Inicializando DataEngine multi-exchange..."):
        try:
            de = DataEngine()
            symbols = de.get_common_pairs(max_pairs=50)
            if not symbols:
                st.warning("⚠️ No se pudo obtener el universo de ningún exchange. Verifica la conexión.")
                symbols = []
            st.session_state.data_engine = de
            st.session_state.symbols = symbols
            st.session_state.exchanges = de.get_available_exchanges()
            st.session_state.data_dict = {}
            st.session_state.ranking_history = []
            st.session_state.optimization_results = None
            # Wise solo si está disponible
            if WiseIntegration is not None:
                st.session_state.wise = WiseIntegration()
            else:
                st.session_state.wise = None
            st.success(f"✅ DataEngine listo. {len(symbols)} activos cargados desde {', '.join(st.session_state.exchanges)}")
        except Exception as e:
            st.error(f"❌ Error inicializando DataEngine: {e}")
            st.session_state.data_engine = None
            st.session_state.symbols = []
            st.session_state.exchanges = []
            st.session_state.data_dict = {}

# ============================================================
# PESTAÑAS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Trade Óptimo",
    "🏆 Ranking Completo",
    "📈 Backtesting",
    "📊 Diagnóstico & Exchanges"
])

# ============================================================
# TAB 1: TRADE ÓPTIMO
# ============================================================
with tab1:
    st.header("🎯 Trade Óptimo — Listo para Ejecutar")

    if not st.session_state.symbols:
        st.warning("⚠️ No hay símbolos disponibles. Verifica la conexión a los exchanges.")
        st.stop()

    with st.spinner("🔍 Buscando la mejor oportunidad..."):
        try:
            de = st.session_state.data_engine
            symbols = st.session_state.symbols[:30]
            data_dict = {}

            # Descargar datos reales para cada símbolo (sin sintéticos)
            for sym in symbols:
                df = de.fetch_ohlcv(sym, limit=200)
                if df is not None and not df.empty:
                    data_dict[sym] = df
                    st.session_state.data_dict[sym] = df
                # Si falla, no se genera nada (se omite)

            if not data_dict:
                st.warning("⚠️ No se pudieron obtener datos reales de ningún activo. Verifica la conexión.")
                st.stop()

            # Generar señales
            signals = []
            for sym, df in data_dict.items():
                if df is not None and not df.empty:
                    s = Signal(sym, df, DEFAULT_PARAMS)
                    if s.is_valid:
                        signals.append(s)

            if not signals:
                st.warning("No hay señales válidas en este momento.")
            else:
                # Ranking simple por score (ordenar)
                ranking = sorted(signals, key=lambda x: x.confidence if x.is_valid else 0, reverse=True)
                best = ranking[0]

                # Mostrar tarjeta del trade
                st.markdown(f"""
                <div class="trade-card">
                    <h3>📈 {best.symbol} — {best.direction}</h3>
                    <p><b>Score:</b> {best.score:.2%} | 
                       <b>Confianza:</b> {best.confidence:.2%} | 
                       <b>Régimen:</b> {best.regime}</p>
                </div>
                """, unsafe_allow_html=True)

                # Columnas principales
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.subheader("📊 Entrada")
                    st.metric("Precio actual", f"${best.entry_price:.2f}")
                    st.metric("Leverage sugerido", "3x")
                    st.metric("Posición sugerida", f"{INITIAL_CAPITAL * 3 / best.entry_price:.4f}")

                with col2:
                    st.subheader("🛑 Stop Loss")
                    st.metric("Precio SL", f"${best.sl_price:.2f}")
                    sl_pct = (best.entry_price - best.sl_price) / best.entry_price * 100
                    st.metric("Porcentaje", f"{sl_pct:.2f}%")

                with col3:
                    st.subheader("🎯 Take Profit")
                    st.metric("Precio TP", f"${best.tp_price:.2f}")
                    tp_pct = (best.tp_price - best.entry_price) / best.entry_price * 100
                    st.metric("Porcentaje", f"{tp_pct:.2f}%")

                # Trailing Stop comparativa
                st.markdown("---")
                st.subheader("📊 Comparativa de Trailing Stop")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### ✅ Con Activación")
                    st.metric("Activación", f"{DEFAULT_PARAMS['trailing_activation']*100:.2f}%")
                    st.metric("Distancia", f"{DEFAULT_PARAMS['trailing_distance']*100:.2f}%")
                    st.metric("Precio SL aprox", f"${best.entry_price * (1 - DEFAULT_PARAMS['trailing_distance']):.2f}")

                with col2:
                    st.markdown("#### ❌ Sin Activación")
                    st.metric("Activación", "N/A")
                    st.metric("Distancia", f"{DEFAULT_PARAMS['trailing_distance']*100:.2f}%")
                    st.metric("Precio SL aprox", f"${best.entry_price * (1 - DEFAULT_PARAMS['trailing_distance']):.2f}")

                st.info(f"📌 **Recomendación:** Usar Trailing {'CON' if trailing_activation_enabled else 'SIN'} activación según la configuración actual.")

                # Break Even
                st.subheader("⚖️ Break Even")
                col1, col2, col3 = st.columns(3)
                col1.metric("Trigger", f"{DEFAULT_PARAMS['break_even_trigger']*100:.2f}%")
                col2.metric("Precio Trigger", f"${best.entry_price * (1 + DEFAULT_PARAMS['break_even_trigger']):.2f}")
                col3.metric("Buffer", f"{DEFAULT_PARAMS['break_even_buffer']*100:.2f}%")

                # Detalles completos
                with st.expander("📋 Todos los parámetros del trade"):
                    st.json({
                        "Activo": best.symbol,
                        "Dirección": best.direction,
                        "Score": best.score,
                        "Confianza": best.confidence,
                        "Régimen": best.regime,
                        "Precio entrada": best.entry_price,
                        "SL": best.sl_price,
                        "TP": best.tp_price,
                        "Trailing activación": DEFAULT_PARAMS['trailing_activation'],
                        "Trailing distancia": DEFAULT_PARAMS['trailing_distance'],
                        "BE trigger": DEFAULT_PARAMS['break_even_trigger'],
                        "BE buffer": DEFAULT_PARAMS['break_even_buffer'],
                        "Tiempo máximo (min)": DEFAULT_PARAMS['max_hold_minutes'],
                    })

        except Exception as e:
            st.error(f"Error al buscar trade: {e}")
            logger.error(f"Error en Tab1: {e}")

    # Estado del mercado (diagnóstico básico)
    st.markdown("---")
    st.subheader("⏳ Estado del Mercado")
    if st.session_state.data_dict:
        # Calcular ADX promedio simple
        adx_values = []
        for sym, df in st.session_state.data_dict.items():
            if df is not None and not df.empty:
                from core_engine import compute_adx
                adx_series = compute_adx(df)
                if not adx_series.empty:
                    adx_values.append(adx_series.iloc[-1])
        if adx_values:
            avg_adx = np.mean(adx_values)
            st.metric("ADX promedio", f"{avg_adx:.1f}")
            if avg_adx > 25:
                st.success("Tendencia general: Fuerte")
            elif avg_adx > 20:
                st.info("Tendencia general: Moderada")
            else:
                st.warning("Tendencia general: Débil / Lateral")
        else:
            st.info("No hay suficientes datos para diagnóstico.")

# ============================================================
# TAB 2: RANKING COMPLETO
# ============================================================
with tab2:
    st.header("🏆 Ranking Completo — Top 10 Long / Short")

    if not st.session_state.symbols:
        st.warning("⚠️ No hay símbolos disponibles.")
        st.stop()

    with st.spinner("🔍 Generando ranking..."):
        try:
            de = st.session_state.data_engine
            symbols = st.session_state.symbols[:30]
            data_dict = {}

            for sym in symbols:
                df = de.fetch_ohlcv(sym, limit=200)
                if df is not None and not df.empty:
                    data_dict[sym] = df

            if not data_dict:
                st.warning("No se pudieron obtener datos para el ranking.")
                st.stop()

            signals = []
            for sym, df in data_dict.items():
                s = Signal(sym, df, DEFAULT_PARAMS)
                if s.is_valid:
                    signals.append(s)

            if not signals:
                st.warning("No hay señales válidas.")
            else:
                # Separar Long y Short
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
                        st.dataframe(df_long, width='stretch', hide_index=True)
                    else:
                        st.warning("No hay señales Long")

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
                        st.dataframe(df_short, width='stretch', hide_index=True)
                    else:
                        st.warning("No hay señales Short")

                # Detalles expandibles
                with st.expander("📋 Detalles de todas las señales"):
                    for s in signals[:20]:
                        st.write(f"**{s.symbol}** ({s.direction}) — Score: {s.score:.2%}, Confianza: {s.confidence:.2%}")
                        st.json({
                            "Score": s.score,
                            "Confianza": s.confidence,
                            "ADX": s.adx,
                            "KER": s.ker,
                            "Régimen": s.regime,
                            "Precio": s.entry_price,
                            "SL": s.sl_price,
                            "TP": s.tp_price,
                            "Trailing activación": s.trailing_activation,
                            "Trailing distancia": s.trailing_distance,
                            "BE trigger": s.break_even_trigger,
                            "BE buffer": s.break_even_buffer,
                            "Tiempo máximo": s.max_hold_minutes,
                        })

        except Exception as e:
            st.error(f"Error en ranking: {e}")
            logger.error(f"Error en Tab2: {e}")

# ============================================================
# TAB 3: BACKTESTING
# ============================================================
with tab3:
    st.header("🧪 Backtesting 24/7")

    if run_backtest_btn:
        with st.spinner("🔄 Ejecutando backtesting con datos reales..."):
            try:
                de = st.session_state.data_engine
                symbols = st.session_state.symbols[:15]
                data_dict = {}

                for sym in symbols:
                    df = de.fetch_historical(sym, days=180)
                    if df is not None and not df.empty:
                        data_dict[sym] = df

                if not data_dict:
                    st.error("No se pudieron obtener datos históricos para el backtesting.")
                else:
                    params = {'__global__': DEFAULT_PARAMS}
                    bt = Backtester(
                        data_dict,
                        params,
                        initial_capital=INITIAL_CAPITAL,
                        use_hour_filter=use_hour_filter,
                        trailing_activation_enabled=trailing_activation_enabled
                    )
                    final_cap, trades, equity = bt.run()
                    metrics = bt.calculate_metrics()

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("🎯 Win Rate", f"{metrics.get('win_rate', 0):.2%}")
                    col2.metric("📈 Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
                    col3.metric("📉 Max Drawdown", f"{metrics.get('max_dd', 0):.2%}")
                    col4.metric("⭐ Sharpe", f"{metrics.get('sharpe', 0):.2f}")

                    col5, col6, col7, col8 = st.columns(4)
                    col5.metric("💰 Capital Final", format_currency(metrics.get('final_capital', 0)))
                    col6.metric("📊 N° Trades", metrics.get('n_trades', 0))
                    col7.metric("🟢 Win Rate", f"{metrics.get('win_rate', 0):.2%}")
                    col8.metric("⏱️ PnL/hora", format_currency(metrics.get('hourly_profit_pct', 0) * INITIAL_CAPITAL / 100))

                    if not equity.empty:
                        fig = px.line(equity, x='timestamp', y='equity', title="📈 Curva de Capital")
                        st.plotly_chart(fig, use_container_width=True)

                    if not trades.empty:
                        fig2 = px.histogram(trades, x='return_pct', nbins=30, title="📊 Distribución de Retornos")
                        st.plotly_chart(fig2, use_container_width=True)

                        st.subheader("📋 Últimos Trades")
                        st.dataframe(trades.tail(10), width='stretch')

                        csv = trades.to_csv(index=False)
                        st.download_button("⬇️ Descargar trades (CSV)", data=csv, file_name="backtest_trades.csv")

            except Exception as e:
                st.error(f"Error en backtesting: {e}")
                logger.error(f"Error en Tab3: {e}")
    else:
        st.info("Presiona el botón en la barra lateral para ejecutar el backtesting.")

# ============================================================
# TAB 4: DIAGNÓSTICO & EXCHANGES
# ============================================================
with tab4:
    st.header("📊 Diagnóstico del Mercado y Estado de Exchanges")

    # Estado de exchanges
    st.subheader("🔌 Exchanges Conectados")
    de = st.session_state.data_engine
    if de:
        available = de.get_available_exchanges()
        for ex in available:
            st.write(f"✅ {ex}")
        status = de.get_status()
        st.caption(f"Universo: {status.get('universe_size', 0)} activos")
        st.caption(f"Primary: {status.get('primary', 'N/A')}")
    else:
        st.warning("DataEngine no disponible")

    # Diagnóstico simple de mercado
    st.subheader("📈 Diagnóstico Rápido")
    if st.session_state.data_dict:
        # Calcular ADX y régimen promedio
        regimes = []
        adx_values = []
        for sym, df in st.session_state.data_dict.items():
            if df is not None and not df.empty:
                from core_engine import compute_adx, compute_regime
                adx_series = compute_adx(df)
                if not adx_series.empty:
                    adx_values.append(adx_series.iloc[-1])
                regimes.append(compute_regime(df))
        if adx_values:
            avg_adx = np.mean(adx_values)
            st.metric("ADX promedio", f"{avg_adx:.1f}")
            # Régimen más común
            from collections import Counter
            regime_counts = Counter(regimes)
            if regime_counts:
                most_common = regime_counts.most_common(1)[0][0]
                st.metric("Régimen predominante", most_common)
        else:
            st.info("No hay suficientes datos para diagnóstico.")
    else:
        st.info("No hay datos cargados. Ejecuta el escaneo de señales primero.")

    # Wise Integration (si está disponible)
    if WiseIntegration is not None and st.session_state.get('wise'):
        st.markdown("---")
        st.subheader("💱 Wise Integration")
        wise = st.session_state.wise
        df_wise = wise.get_wise_table()
        st.dataframe(df_wise, width='stretch')
    else:
        st.caption("Wise Integration no disponible (módulo opcional).")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(f"🧸 {PROJECT_NAME} — v{VERSION} 🧸🐻🎉")
st.caption("💜 Apoya el proyecto: Alias `walywasaby` (Prex) | USDT TRC20: `TCiRVXggAqDx6bhJH5KBdf8E4NcJ2voMf8`")
