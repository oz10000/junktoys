# firm_signals_omega/assistant.py
"""
Asistente de Ejecución — Firm Signals Ω

Proporciona estado continuo, estimaciones y guía para el operador.
"""

from datetime import datetime
from typing import Dict, Optional
import numpy as np

class ExecutionAssistant:
    """
    Asistente de ejecución que guía al operador durante todo el proceso
    """
    
    def __init__(self):
        self.state = "ESPERAR"
        self.progress = 0.0
        self.current_signal = None
        self.estimations = {}
        self.history = []
        self._formation_details = {}
        
    def update(self, certification_response: Dict, market_data: Dict):
        """
        Actualiza el estado del asistente con la última certificación
        """
        self.state = certification_response.get('status', 'ESPERAR')
        self.progress = certification_response.get('progress', 0.0)
        self.current_signal = certification_response.get('signal')
        
        # Actualizar estimaciones
        self.estimations = certification_response.get('estimations', {})
        
        # Registrar historial
        self.history.append({
            'timestamp': datetime.now(),
            'state': self.state,
            'progress': self.progress,
            'signal': self.current_signal
        })
        
        # Mantener historial limitado
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
    
    def get_display(self) -> Dict:
        """
        Retorna la información para mostrar en la interfaz
        """
        return {
            'status': self._get_status_display(),
            'state': self.state,
            'progress': self.progress,
            'progress_bar': self._get_progress_bar(),
            'formation': self._get_formation_details(),
            'estimated_time': self.estimations,
            'signal': self._get_signal_summary(),
            'next_check': self._get_next_check_time(),
            'tips': self._get_tips(),
        }
    
    def _get_status_display(self) -> str:
        """Obtiene el estado con emoji y color"""
        status_map = {
            'ESPERAR': '⏳ ESPERAR',
            'PREPARANDO': '🔍 PREPARANDO',
            'CERTIFICANDO: calidad': '📊 CERTIFICANDO',
            'CERTIFICANDO: confirmacion': '🔬 CERTIFICANDO',
            'CERTIFICANDO: microestructura': '🔍 CERTIFICANDO',
            'CERTIFICANDO: temporal': '⏰ CERTIFICANDO',
            'CERTIFICANDO: contexto': '🌍 CERTIFICANDO',
            'PUBLICADA': '🎯 SEÑAL CERTIFICADA',
            'CANCELADA': '⛔ SEÑAL RECHAZADA',
        }
        return status_map.get(self.state, self.state)
    
    def _get_progress_bar(self) -> Dict:
        """Genera barra de progreso visual"""
        bar_length = 20
        filled = int(self.progress * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        return {
            'bar': bar,
            'percentage': self.progress * 100,
            'label': f"{self.progress*100:.0f}%"
        }
    
    def _get_formation_details(self) -> Dict:
        """Detalles de formación de la señal"""
        if self.state == "ESPERAR":
            return {
                'level': 'Esperando condiciones',
                'components': {
                    'ADX': '0%',
                    'Volumen': '0%',
                    'Score': '0%',
                    'Régimen': '0%',
                }
            }
        
        return {
            'level': f'Formación {self.progress*100:.0f}%',
            'components': {
                'ADX': f'{min(100, self.progress*120):.0f}%',
                'Volumen': f'{min(100, self.progress*110):.0f}%',
                'Score': f'{min(100, self.progress*130):.0f}%',
                'Régimen': '✅' if self.progress > 0.6 else '⏳',
            }
        }
    
    def _get_signal_summary(self) -> Optional[Dict]:
        """Resumen de la señal actual"""
        if self.current_signal is None:
            return None
        
        return {
            'symbol': self.current_signal.get('symbol', ''),
            'direction': self.current_signal.get('direction', ''),
            'score': self.current_signal.get('score', 0),
            'entry_price': self.current_signal.get('entry_price', 0),
            'sl_price': self.current_signal.get('sl_price', 0),
            'tp_price': self.current_signal.get('tp_price', 0),
        }
    
    def _get_next_check_time(self) -> str:
        """Calcula cuándo revisar nuevamente"""
        remaining = self.estimations.get('remaining_minutes', 30)
        if remaining < 1:
            return "Ahora mismo"
        elif remaining < 60:
            return f"En {int(remaining)} minutos"
        else:
            hours = remaining / 60
            return f"En {hours:.1f} horas"
    
    def _get_tips(self) -> List[str]:
        """Consejos para el operador según el estado"""
        tips_map = {
            'ESPERAR': [
                '💡 Revisa el panel cada 30 minutos',
                '📊 Mantén el trailing stop configurado en 0.3%',
                '🔍 Monitorea el ADX y el volumen para anticipar señales',
            ],
            'PREPARANDO': [
                '⏳ Prepárate para ejecutar',
                '📊 Revisa los parámetros de la señal candidata',
                '🎯 Ten el exchange listo para entrada Market',
            ],
            'CERTIFICANDO': [
                '🔬 Espera la certificación completa',
                '📊 No ejecutes antes de tiempo',
                '🎯 La señal está siendo validada',
            ],
            'PUBLICADA': [
                '🚀 Ejecuta la orden de mercado AHORA',
                '📊 Configura SL y TP inmediatamente',
                '🎯 Activa el trailing stop al 0.3%',
                '⏰ La operación tiene una duración estimada de 1.5-3 horas',
            ],
            'CANCELADA': [
                '⏳ Espera la próxima oportunidad',
                '📊 La señal no cumplió los estándares de calidad',
                '🎯 La próxima revisión será en 30 minutos',
            ],
        }
        return tips_map.get(self.state, ['💡 Esperando condiciones de mercado'])
