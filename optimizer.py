# optimizer.py
import numpy as np
import pandas as pd
import itertools
import time
import json
import os
from datetime import datetime, timedelta
from scipy.optimize import minimize
from skopt import gp_minimize
from skopt.space import Real, Integer
from concurrent.futures import ProcessPoolExecutor, as_completed

from data_engine import DataEngine
from backtester import Backtester
from scoring_engine import compute_advanced_score
from ranking_engine import RankingEngine
from config import (
    PARAM_RANGES, OPTIMIZATION_ITERATIONS, WALK_FORWARD_SPLITS,
    MONTE_CARLO_SIMULATIONS, BAYESIAN_INITIAL_POINTS, BAYESIAN_N_CALLS,
    DEFAULT_PARAMS, INITIAL_CAPITAL, RESULTS_DIR
)
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizationLab:
    """Laboratorio completo de optimización"""
    
    def __init__(self, symbols, data_dict):
        self.symbols = symbols
        self.data = data_dict
        self.results = []
        self.best_params = None
        self.best_winrate = 0
        self.best_metrics = {}
        self.tracking = {
            'iterations': [],
            'winrates': [],
            'profit_factors': [],
            'drawdowns': [],
            'sharpe_ratios': [],
        }
        os.makedirs(RESULTS_DIR, exist_ok=True)
    
    def run_grid_search(self, param_grid=None):
        """Grid Search sobre parámetros"""
        if param_grid is None:
            param_grid = {
                'sl_mult': [0.6, 0.8, 1.0, 1.2, 1.4],
                'tp_mult': [1.5, 2.0, 2.5, 3.0, 3.5],
                'trailing_distance': [0.004, 0.006, 0.008, 0.010, 0.012],
                'trailing_activation': [0.005, 0.010, 0.015, 0.020],
                'min_score': [0.20, 0.25, 0.30, 0.35, 0.40],
            }
        
        logger.info("🚀 Iniciando Grid Search...")
        keys = list(param_grid.keys())
        combinations = list(itertools.product(*param_grid.values()))
        logger.info(f"📊 {len(combinations)} combinaciones a probar")
        
        results = []
        for i, combo in enumerate(combinations):
            params = dict(zip(keys, combo))
            full_params = DEFAULT_PARAMS.copy()
            full_params.update(params)
            
            winrate = self._evaluate_params(full_params)
            results.append({
                'params': full_params,
                'winrate': winrate,
                'iteration': i
            })
            
            if i % 10 == 0:
                logger.info(f"Grid Search: {i}/{len(combinations)} completadas")
        
        results.sort(key=lambda x: x['winrate'], reverse=True)
        self._update_best(results[0])
        return results
    
    def run_random_search(self, n_iterations=50):
        """Random Search sobre parámetros"""
        logger.info(f"🎲 Iniciando Random Search ({n_iterations} iteraciones)...")
        results = []
        
        for i in range(n_iterations):
            params = self._generate_random_params()
            winrate = self._evaluate_params(params)
            results.append({
                'params': params,
                'winrate': winrate,
                'iteration': i
            })
            
            if winrate > self.best_winrate:
                self._update_best({'params': params, 'winrate': winrate, 'iteration': i})
            
            if i % 10 == 0:
                logger.info(f"Random Search: {i}/{n_iterations} completadas, mejor WinRate: {self.best_winrate:.2%}")
        
        results.sort(key=lambda x: x['winrate'], reverse=True)
        return results
    
    def run_bayesian_optimization(self, n_calls=BAYESIAN_N_CALLS, n_initial_points=BAYESIAN_INITIAL_POINTS):
        """Optimización Bayesiana"""
        logger.info(f"🧠 Iniciando Optimización Bayesiana ({n_calls} llamadas)...")
        
        dimensions = [
            Real(PARAM_RANGES['sl_mult'][0], PARAM_RANGES['sl_mult'][1], name='sl_mult'),
            Real(PARAM_RANGES['tp_mult'][0], PARAM_RANGES['tp_mult'][1], name='tp_mult'),
            Real(PARAM_RANGES['trailing_distance'][0], PARAM_RANGES['trailing_distance'][1], name='trailing_distance'),
            Real(PARAM_RANGES['trailing_activation'][0], PARAM_RANGES['trailing_activation'][1], name='trailing_activation'),
            Real(PARAM_RANGES['break_even_trigger'][0], PARAM_RANGES['break_even_trigger'][1], name='break_even_trigger'),
            Real(PARAM_RANGES['min_score'][0], PARAM_RANGES['min_score'][1], name='min_score'),
            Real(PARAM_RANGES['adx_threshold'][0], PARAM_RANGES['adx_threshold'][1], name='adx_threshold'),
            Real(PARAM_RANGES['ker_threshold'][0], PARAM_RANGES['ker_threshold'][1], name='ker_threshold'),
        ]
        
        def objective(params):
            param_dict = DEFAULT_PARAMS.copy()
            for i, dim in enumerate(dimensions):
                param_dict[dim.name] = params[i]
            return -self._evaluate_params(param_dict)
        
        result = gp_minimize(
            objective,
            dimensions,
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            random_state=42,
            verbose=True
        )
        
        best_params = DEFAULT_PARAMS.copy()
        for i, dim in enumerate(dimensions):
            best_params[dim.name] = result.x[i]
        
        winrate = self._evaluate_params(best_params)
        self._update_best({'params': best_params, 'winrate': winrate})
        
        return {'best_params': best_params, 'winrate': winrate, 'result': result}
    
    def run_walk_forward(self, n_splits=WALK_FORWARD_SPLITS):
        """Walk-Forward Validation con optimización en cada ventana"""
        logger.info(f"🚶 Iniciando Walk-Forward ({n_splits} splits)...")
        
        dates = sorted(self.data[list(self.data.keys())[0]].index)
        split_size = len(dates) // (n_splits + 1)
        
        results = []
        for i in range(n_splits):
            train_end = (i + 1) * split_size
            test_end = min(len(dates), (i + 2) * split_size)
            
            train_dates = dates[:train_end]
            test_dates = dates[train_end:test_end]
            
            train_data = {}
            test_data = {}
            for sym, df in self.data.items():
                train_data[sym] = df.loc[df.index.isin(train_dates)]
                test_data[sym] = df.loc[df.index.isin(test_dates)]
            
            logger.info(f"🔬 Optimizando ventana {i+1}/{n_splits}...")
            opt_params = self._run_quick_optimization(train_data)
            
            bt = Backtester(test_data, {'__global__': opt_params}, INITIAL_CAPITAL)
            _, _, _ = bt.run()
            metrics = bt.calculate_metrics()
            
            results.append({
                'window': i,
                'train_params': opt_params,
                'test_winrate': metrics.get('win_rate', 0),
                'test_profit_factor': metrics.get('profit_factor', 1),
                'test_drawdown': metrics.get('max_dd', 0),
                'n_trades': metrics.get('n_trades', 0),
            })
            
            logger.info(f"📊 Ventana {i+1}: WinRate {metrics.get('win_rate', 0):.2%}")
        
        avg_params = DEFAULT_PARAMS.copy()
        for key in avg_params.keys():
            values = [r['train_params'].get(key, 0) for r in results]
            avg_params[key] = np.mean(values)
        
        return results, avg_params
    
    def run_monte_carlo(self, n_simulations=MONTE_CARLO_SIMULATIONS):
        """Monte Carlo Simulation sobre los trades"""
        logger.info(f"🎰 Iniciando Monte Carlo ({n_simulations} simulaciones)...")
        
        params = self.best_params or DEFAULT_PARAMS
        bt = Backtester(self.data, {'__global__': params}, INITIAL_CAPITAL)
        _, trades, equity = bt.run()
        
        if trades.empty:
            logger.warning("⚠️ No hay trades para simular")
            return {}
        
        pnls = trades['pnl'].values
        initial_capital = INITIAL_CAPITAL
        
        final_capitals = []
        max_drawdowns = []
        
        for _ in range(n_simulations):
            sampled = np.random.choice(pnls, size=len(pnls), replace=True)
            cap = initial_capital
            peak = initial_capital
            max_dd = 0
            
            for pnl in sampled:
                cap += pnl
                if cap > peak:
                    peak = cap
                dd = (peak - cap) / peak if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
            
            final_capitals.append(cap)
            max_drawdowns.append(max_dd)
        
        return {
            'mean_final_capital': np.mean(final_capitals),
            'std_final_capital': np.std(final_capitals),
            'percentile_5': np.percentile(final_capitals, 5),
            'percentile_95': np.percentile(final_capitals, 95),
            'mean_max_dd': np.mean(max_drawdowns),
            'std_max_dd': np.std(max_drawdowns),
            'ruin_prob': np.mean(np.array(final_capitals) < initial_capital * 0.5),
        }
    
    def run_full_optimization(self):
        """Ejecuta el ciclo completo de optimización (100 iteraciones)"""
        logger.info("="*60)
        logger.info("🧠 INICIANDO OPTIMIZACIÓN COMPLETA (100 iteraciones)")
        logger.info("="*60)
        
        all_results = []
        
        # Fase 1: Grid Search
        grid_results = self.run_grid_search()
        all_results.extend(grid_results)
        
        # Fase 2: Random Search
        random_results = self.run_random_search(n_iterations=30)
        all_results.extend(random_results)
        
        # Fase 3: Bayesian Optimization
        bayes_results = self.run_bayesian_optimization(n_calls=30)
        if 'winrate' in bayes_results:
            all_results.append({'params': bayes_results['best_params'], 'winrate': bayes_results['winrate']})
        
        # Fase 4: Walk-Forward
        wf_results, avg_params = self.run_walk_forward()
        all_results.append({'params': avg_params, 'winrate': np.mean([r['test_winrate'] for r in wf_results])})
        
        # Fase 5: Monte Carlo
        mc_results = self.run_monte_carlo()
        
        all_results.sort(key=lambda x: x.get('winrate', 0), reverse=True)
        
        best = all_results[0]
        self._update_best(best)
        
        self._generate_report(best, wf_results, mc_results)
        
        return {
            'best_params': self.best_params,
            'best_winrate': self.best_winrate,
            'best_metrics': self.best_metrics,
            'walk_forward': wf_results,
            'monte_carlo': mc_results,
            'tracking': self.tracking,
        }
    
    # ===================== MÉTODOS AUXILIARES =====================
    
    def _evaluate_params(self, params, data=None):
        data = data or self.data
        try:
            bt = Backtester(data, {'__global__': params}, INITIAL_CAPITAL)
            _, _, _ = bt.run()
            metrics = bt.calculate_metrics()
            winrate = metrics.get('win_rate', 0)
            
            self.tracking['iterations'].append(len(self.tracking['iterations']))
            self.tracking['winrates'].append(winrate)
            self.tracking['profit_factors'].append(metrics.get('profit_factor', 1))
            self.tracking['drawdowns'].append(metrics.get('max_dd', 0))
            self.tracking['sharpe_ratios'].append(metrics.get('sharpe', 0))
            
            return winrate
        except Exception as e:
            logger.error(f"Error evaluando parámetros: {e}")
            return 0
    
    def _generate_random_params(self):
        params = DEFAULT_PARAMS.copy()
        for key, (min_val, max_val) in PARAM_RANGES.items():
            if key in params:
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[key] = np.random.randint(min_val, max_val + 1)
                else:
                    params[key] = np.random.uniform(min_val, max_val)
        return params
    
    def _run_quick_optimization(self, data):
        best_winrate = 0
        best_params = DEFAULT_PARAMS.copy()
        
        for _ in range(20):
            params = self._generate_random_params()
            winrate = self._evaluate_params(params, data)
            if winrate > best_winrate:
                best_winrate = winrate
                best_params = params
        
        return best_params
    
    def _update_best(self, result):
        winrate = result.get('winrate', 0)
        params = result.get('params', {})
        if winrate > self.best_winrate:
            self.best_winrate = winrate
            self.best_params = params
            bt = Backtester(self.data, {'__global__': params}, INITIAL_CAPITAL)
            _, _, _ = bt.run()
            self.best_metrics = bt.calculate_metrics()
            logger.info(f"🎯 NUEVO MEJOR WinRate: {winrate:.2%} con params: {params}")
    
    def _generate_report(self, best, wf_results, mc_results):
        report = {
            'timestamp': datetime.now().isoformat(),
            'best_params': self.best_params,
            'best_winrate': self.best_winrate,
            'best_metrics': self.best_metrics,
            'walk_forward': wf_results,
            'monte_carlo': mc_results,
            'tracking': self.tracking,
        }
        
        filename = os.path.join(RESULTS_DIR, f'optimization_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Informe guardado en {filename}")
        
        print("\n" + "="*60)
        print("📊 RESUMEN DE OPTIMIZACIÓN")
        print("="*60)
        print(f"Mejor WinRate: {self.best_winrate:.2%}")
        print(f"Mejor Profit Factor: {self.best_metrics.get('profit_factor', 0):.2f}")
        print(f"Mejor Drawdown: {self.best_metrics.get('max_dd', 0):.2%}")
        print(f"Mejor Sharpe: {self.best_metrics.get('sharpe', 0):.2f}")
        print(f"N° Trades: {self.best_metrics.get('n_trades', 0)}")
        print(f"\nParámetros óptimos:")
        for key, val in self.best_params.items():
            if isinstance(val, float):
                print(f"  {key}: {val:.4f}")
            else:
                print(f"  {key}: {val}")
        print("\nWalk-Forward resultados:")
        for r in wf_results:
            print(f"  Ventana {r['window']}: WinRate {r['test_winrate']:.2%}, Trades {r['n_trades']}")
        print(f"\nMonte Carlo (1000 sims):")
        print(f"  Capital final medio: ${mc_results.get('mean_final_capital', 0):.2f}")
        print(f"  Probabilidad de ruina: {mc_results.get('ruin_prob', 0):.2%}")
        print("="*60)


def run_complete_optimization(symbols=None, data_dict=None):
    """
    Función principal para ejecutar el laboratorio completo
    """
    logger.info("🧠 INICIANDO LABORATORIO DE OPTIMIZACIÓN JUNK TOYS v6.0")
    
    if data_dict is None:
        de = DataEngine()
        if symbols is None:
            symbols = de.get_common_pairs(max_pairs=50)
        
        data_dict = {}
        logger.info(f"📥 Descargando datos para {len(symbols)} activos...")
        for sym in symbols[:20]:
            df = de.fetch_historical(sym, days=180)
            if df is not None and not df.empty:
                data_dict[sym] = df
    
    if not data_dict:
        logger.error("❌ No se pudieron descargar datos")
        return None
    
    lab = OptimizationLab(list(data_dict.keys()), data_dict)
    results = lab.run_full_optimization()
    
    return results
