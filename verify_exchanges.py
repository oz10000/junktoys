#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JUNK TOYS — Verificador de Exchanges
Prueba conectividad y descarga de velas de múltiples exchanges públicos
Muestra resultados en consola con formato ASCII
No utiliza fallbacks ni datos sintéticos
"""

import ccxt
import time
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# ============================================================
# CONFIGURACIÓN
# ============================================================
TEST_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
TIMEFRAME = '5m'
LIMIT = 50

EXCHANGES_TO_TEST = [
    'bybit',
    'binance',
    'okx',
    'kucoin',
    'mexc',
    'kraken',
]

EXCHANGE_OPTIONS = {
    'bybit': {'defaultType': 'linear'},
    'binance': {'defaultType': 'future'},
    'okx': {'defaultType': 'swap'},
    'kucoin': {'defaultType': 'future'},
    'mexc': {'defaultType': 'future'},
    'kraken': {'defaultType': 'spot'},
}

# ============================================================
# FUNCIONES DE COLOR (para consola)
# ============================================================
def green(text: str) -> str:
    return f"\033[92m{text}\033[0m"

def red(text: str) -> str:
    return f"\033[91m{text}\033[0m"

def yellow(text: str) -> str:
    return f"\033[93m{text}\033[0m"

def cyan(text: str) -> str:
    return f"\033[96m{text}\033[0m"

def white(text: str) -> str:
    return f"\033[97m{text}\033[0m"

def bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"

# ============================================================
# PRUEBA DE EXCHANGE
# ============================================================
def test_exchange(ex_id: str) -> Dict:
    """Prueba un exchange: conectividad y descarga de velas."""
    result = {
        'exchange': ex_id,
        'status': '❌ FALLÓ',
        'symbols_tested': 0,
        'symbols_ok': 0,
        'candles_total': 0,
        'errors': [],
        'details': {},
        'time_ms': 0,
        'api_type': 'unknown'
    }
    
    start_total = time.time()
    
    try:
        # 1. Conectar
        opts = EXCHANGE_OPTIONS.get(ex_id, {})
        exchange_class = getattr(ccxt, ex_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'options': opts
        })
        
        # 2. Cargar mercados
        exchange.load_markets()
        result['api_type'] = str(exchange.options.get('defaultType', 'spot'))
        
        # 3. Probar cada símbolo
        for sym in TEST_SYMBOLS:
            result['symbols_tested'] += 1
            try:
                start = time.time()
                ohlcv = exchange.fetch_ohlcv(sym, TIMEFRAME, limit=LIMIT)
                elapsed = (time.time() - start) * 1000
                
                if ohlcv and len(ohlcv) > 0:
                    result['symbols_ok'] += 1
                    result['candles_total'] += len(ohlcv)
                    result['details'][sym] = {
                        'status': '✅ OK',
                        'candles': len(ohlcv),
                        'time_ms': round(elapsed, 1),
                        'first_ts': datetime.fromtimestamp(ohlcv[0][0]/1000).isoformat() if ohlcv else None,
                        'last_ts': datetime.fromtimestamp(ohlcv[-1][0]/1000).isoformat() if ohlcv else None,
                    }
                else:
                    result['errors'].append(f"{sym}: sin datos")
                    result['details'][sym] = {'status': '❌ SIN DATOS'}
            except Exception as e:
                result['errors'].append(f"{sym}: {str(e)[:80]}")
                result['details'][sym] = {'status': f'❌ ERROR: {str(e)[:60]}'}
        
        # 4. Determinar estado final
        if result['symbols_ok'] >= 2:
            result['status'] = '✅ FUNCIONA'
        elif result['symbols_ok'] >= 1:
            result['status'] = '⚠️ PARCIAL'
        else:
            result['status'] = '❌ FALLÓ'
            
    except Exception as e:
        result['status'] = '❌ FALLÓ'
        result['errors'].append(f"Conectividad: {str(e)[:100]}")
    
    result['time_ms'] = round((time.time() - start_total) * 1000, 1)
    return result

# ============================================================
# MOSTRAR RESULTADOS EN CONSOLA (ASCII)
# ============================================================
def print_ascii_banner():
    """Muestra banner ASCII del proyecto."""
    print()
    print(cyan("="*70))
    print(cyan("  🧸 JUNK TOYS — VERIFICADOR DE EXCHANGES 🧸"))
    print(cyan("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print(cyan("="*70))
    print()

def print_exchange_result(result: Dict):
    """Muestra resultado de un exchange en formato ASCII."""
    ex = result['exchange']
    status = result['status']
    ok_count = result['symbols_ok']
    total_count = result['symbols_tested']
    candles = result['candles_total']
    time_ms = result['time_ms']
    
    # Línea principal
    status_color = green if '✅' in status else red if '❌' in status else yellow
    print(f"{status_color(status)}  {bold(ex.upper())}  ", end="")
    print(f"({ok_count}/{total_count} símbolos)  ", end="")
    print(f"{candles} velas  ", end="")
    print(f"{time_ms}ms  ", end="")
    print(f"[{result['api_type']}]")
    
    # Detalles por símbolo
    for sym, detail in result['details'].items():
        if detail.get('status', '').startswith('✅'):
            print(f"    {green('✅')} {sym:<10} {detail.get('candles', 0):>3} velas  {detail.get('time_ms', 0):>5}ms  {detail.get('first_ts', '')[:16]} → {detail.get('last_ts', '')[:16]}")
        elif detail.get('status', '').startswith('❌'):
            print(f"    {red('❌')} {sym:<10} {detail.get('status', 'ERROR')}")
        else:
            print(f"    {yellow('⚠️')} {sym:<10} {detail.get('status', 'UNKNOWN')}")
    
    # Errores si los hay
    if result['errors']:
        for err in result['errors'][:3]:
            print(f"    {red('⚠️')} {err[:70]}")
        if len(result['errors']) > 3:
            print(f"    {yellow('... y')} {len(result['errors'])-3} {yellow('errores más')}")
    
    print()

def print_summary(results: List[Dict]):
    """Muestra resumen final."""
    print(cyan("-"*70))
    print(cyan("  📊 RESUMEN FINAL"))
    print(cyan("-"*70))
    
    working = [r for r in results if '✅ FUNCIONA' in r['status']]
    partial = [r for r in results if '⚠️ PARCIAL' in r['status']]
    failed = [r for r in results if '❌ FALLÓ' in r['status']]
    
    print(f"  {green('✅ Funcionan:')} {len(working)}  ", end="")
    print(f"{yellow('⚠️ Parciales:')} {len(partial)}  ", end="")
    print(f"{red('❌ Fallaron:')} {len(failed)}")
    
    if working:
        print(f"\n  {green('✅ EXCHANGE RECOMENDADO:')} {bold(working[0]['exchange'].upper())}")
        print(f"     ({working[0]['symbols_ok']}/{working[0]['symbols_tested']} símbolos, {working[0]['candles_total']} velas, {working[0]['time_ms']}ms)")
    
    print()
    print(cyan("="*70))
    print(cyan("  🧸 Verificación completada. Bybit es el exchange recomendado."))
    print(cyan("="*70))
    print()

# ============================================================
# MAIN
# ============================================================
def main():
    print_ascii_banner()
    
    results = []
    for ex_id in EXCHANGES_TO_TEST:
        print(f"🔍 Probando {ex_id.upper()}...")
        result = test_exchange(ex_id)
        results.append(result)
        print_exchange_result(result)
        time.sleep(0.5)  # Pequeña pausa entre pruebas
    
    print_summary(results)
    
    # Retornar código de salida
    working = [r for r in results if '✅ FUNCIONA' in r['status']]
    if working:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
