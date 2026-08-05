# firm_signals_omega/streamlit_app.py
"""
Firm Signals Ω — Interfaz Streamlit

Panel independiente para monitoreo y ejecución de certificación de señales.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

from .config import FIRM_SIGNALS_CONFIG
from .data_engine import FirmDataEngine
from .certification_engine import CertificationEngine
from .assistant import ExecutionAssistant
from .signal_generator import SignalGenerator
from .ranking_engine import RankingEngine

def render_firm_signals_panel():
    """Renderiza el panel de Firm Signals Ω"""
    
    st.markdown("---")
    st.title("🧸 FIRM SIGNALS Ω")
    st.subheader("Motor de Certificación de Señales de Máxima Calidad")
    st.markdown("---")
    
    # Inicializar
    if 'firm_data_engine' not in st.session_state:
        st.session_state.firm_data_engine = FirmDataEngine()
        st.session_state.firm_assistant = ExecutionAssistant()
        st.session_state.firm_certification = CertificationEngine()
        st.session_state.firm_last_scan = None
        st.session_state.firm_candidates = []
    
    # Sidebar de control
    with st.sidebar:
        st.header("🎛️ Control")
        scan_btn = st.button("🚀 Ejecutar Análisis", type="primary", use_container_width=True)
        st.markdown("---")
        st.header("📊 Estado")
        status = st.session_state.firm_assistant.get_display()
        st.metric("Estado", status['status'])
        st.metric("Progreso", f"{status['progress']*100:.0f}%")
        st.caption(f"Próxima revisión: {status.get('next_check', 'N/A')}")
    
    # Botón de ejecución
    if scan_btn or st.session_state.firm_last_scan is None:
        with st.spinner("🔍 Ejecutando análisis de Firm Signals Ω..."):
            # Obtener datos
            data_engine = st.session_state.firm_data_engine
            symbols = data_engine.get_symbols(max_symbols=50)
            
            # Generar señales candidatas
            generator = SignalGenerator(data_engine)
            candidates = generator.generate_candidates(symbols)
            
            st.session_state.firm_candidates = candidates
            st.session_state.firm_last_scan = datetime.now()
            
            # Certificar la mejor candidata
            if candidates:
                best = candidates[0]
                
                # Obtener datos de mercado
                market_data = {}
                macro_data = {}
                
                # Certificar
                cert_engine = st.session_state.firm_certification
                result = cert_engine.certify(best, market_data, macro_data)
                
                # Actualizar asistente
                assistant = st.session_state.firm_assistant
                assistant.update(result, market_data)
    
    # Mostrar estado
    assistant = st.session_state.firm_assistant
    display = assistant.get_display()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📡 Estado", display['status'])
    with col2:
        st.metric("📊 Progreso", f"{display['progress']*100:.0f}%")
    with col3:
        next_check = display.get('next_check', 'N/A')
        st.metric("⏰ Próxima revisión", next_check)
    
    # Barra de progreso
    st.progress(display['progress'])
    
    # Detalles de formación
    formation = display.get('formation', {})
    if formation:
        st.subheader("🔬 Formación de Señal")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Nivel:** {formation.get('level', 'N/A')}")
        with col2:
            if 'components' in formation:
                for name, value in formation['components'].items():
                    st.write(f"{name}: {value}")
    
    # Estimaciones de tiempo
    estimations = display.get('estimated_time', {})
    if estimations:
        st.subheader("⏳ Estimación de Próxima Señal")
        cols = st.columns(4)
        probs = [
            ('15 min', estimations.get('probability_15min', 0)),
            ('30 min', estimations.get('probability_30min', 0)),
            ('1 h', estimations.get('probability_1h', 0)),
            ('3 h', estimations.get('probability_3h', 0)),
            ('6 h', estimations.get('probability_6h', 0)),
            ('12 h', estimations.get('probability_12h', 0)),
            ('24 h', estimations.get('probability_24h', 0)),
        ]
        for i, (label, prob) in enumerate(probs):
            with cols[i % 4]:
                st.metric(label, f"{prob*100:.0f}%")
    
    # Mostrar señal si está publicada
    signal = display.get('signal')
    if signal:
        st.markdown("---")
        st.success("🎯 SEÑAL CERTIFICADA — Lista para ejecutar")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Activo", signal.get('symbol', 'N/A'))
            st.metric("Dirección", signal.get('direction', 'N/A'))
        with col2:
            st.metric("Score", f"{signal.get('score', 0):.3f}")
            st.metric("Confianza", f"{signal.get('confidence', 0)*100:.1f}%")
        with col3:
            st.metric("Precio", f"${signal.get('entry_price', 0):.2f}")
            st.metric("SL", f"${signal.get('sl_price', 0):.2f}")
            st.metric("TP", f"${signal.get('tp_price', 0):.2f}")
        
        # Detalles completos
        with st.expander("📋 Detalles completos de la señal", expanded=True):
            st.json(signal)
    else:
        # Mostrar candidatas si no hay señal publicada
        candidates = st.session_state.firm_candidates
        if candidates:
            st.subheader("📊 Candidatas (en espera de certificación)")
            df_candidates = pd.DataFrame([{
                'Activo': c.get('symbol', ''),
                'Score': c.get('score', 0),
                'ADX': c.get('adx', 0),
                'Dirección': c.get('direction', ''),
                'Régimen': c.get('regime', ''),
            } for c in candidates[:10]])
            st.dataframe(df_candidates, width='stretch')
    
    # Tips
    tips = display.get('tips', [])
    if tips:
        st.markdown("---")
        st.subheader("💡 Consejos")
        for tip in tips:
            st.write(tip)
    
    # Histórico
    with st.expander("📜 Histórico de Certificaciones"):
        history = assistant.history[-20:] if hasattr(assistant, 'history') else []
        if history:
            df_history = pd.DataFrame([{
                'Hora': h.get('timestamp', datetime.now()).strftime('%H:%M:%S'),
                'Estado': h.get('state', ''),
                'Progreso': f"{h.get('progress', 0)*100:.0f}%",
                'Señal': h.get('signal', {}).get('symbol', 'N/A') if h.get('signal') else 'N/A'
            } for h in history])
            st.dataframe(df_history, width='stretch')
