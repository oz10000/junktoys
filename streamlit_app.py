# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import logging
import sys
import os

# ============================================================
# IMPORTS DEL SISTEMA PRINCIPAL
# ============================================================
from data_engine import DataEngine
from config import (
    INITIAL_CAPITAL, DEFAULT_PARAMS, VERSION, PROJECT_NAME,
    TIMEFRAME, KILL_SWITCH, ENTRY_ZONES, FALLBACK_SYMBOLS
)
from signal_engine import Signal
from core_engine import compute_atr, compute_adx, compute_ker
from utils import format_currency
from backtester import Backtester

# ============================================================
# IMPORTS DE FIRM SIGNALS Ω (con fallback seguro)
# ============================================================
FIRM_SIGNALS_AVAILABLE = False
try:
    from firm_signals_omega.streamlit_app import render_firm_signals_panel
    FIRM_SIGNALS_AVAILABLE = True
except ImportError:
    # Si no está disponible, definimos una función placeholder
    def render_firm_signals_panel():
        st.warning("⚠️ El módulo Firm Signals Ω no está instalado. Consulta la documentación para su instalación.")
        st.info("Para instalar: copia la carpeta 'firm_signals_omega' en la raíz del proyecto.")

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================
st.set_page_config(
    page_title="🧸 Junk Toys — Sistema de Señales",
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
# SIDEBAR (configuración y botones)
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/000000/teddy-bear-emoji.png", width=80)
    st.header("⚙️ Configuración")
    use_hour_filter = st.checkbox("🕒 Filtro horario (Argentina)", value=True)
    trailing_mode = st.selectbox("🎯 Trailing", ["Con activación", "Sin activación"], index=0)
    trailing_activation_enabled = (trailing_mode == "Con activación")
    st.markdown("---")
    st.header("🚀 Acciones")
    
    # Botón de backtesting (sistema principal)
    run_backtest_btn = st.button("🧪 Backtesting", type="secondary", use_container_width=True)
    # Botón de optimización (sistema principal)
    run_optimization_btn = st.button("🧠 Optimización", type="secondary", use_container_width=True)
    # Botón para abrir Firm Signals Ω (nuevo)
    if FIRM_SIGNALS_AVAILABLE:
        st.markdown("---")
        st.header("🧸 Firm Signals Ω")
        if st.button("🚀 Ejecutar Análisis", type="primary", use_container_width=True):
            st.session_state.show_firm_signals = True
    else:
        st.markdown("---")
        st.info("⚡ Firm Signals Ω no disponible")
    
    st.markdown("---")
    st.header("📊 Estado")
    st.caption(f"Capital: {format_currency(INITIAL_CAPITAL)}")
    st.caption(f"Timeframe: {TIMEFRAME}")
    st.caption(f"Activos certificados: {len(st.session_state.get('certified_symbols', FALLBACK_SYMBOLS[:10]))}")
    st.caption(f"🧸 Junk Toys v{VERSION}")

# ============================================================
# INICIALIZACIÓN DE SESIÓN (sistema principal)
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
# FUNCIONES DEL SISTEMA PRINCIPAL
# ============================================================
def scan_and_rank():
    de = st.session_state.data_engine
    symbols = st.session_state.certified_symbols
    data_dict = {}

    for sym in symbols[:30]:
        df = de.fetch_ohlcv(sym, limit=300)
        if df is not None and not df.empty:
            data_dict[sym] = df
        else:
            for alt_ex in ['kucoin', 'mexc', 'kraken']:
                df = de.fetch_ohlcv(sym, limit=300, exchange_id=alt_ex)
                if df is not None and not df.empty:
                    data_dict[sym] = df
                    break

    if not data_dict:
        for sym in symbols[:10]:
            df = de.fetch_ohlcv(sym, limit=100)
            if df is not None and not df.empty:
                data_dict[sym] = df

    st.session_state.data_dict = data_dict
    st.session_state.last_refresh = datetime.now()

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
# PESTAÑAS PRINCIPALES (incluyendo Firm Signals Ω)
# ============================================================
tab_names = [
    "📊 Trade Óptimo",
    "🏆 Ranking Completo",
    "📈 Backtesting",
    "📊 BTC/ETH/SOL",
    "🧠 Optimización",
    "📈 Diagnóstico",
    "🏦 Exchanges & Wise",
    "🧸 Firm Signals Ω"
]

tabs = st.tabs(tab_names)

# ============================================================
# TAB 1: Trade Óptimo (copiado del sistema original)
# ============================================================
with tabs[0]:
    st.header("🎯 Trade Óptimo — Listo para Ejecutar")
    with st.spinner("🔍 Buscando la mejor oportunidad..."):
        try:
            de = st.session_state.data_engine
            symbols = st.session_state.symbols[:50]
            data_dict = {}
            for sym in symbols[:30]:
                df = de.fetch_ohlcv(sym, limit=300)
                if df is not None and not df.empty:
                    data_dict[sym] = df
                    if sym not in st.session_state.data_dict:
                        st.session_state.data_dict[sym] = df
            if data_dict:
                signals = []
                for sym, df in data_dict.items():
                    s = Signal(sym, df, DEFAULT_PARAMS)
                    if s.is_valid:
                        signals.append(s)
                if signals:
                    from ranking_engine import RankingEngine
                    ranking_engine = RankingEngine(de)
                    ranking = ranking_engine.rank_symbols(signals, data_dict)
                    if ranking:
                        best = ranking[0]
                        signal = best['signal']
                        metrics = ranking_engine.get_historical_metrics(best['symbol'])
                        market_data = {'spread': 0.001, 'volume': best['amplitudes'].get('avg_volume', 0)}
                        sr_data = best.get('sr_strength', 0)
                        amplitudes = best['amplitudes']
                        from trade_summary import TradeSummary
                        trade = TradeSummary(signal, metrics, market_data, sr_data, amplitudes, DEFAULT_PARAMS)
                        trade_dict = trade.to_dict()
                        st.markdown(f"""
                        <div class="trade-card">
                            <h3>📈 {trade_dict['symbol']} — {trade_dict['direction']}</h3>
                            <p><b>Score:</b> {trade_dict['score']:.2%} | 
                               <b>Confianza:</b> {trade_dict['confidence']:.2%} | 
                               <b>Probabilidad:</b> {trade_dict['probability']:.2%}</p>
                            <p><b>Edge:</b> {trade_dict['edge_type']} ({trade_dict['edge']:.3f})</p>
                            <p><b>Régimen:</b> {trade_dict['regime']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.subheader("📊 Entrada")
                            st.metric("Precio", f"${trade_dict['entry_price']:.2f}")
                            st.metric("Tipo", trade_dict['entry_type'])
                            st.metric("Leverage", f"{trade_dict['leverage']}x")
                            st.metric("Position Size", f"{trade_dict['position_size']:.4f}")
                        with col2:
                            st.subheader("🛑 Stop Loss")
                            st.metric("Precio", f"${trade_dict['sl_price']:.2f}")
                            st.metric("Porcentaje", f"{trade_dict['sl_pct']:.2f}%")
                            st.metric("Monto", format_currency(trade_dict['sl_amount']))
                            st.metric("Risk/Reward", f"{trade_dict['risk_reward_ratio']:.2f}")
                        with col3:
                            st.subheader("🎯 Take Profit")
                            st.metric("Precio", f"${trade_dict['tp_price']:.2f}")
                            st.metric("Porcentaje", f"{trade_dict['tp_pct']:.2f}%")
                            st.metric("Monto", format_currency(trade_dict['tp_amount']))
                            st.metric("Retorno esperado", format_currency(trade_dict['expected_return']))
                        st.markdown("---")
                        st.subheader("📊 Comparativa de Trailing Stop")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("#### ✅ Con Activación")
                            st.metric("Activación", f"{trade_dict['trailing_activation_pct']:.2f}%")
                            st.metric("Precio Activación", f"${trade_dict['trailing_activation_price']:.2f}")
                            st.metric("Distancia", f"{trade_dict['trailing_distance_pct']:.2f}%")
                            st.metric("Precio SL", f"${trade_dict['trailing_sl_price']:.2f}")
                            st.metric("Win Rate estimado", f"{trade.probability * 1.05:.1%}")
                        with col2:
                            st.markdown("#### ❌ Sin Activación")
                            st.metric("Activación", "N/A")
                            st.metric("Precio Activación", "N/A")
                            st.metric("Distancia", f"{trade_dict['trailing_no_activation_pct']:.2f}%")
                            st.metric("Precio SL", f"${trade_dict['trailing_no_activation_price']:.2f}")
                            st.metric("Win Rate estimado", f"{trade.probability * 0.95:.1%}")
                        st.info(f"📌 **Recomendación:** Usar Trailing {'CON' if trailing_activation_enabled else 'SIN'} activación según la configuración actual.")
                        st.subheader("⚖️ Break Even")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Trigger", f"{trade_dict['be_trigger_pct']:.2f}%")
                        col2.metric("Precio Trigger", f"${trade_dict['be_trigger_price']:.2f}")
                        col3.metric("Buffer", f"{trade_dict['be_buffer_pct']:.2f}%")
                        st.subheader("⚠️ Riesgo")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Riesgo total", format_currency(trade_dict['risk_amount']))
                        col2.metric("Riesgo %", f"{trade_dict['risk_pct']:.2f}%")
                        col3.metric("Drawdown esperado", format_currency(trade_dict['expected_drawdown']))
                        with st.expander("📋 Todos los parámetros del trade"):
                            df_trade = trade.to_dataframe()
                            st.dataframe(df_trade, width='stretch', hide_index=True)
                        st.subheader("📊 Soportes y Resistencias")
                        if best.get('supports') or best.get('resistances'):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Soportes**")
                                for sup, qual in best.get('supports', [])[:5]:
                                    st.write(f"  ${sup:.2f} (calidad: {qual:.2f})")
                            with col2:
                                st.write("**Resistencias**")
                                for res, qual in best.get('resistances', [])[:5]:
                                    st.write(f"  ${res:.2f} (calidad: {qual:.2f})")
                        st.subheader("📊 Zonas de Entrada")
                        zones = define_zones(trade.amplitudes.get('avg_candle_range', 0.5), trade.entry_price)
                        for zone_name, zone_data in zones.items():
                            color = ENTRY_ZONES.get(zone_name, {}).get('color', '#888')
                            st.markdown(f"""
                            <div class="trade-card zone-{zone_name.lower()}">
                                <b>Zona {zone_name}</b>: ${zone_data['support']:.2f} — ${zone_data['resistance']:.2f}
                                <br><small>{ENTRY_ZONES.get(zone_name, {}).get('desc', '')}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("No hay trades óptimos en este momento")
                else:
                    st.warning("No hay señales válidas en este momento")
            else:
                st.warning("No se pudieron obtener datos")
        except Exception as e:
            st.error(f"Error: {e}")
    st.markdown("---")
    st.subheader("⏳ Estado del Mercado")
    if st.session_state.data_dict:
        from market_diagnosis import MarketDiagnosis
        diagnosis = MarketDiagnosis(st.session_state.data_dict)
        summary = diagnosis.get_summary()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Régimen", summary.get('regime', 'Chop'))
        col2.metric("Tendencia", summary.get('trend', 'Neutral'))
        col3.metric("ADX Promedio", f"{summary.get('avg_adx', 0):.1f}")
        col4.metric("Riesgo", summary.get('risk_level', 'Moderado'))
        from ranking_engine import RankingEngine
        ranking_engine = RankingEngine(de)
        next_opp = ranking_engine.estimate_next_opportunity()
        if next_opp:
            st.info(f"⏳ Próxima oportunidad estimada en {next_opp['remaining_minutes']:.0f} minutos (confianza: {next_opp['confidence']:.0%})")
        else:
            st.info("⏳ No hay suficientes datos para estimar la próxima oportunidad")

# ============================================================
# TAB 2: Ranking Completo (sistema principal)
# ============================================================
with tabs[1]:
    st.header("🏆 Ranking Completo — Top 10 Long / Short")
    with st.spinner("🔍 Escaneando el mercado..."):
        try:
            de = st.session_state.data_engine
            symbols = st.session_state.symbols[:50]
            data_dict = {}
            for sym in symbols[:30]:
                df = de.fetch_ohlcv(sym, limit=300)
                if df is not None and not df.empty:
                    data_dict[sym] = df
            if data_dict:
                signals = []
                for sym, df in data_dict.items():
                    s = Signal(sym, df, DEFAULT_PARAMS)
                    if s.is_valid:
                        signals.append(s)
                if signals:
                    from ranking_engine import RankingEngine
                    ranking_engine = RankingEngine(de)
                    ranking = ranking_engine.rank_symbols(signals, data_dict)
                    if ranking:
                        longs = [r for r in ranking if r['direction'] == 'Long']
                        shorts = [r for r in ranking if r['direction'] == 'Short']
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("🟢 Top 10 Long")
                            if longs:
                                df_long = pd.DataFrame([{
                                    'Pos': i+1,
                                    'Activo': r['symbol'],
                                    'Score': f"{r['score']:.2%}",
                                    'Confianza': f"{r['confidence']:.2%}",
                                    'Edge': r.get('edge_type', 'N/A'),
                                    'Régimen': r['regime'],
                                    'Precio': r['entry_price'],
                                    'SL': r['sl'],
                                    'TP': r['tp'],
                                } for i, r in enumerate(longs[:10])])
                                st.dataframe(df_long, width='stretch', hide_index=True)
                            else:
                                st.warning("No hay señales Long")
                        with col2:
                            st.subheader("🔴 Top 10 Short")
                            if shorts:
                                df_short = pd.DataFrame([{
                                    'Pos': i+1,
                                    'Activo': r['symbol'],
                                    'Score': f"{r['score']:.2%}",
                                    'Confianza': f"{r['confidence']:.2%}",
                                    'Edge': r.get('edge_type', 'N/A'),
                                    'Régimen': r['regime'],
                                    'Precio': r['entry_price'],
                                    'SL': r['sl'],
                                    'TP': r['tp'],
                                } for i, r in enumerate(shorts[:10])])
                                st.dataframe(df_short, width='stretch', hide_index=True)
                            else:
                                st.warning("No hay señales Short")
                        with st.expander("📋 Detalles completos de todas las señales"):
                            for r in ranking[:20]:
                                st.write(f"**{r['symbol']}** — {r['direction']} (Score: {r['score']:.2%})")
                                st.json({
                                    "Score": r['score'],
                                    "Confianza": r['confidence'],
                                    "Edge": r.get('edge_type', 'N/A'),
                                    "Régimen": r['regime'],
                                    "Precio": r['entry_price'],
                                    "SL": r['sl'],
                                    "TP": r['tp'],
                                    "Amplitud": r.get('predicted_amplitude', 0),
                                })
                    else:
                        st.warning("No hay señales válidas")
                else:
                    st.warning("No hay señales válidas")
            else:
                st.warning("No se pudieron obtener datos")
        except Exception as e:
            st.error(f"Error: {e}")

# ============================================================
# TAB 3: Backtesting (sistema principal)
# ============================================================
with tabs[2]:
    st.header("📈 Backtesting Completo")
    if run_backtest_btn:
        with st.spinner("🔄 Ejecutando backtesting..."):
            try:
                de = st.session_state.data_engine
                symbols = st.session_state.symbols[:20]
                data_dict = {}
                for sym in symbols:
                    df = de.fetch_historical(sym, days=180)
                    if df is not None and not df.empty:
                        data_dict[sym] = df
                if not data_dict:
                    st.error("No se pudieron descargar datos")
                else:
                    params = {'__global__': DEFAULT_PARAMS}
                    bt = Backtester(data_dict, params, INITIAL_CAPITAL,
                                   use_hour_filter=use_hour_filter,
                                   trailing_activation_enabled=trailing_activation_enabled)
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
    else:
        st.info("Presiona el botón en la barra lateral para ejecutar el backtesting")

# ============================================================
# TAB 4: BTC/ETH/SOL (sistema principal)
# ============================================================
with tabs[3]:
    st.header("📊 Análisis Independiente: Bitcoin · Ethereum · Solana")
    with st.spinner("🔍 Analizando BTC, ETH y SOL..."):
        try:
            from btc_eth_sol_analysis import BTC_ETH_SOL_Analyzer
            de = st.session_state.data_engine
            analyzer = BTC_ETH_SOL_Analyzer(de)
            summary = analyzer.get_summary()
            col1, col2, col3 = st.columns(3)
            if 'BTC/USDT' in summary['analysis']:
                btc = summary['analysis']['BTC/USDT']
                col1.metric("₿ Bitcoin", f"${btc['price']:,.0f}", delta=f"{btc['change_24h']:.2f}%")
                col1.write(f"ADX: {btc['adx']:.1f} | Régimen: {btc['regime']}")
            if 'ETH/USDT' in summary['analysis']:
                eth = summary['analysis']['ETH/USDT']
                col2.metric("⟠ Ethereum", f"${eth['price']:,.0f}", delta=f"{eth['change_24h']:.2f}%")
                col2.write(f"ADX: {eth['adx']:.1f} | Régimen: {eth['regime']}")
            if 'SOL/USDT' in summary['analysis']:
                sol = summary['analysis']['SOL/USDT']
                col3.metric("◎ Solana", f"${sol['price']:,.0f}", delta=f"{sol['change_24h']:.2f}%")
                col3.write(f"ADX: {sol['adx']:.1f} | Régimen: {sol['regime']}")
            st.markdown("---")
            st.subheader("📊 Fortaleza Relativa")
            strongest = summary.get('strongest')
            weakest = summary.get('weakest')
            if strongest:
                st.success(f"💪 Más fuerte: {strongest}")
            if weakest:
                st.error(f"📉 Más débil: {weakest}")
            st.subheader("📋 Recomendaciones")
            recommendations = summary.get('recommendations', [])
            if recommendations:
                for rec in recommendations:
                    color = "🟢" if rec['action'] == 'LONG' else "🔴" if rec['action'] == 'SHORT' else "⚪"
                    st.write(f"{color} **{rec['symbol']}**: {rec['action']} (confianza: {rec['confidence']:.1%})")
            divergences = summary.get('divergences', [])
            if divergences:
                st.subheader("⚠️ Divergencias Detectadas")
                for div in divergences:
                    emoji = "🔴" if div['type'] == 'bearish' else "🟢"
                    st.write(f"{emoji} {div['symbol1']} vs {div['symbol2']}: {div['type']} (severidad: {div['severity']:.2f})")
        except Exception as e:
            st.error(f"Error: {e}")

# ============================================================
# TAB 5: Optimización (sistema principal)
# ============================================================
with tabs[4]:
    st.header("🧠 Laboratorio de Optimización (100 iteraciones)")
    if run_optimization_btn:
        with st.spinner("🧠 Ejecutando optimización completa (100 iteraciones)..."):
            try:
                from optimizer import OptimizationLab
                de = st.session_state.data_engine
                symbols = st.session_state.symbols[:20]
                data_dict = {}
                for sym in symbols:
                    df = de.fetch_historical(sym, days=180)
                    if df is not None and not df.empty:
                        data_dict[sym] = df
                if not data_dict:
                    st.error("No se pudieron descargar datos")
                else:
                    lab = OptimizationLab(list(data_dict.keys()), data_dict)
                    results = lab.run_full_optimization()
                    st.session_state.optimization_results = results
                    st.success("✅ Optimización completada")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("🏆 Mejor Win Rate", f"{results['best_winrate']:.2%}")
                    col2.metric("📈 Profit Factor", f"{results['best_metrics'].get('profit_factor', 0):.2f}")
                    col3.metric("📉 Drawdown", f"{results['best_metrics'].get('max_dd', 0):.2%}")
                    col4.metric("⭐ Sharpe", f"{results['best_metrics'].get('sharpe', 0):.2f}")
                    st.subheader("📋 Parámetros Óptimos")
                    st.json(results['best_params'])
                    if lab.tracking['winrates']:
                        fig = px.line(x=lab.tracking['iterations'], y=lab.tracking['winrates'],
                                      title="📈 Evolución del Win Rate durante la optimización")
                        fig.update_layout(yaxis_tickformat='.0%')
                        st.plotly_chart(fig, use_container_width=True)
                    if results.get('walk_forward'):
                        st.subheader("📊 Walk-Forward Validation")
                        wf_df = pd.DataFrame(results['walk_forward'])
                        st.dataframe(wf_df, width='stretch')
                    if results.get('monte_carlo'):
                        st.subheader("🎰 Monte Carlo (1000 simulaciones)")
                        mc = results['monte_carlo']
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Capital final medio", format_currency(mc.get('mean_final_capital', 0)))
                        col2.metric("Probabilidad de ruina", f"{mc.get('ruin_prob', 0):.2%}")
                        col3.metric("Drawdown medio", f"{mc.get('mean_max_dd', 0):.2%}")
            except Exception as e:
                st.error(f"Error en optimización: {e}")
    else:
        st.info("Presiona el botón en la barra lateral para ejecutar la optimización completa")

# ============================================================
# TAB 6: Diagnóstico (sistema principal)
# ============================================================
with tabs[5]:
    st.header("📈 Diagnóstico del Mercado")
    if st.session_state.data_dict:
        from market_diagnosis import MarketDiagnosis
        diagnosis = MarketDiagnosis(st.session_state.data_dict)
        summary = diagnosis.get_summary()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Régimen", summary.get('regime', 'Chop'))
        col2.metric("📈 Tendencia", summary.get('trend', 'Neutral'))
        col3.metric("📉 ADX Promedio", f"{summary.get('avg_adx', 0):.1f}")
        col4.metric("⚠️ Riesgo", summary.get('risk_level', 'Moderado'))
        col5, col6, col7 = st.columns(3)
        col5.metric("📊 Volatilidad", f"{summary.get('avg_volatility', 0)*100:.2f}%")
        col6.metric("🔗 Correlación", f"{summary.get('correlation', 0):.2f}")
        col7.metric("💧 Volumen Total", format_currency(summary.get('total_volume', 0)))
        regime_dist = diagnosis.diagnosis.get('regime_distribution', {})
        if regime_dist:
            st.subheader("📊 Distribución de Regímenes")
            df_regime = pd.DataFrame({
                'Régimen': list(regime_dist.keys()),
                'Cantidad': list(regime_dist.values())
            })
            fig = px.pie(df_regime, values='Cantidad', names='Régimen', title="Distribución de Regímenes de Mercado")
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("📊 Riesgo por Activo")
        if st.session_state.data_dict:
            risk_data = []
            for sym, df in list(st.session_state.data_dict.items())[:20]:
                if df is not None and not df.empty:
                    atr = compute_atr(df).iloc[-1] if not compute_atr(df).empty else 0
                    close = df['close'].iloc[-1]
                    volatility = atr / close * 100 if close > 0 else 0
                    risk_data.append({
                        'Activo': sym,
                        'Volatilidad': volatility,
                        'Precio': close,
                    })
            if risk_data:
                df_risk = pd.DataFrame(risk_data)
                fig = px.bar(df_risk, x='Activo', y='Volatilidad', title="Volatilidad por Activo")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos disponibles para el diagnóstico")

# ============================================================
# TAB 7: Exchanges & Wise (sistema principal)
# ============================================================
with tabs[6]:
    st.header("🏦 Exchanges y Wise Integration")
    st.subheader("📊 Exchanges Conectados")
    available = st.session_state.data_engine.get_available_exchanges()
    from config import EXCHANGES
    for ex_id in available:
        status = EXCHANGES.get(ex_id, {}).get('type', 'spot')
        st.write(f"✅ {ex_id} ({status})")
    st.subheader("📊 Activos por Exchange")
    from exchange_aggregator import ExchangeAggregator
    aggregator = ExchangeAggregator(st.session_state.data_engine)
    summary = aggregator.get_asset_summary()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Activos", summary['total'])
    col2.metric("Aprobados", summary['approved'])
    col3.metric("Recomendados", summary['recommended'])
    col4.metric("Rechazados", summary['rejected'])
    st.write("**Detalle por exchange:**")
    for ex_id, count in summary['by_exchange'].items():
        st.write(f"  {ex_id}: {count} activos")
    with st.expander("📋 Tabla de Activos por Exchange"):
        df_assets = aggregator.display_asset_table()
        st.dataframe(df_assets, width='stretch')
    st.markdown("---")
    st.subheader("💱 Wise Integration — Monedas Soportadas")
    from wise_integration import WiseIntegration
    wise = WiseIntegration()
    df_wise = wise.get_wise_table()
    st.dataframe(df_wise, width='stretch')
    st.subheader("🔄 Conversor de Monedas Wise")
    col1, col2 = st.columns(2)
    with col1:
        from_cur = st.selectbox("Desde", wise.get_wise_supported_list(), index=0)
        amount = st.number_input("Cantidad", min_value=0.0, value=100.0)
    with col2:
        to_cur = st.selectbox("Hasta", wise.get_wise_supported_list(), index=1)
        if st.button("Calcular conversión"):
            result = wise.convert(amount, from_cur, to_cur)
            if result is not None:
                st.success(f"💰 {amount:.2f} {from_cur} = {result:.2f} {to_cur}")
            else:
                st.warning("No se pudo obtener la tasa de cambio")

# ============================================================
# TAB 8: Firm Signals Ω (nuevo motor de certificación)
# ============================================================
with tabs[7]:
    if FIRM_SIGNALS_AVAILABLE:
        render_firm_signals_panel()
    else:
        st.warning("⚠️ El módulo Firm Signals Ω no está instalado en el repositorio.")
        st.info("""
        ### Instalación de Firm Signals Ω
        
        Para habilitar este módulo, debes agregar la carpeta `firm_signals_omega` en la raíz del proyecto.
        
        Los archivos necesarios son:
        - `firm_signals_omega/__init__.py`
        - `firm_signals_omega/config.py`
        - `firm_signals_omega/data_engine.py`
        - `firm_signals_omega/certification_engine.py`
        - `firm_signals_omega/assistant.py`
        - `firm_signals_omega/signal_generator.py`
        - `firm_signals_omega/ranking_engine.py`
        - `firm_signals_omega/validator.py`
        - `firm_signals_omega/macro_integration.py`
        - `firm_signals_omega/streamlit_app.py`
        - `firm_signals_omega/utils.py`
        
        Consulta la documentación para más detalles.
        """)

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(f"🧸 {PROJECT_NAME} — v{VERSION} 🧸🐻🎉")
st.caption("💜 Apoya el proyecto: Alias `walywasaby` (Prex) | USDT TRC20: `TCiRVXggAqDx6bhJH5KBdf8E4NcJ2voMf8`")
