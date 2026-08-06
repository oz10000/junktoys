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
    TIMEFRAME, KILL_SWITCH, ENTRY_ZONES, FALLBACK_SYMBOLS,
    EXCHANGES  # <--- FIRM_SIGNALS_CONFIG ELIMINADO DE AQUÍ
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
# FUNCIONES AUXILIARES
# ============================================================
def pad_list(items, target=10):
    result = items[:target]
    while len(result) < target:
        result.append(None)
    return result

def estimate_time_for_symbol(symbol, score, is_valid, signal_history):
    if is_valid:
        return 0.0
    hist = [s for s in signal_history if s.get('symbol') == symbol and s.get('is_valid', False)]
    if len(hist) > 1:
        intervals = [(hist[i+1]['timestamp'] - hist[i]['timestamp']).total_seconds() / 60 for i in range(len(hist)-1)]
        if intervals:
            avg_interval = np.mean(intervals)
            reduction = abs(score) * 0.5
            return max(0.0, avg_interval * (1 - reduction))
    if abs(score) > 0.3:
        base = 60.0
        reduction = abs(score) * 0.6
        return max(5.0, base * (1 - reduction))
    return None

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

        estimated_time = estimate_time_for_symbol(sym, s.score, s.is_valid, st.session_state.signal_history)

        rank_entry = {
            'symbol': sym,
            'signal': s,
            'score': s.score,
            'adx': adx_val,
            'ker': ker_val,
            'atr_pct': atr_pct,
            'amplitude_pct': atr_pct,
            'amplitude_usd': atr_val,
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
            'estimated_time': estimated_time,
        }
        all_rankings.append(rank_entry)
        if s.is_valid:
            valid_signals.append(s)

    all_rankings.sort(key=lambda x: abs(x['score']), reverse=True)
    return all_rankings, valid_signals

def estimate_next_signal_global(signal_history):
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
            "Amplitud %": r['amplitude_pct'],
            "Amplitud USD": r['amplitude_usd'],
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
        st.write(f"Amplitud: {r['amplitude_pct']:.2f}% (${r['amplitude_usd']:.2f})")

    with col2:
        st.markdown("**🛑 Gestión de Riesgo**")
        st.write(f"SL: ${r['sl_price']:.4f} ({r['sl_price']/r['entry_price']-1:.2%})")
        st.write(f"TP: ${r['tp_price']:.4f} ({r['tp_price']/r['entry_price']-1:.2%})")
        st.write(f"Break Even Trigger: {r['break_even_trigger']:.2%}")
        st.write(f"Tiempo máx: {r['max_hold_minutes']} min")

        est_time = r.get('estimated_time')
        if est_time is not None and isinstance(est_time, (int, float)):
            if est_time < 1:
                st.write("⏳ Tiempo estimado para activación: < 1 min")
            elif est_time < 60:
                st.write(f"⏳ Tiempo estimado para activación: {int(est_time)} min")
            else:
                st.write(f"⏳ Tiempo estimado para activación: {est_time/60:.1f} h")
        else:
            st.write("⏳ Tiempo estimado para activación: N/A")

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
# PESTAÑAS
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
# TAB 1 — TRADE ÓPTIMO
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
                        from amplitude_analyzer import define_zones
                        avg_range = trade.amplitudes.get('avg_candle_range', 0.5)
                        zones = define_zones(avg_range, trade.entry_price)
                        if isinstance(zones, dict):
                            for zone_name, zone_data in zones.items():
                                if isinstance(zone_data, dict):
                                    color = ENTRY_ZONES.get(zone_name, {}).get('color', '#888')
                                    st.markdown(f"""
                                    <div class="trade-card zone-{zone_name.lower()}">
                                        <b>Zona {zone_name}</b>: ${zone_data.get('support', 0):.2f} — ${zone_data.get('resistance', 0):.2f}
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
# TAB 2 — RANKING COMPLETO
# ============================================================
with tabs[1]:
    st.header("🏆 Ranking Completo — Top 10 Long / Short")
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
            longs = [r for r in all_rankings if r['direction'] == 'Long' or (r['direction'] == 'N/A' and r['score'] > 0)]
            shorts = [r for r in all_rankings if r['direction'] == 'Short' or (r['direction'] == 'N/A' and r['score'] < 0)]

            if not longs:
                longs = sorted([r for r in all_rankings if r['score'] > 0], key=lambda x: abs(x['score']), reverse=True)
            if not shorts:
                shorts = sorted([r for r in all_rankings if r['score'] < 0], key=lambda x: abs(x['score']), reverse=True)

            longs_padded = pad_list(longs, 10)
            shorts_padded = pad_list(shorts, 10)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🟢 Top 10 Long")
                data_long = []
                for i, r in enumerate(longs_padded):
                    if r is None:
                        data_long.append({'Pos': i+1, 'Activo': 'N/A', 'Score': 'N/A', 'ADX': 'N/A', 'KER': 'N/A', 'Amplitud%': 'N/A', 'Amplitud$': 'N/A', 'Tiempo estimado': 'N/A', 'Aprobado': 'N/A', 'Motivo': 'No hay suficientes longs'})
                    else:
                        est_time = r.get('estimated_time')
                        if est_time is not None and isinstance(est_time, (int, float)):
                            if est_time < 1:
                                time_str = "< 1 min"
                            elif est_time < 60:
                                time_str = f"{int(est_time)} min"
                            else:
                                time_str = f"{est_time/60:.1f} h"
                        else:
                            time_str = "N/A"
                        data_long.append({
                            'Pos': i+1,
                            'Activo': r['symbol'],
                            'Score': f"{r['score']:.3f}",
                            'ADX': f"{r['adx']:.1f}",
                            'KER': f"{r['ker']:.2f}",
                            'Amplitud%': f"{r['amplitude_pct']:.2f}%",
                            'Amplitud$': f"${r['amplitude_usd']:.2f}",
                            'Tiempo estimado': time_str,
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
                        data_short.append({'Pos': i+1, 'Activo': 'N/A', 'Score': 'N/A', 'ADX': 'N/A', 'KER': 'N/A', 'Amplitud%': 'N/A', 'Amplitud$': 'N/A', 'Tiempo estimado': 'N/A', 'Aprobado': 'N/A', 'Motivo': 'No hay suficientes shorts'})
                    else:
                        est_time = r.get('estimated_time')
                        if est_time is not None and isinstance(est_time, (int, float)):
                            if est_time < 1:
                                time_str = "< 1 min"
                            elif est_time < 60:
                                time_str = f"{int(est_time)} min"
                            else:
                                time_str = f"{est_time/60:.1f} h"
                        else:
                            time_str = "N/A"
                        data_short.append({
                            'Pos': i+1,
                            'Activo': r['symbol'],
                            'Score': f"{r['score']:.3f}",
                            'ADX': f"{r['adx']:.1f}",
                            'KER': f"{r['ker']:.2f}",
                            'Amplitud%': f"{r['amplitude_pct']:.2f}%",
                            'Amplitud$': f"${r['amplitude_usd']:.2f}",
                            'Tiempo estimado': time_str,
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
                est_long = estimate_next_signal_global(long_history)
                if est_long:
                    st.metric("⏱️ Próxima señal LONG",
                              f"{est_long['remaining_minutes']:.0f} min",
                              delta=f"Promedio: {est_long['avg_minutes']:.0f} min")
                    st.caption(f"Confianza: {est_long['confidence']:.0%}")
                else:
                    st.info("No hay suficientes datos para estimar Long")

            with col2:
                est_short = estimate_next_signal_global(short_history)
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
# TAB 3 — BACKTESTING
# ============================================================
with tabs[2]:
    st.header("📈 Backtesting Completo")
    if run_backtest_btn:
        with st.spinner("🔄 Ejecutando backtesting..."):
            try:
                from backtester import Backtester
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
# TAB 4 — BTC/ETH/SOL
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
# TAB 5 — OPTIMIZACIÓN
# ============================================================
with tabs[4]:
    st.header("🧠 Laboratorio de Optimización (100 iteraciones)")
    if st.button("🧠 Ejecutar Optimización", type="secondary"):
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
                    if 'tracking' in results and 'winrates' in results['tracking']:
                        fig = px.line(x=results['tracking']['iterations'], y=results['tracking']['winrates'],
                                      title="📈 Evolución del Win Rate durante la optimización")
                        fig.update_layout(yaxis_tickformat='.0%')
                        st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error en optimización: {e}")
    else:
        st.info("Presiona el botón para ejecutar la optimización completa")

# ============================================================
# TAB 6 — DIAGNÓSTICO
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
# TAB 7 — EXCHANGES & WISE
# ============================================================
with tabs[6]:
    st.header("🏦 Exchanges y Wise Integration")
    st.subheader("📊 Exchanges Conectados")
    available = st.session_state.data_engine.get_available_exchanges()
    for ex_id in available:
        status = EXCHANGES.get(ex_id, {}).get('type', 'spot')
        st.write(f"✅ {ex_id} ({status})")
    st.write("---")
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
# TAB 8 — FIRM SIGNALS Ω (NUEVO PANEL)
# ============================================================
with tabs[7]:
    st.header("🧸 Firm Signals Ω — Panel de Ejecución")
    try:
        from firm_signals_omega.streamlit_panel import render_firm_signals_panel
        render_firm_signals_panel()
    except ImportError as e:
        st.warning(f"⚠️ El módulo Firm Signals Ω no está instalado correctamente.")
        st.info("""
        **Instalación:**
        Copia la carpeta `firm_signals_omega` en la raíz del proyecto.
        """)
    except Exception as e:
        st.error(f"Error al cargar Firm Signals Ω: {e}")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(f"🧸 {PROJECT_NAME} — v{VERSION} 🧸🐻🎉")
st.caption("💜 Apoya el proyecto: Alias `walywasaby` (Prex) | USDT TRC20: `TCiRVXggAqDx6bhJH5KBdf8E4NcJ2voMf8`")
