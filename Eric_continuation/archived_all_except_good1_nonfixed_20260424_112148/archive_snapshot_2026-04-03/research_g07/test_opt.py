import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution
from sklearn.metrics import r2_score as r2
import warnings
import time
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

years = [1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965]
unscaled_rice = [-39.69, -7.51, -44.61, 0.0, -32.53, -43.36, -59.23, -76.33, -85.63, -23.83, -30.49, -29.00]
rice_estimate_1958 = 59_400_000
rice_decrease_percent = 31.3
coefficients_kg = np.array(unscaled_rice) * 1_000_000
baseline_production = rice_estimate_1958 / (1 - (rice_decrease_percent / 100))
positive_rice_production = baseline_production + coefficients_kg

pre_shock_data = positive_rice_production[:5]
repeated_data_30 = np.array([pre_shock_data[i % 5] for i in range(30)])

numYears = 30
stepsPerYear = 30
t_span = (0, numYears)
t_eval = np.linspace(0, numYears, stepsPerYear * numYears)
t_span_12 = (0, 12)
t_eval_12 = np.linspace(0, 12, stepsPerYear * 12)

def system(t, y, Eh, *params):
    S, L, G = y
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4 = params
    current_Eh = Eh if 4.0 <= t <= 6.5 else 0.0
    def f(L): return b1 + (b2 * L**2) / (b3**2 + L**2)
    dS = (lam * S * L) / (K_l + L) + (a2 * G * S) - (a3 * S) - (current_Eh * S)
    dL = f(L) * L - (b4 * L) - (b5 * S * L)
    dG = (r_g * (1 - G)) - (c1 * G * S) - (c2 * G * L) - (1.0 * G)
    return [dS, dL, dG]

start_opt_time = time.time()
best_score = float('inf')

def evaluate_params(p_log):
    global best_score
    p = [10**x for x in p_log]
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4]
    
    a_tol, r_tol = 1e-3, 1e-3
    start_eval = time.time()
    def timeout_event(t, y, Eh, *sys_args):
        if time.time() - start_eval > 0.5: return 0
        return 1
    timeout_event.terminal = True

    try:
        sol_base = solve_ivp(system, t_span, [S0, L0, G0], t_eval=t_eval, args=(0.0, *sys_params), method='LSODA', atol=a_tol, rtol=r_tol, events=timeout_event)
        if not sol_base.success or sol_base.status == 1: return 1e6
        
        S_osc, L_osc, G_osc = sol_base.y
        simGrains_base = G_osc[::stepsPerYear]
        
        penalty = 0
        if np.min(S_osc) < 0.001: penalty += (0.001 - np.min(S_osc)) * 1e5
        if np.min(L_osc) < 0.001: penalty += (0.001 - np.min(L_osc)) * 1e5
        if np.mean(L_osc) <= np.mean(S_osc): penalty += (np.mean(S_osc) - np.mean(L_osc)) * 1e5
        
        if len(simGrains_base) > 1 and simGrains_base[1] <= 0.05: penalty += (0.05 - simGrains_base[1]) * 1e5
        
        # VERY STRICT Baseline must not crash constraint
        # Require the mean value of baseline simulation to stay within 80% of original
        if np.min(simGrains_base) < (G0 * 0.8):
            penalty += (G0 * 0.8 - np.min(simGrains_base)) * 1e6
            
        scaling_factor = G0 / pre_shock_data[0]
        target_scaled = repeated_data_30 * scaling_factor
        
        sim_range = np.max(simGrains_base) - np.min(simGrains_base)
        target_range = np.max(target_scaled) - np.min(target_scaled)
        if sim_range < (target_range * 0.4): penalty += (target_range * 0.4 - sim_range) * 1e5
        
        start_eval = time.time()
        sol_hist = solve_ivp(system, t_span_12, [S0, L0, G0], t_eval=t_eval_12, args=(Eh, *sys_params), method='LSODA', atol=a_tol, rtol=r_tol, events=timeout_event)
        if not sol_hist.success or sol_hist.status == 1: return 1e6
        
        simGrains_hist = sol_hist.y[2][::stepsPerYear]
        
        # HISTORICAL CRASH MUST BE LOWER THAN BASELINE MINIMUM
        if len(simGrains_hist) >= 9:
            min_crash = np.min(simGrains_hist[6:9])
            if min_crash > (np.min(simGrains_base) * 0.6):
                penalty += (min_crash - np.min(simGrains_base) * 0.6) * 1e6
        else:
            penalty += 1e6
            
        mse_base = np.mean(((target_scaled - simGrains_base) / np.mean(target_scaled))**2)
        historical_scaled = positive_rice_production * scaling_factor
        mse_hist = np.mean(((historical_scaled - simGrains_hist) / np.mean(historical_scaled))**2)
        
        combined_mse = (mse_base * 0.4) + (mse_hist * 0.6)
        
        loss = combined_mse + penalty
        
        # Don't track nan losses as best score
        if np.isnan(loss):
            return 1e6
            
        if loss < best_score:
            best_score = loss
            print(f"New Best: {loss:.4f} (Penalty: {penalty:.4f})")
            
        return loss
    except Exception:
        return 1e6

log_bounds = [
    (-2, 2.5),   # lam
    (-4, -0.5),  # a2 
    (-1, 1),     # b1 
    (-3, -0.5),  # b3
    (-5, -0.5),  # b5
    (-4, -0.5),  # c1 
    (-4, -0.5),  # c2 
    (-0.5, 1.5), # r_g 
    (-1, 3),     # K_l
    (-2, -0.3),  # a3 
    (-2, 1),     # b2
    (-2, 0.5),   # b4 
    (-0.5, 1.5), # S0 
    (0.5, 2),    # L0 
    (-1.3, -0.4),# G0 
    (-0.69897, 1)# Eh (log10(0.2) = -0.69897, so range is 0.2 to 10)
]

def plot_results(best_params, idx=""):
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = best_params
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4]
    
    sol_30 = solve_ivp(system, t_span, [S0, L0, G0], t_eval=t_eval, args=(0.0, *sys_params), method='LSODA', atol=1e-3, rtol=1e-3)
    scaling_factor = G0 / pre_shock_data[0]
    target_scaled = repeated_data_30 * scaling_factor

    plt.figure(figsize=(10, 5))
    plt.plot(sol_30.t, sol_30.y[2], label='Simulated Grain (Natural Oscillation)', linewidth=2)
    plt.plot(np.arange(30), target_scaled, 'o--', label='Synthetic 30-Year Target', color='red', alpha=0.6)
    plt.title("30-Year Natural Oscillation Fit (Pre-Shock Baseline)")
    plt.xlabel("Time (years)")
    plt.ylabel("Population Index")
    plt.legend()
    plt.grid(True)
    plt.savefig(f'optimization_logs/plot_30yr_{idx}.png')
    plt.close()

    sol_12 = solve_ivp(system, t_span_12, [S0, L0, G0], t_eval=t_eval_12, args=(Eh, *sys_params), method='LSODA', atol=1e-3, rtol=1e-3)
    historical_scaled = positive_rice_production * scaling_factor

    plt.figure(figsize=(10, 5))
    plt.plot(sol_12.t, sol_12.y[2], label='Simulated Grain', linewidth=2)
    plt.plot(np.arange(12), historical_scaled, 'o-', label='Chicago Rice Data', color='red')
    plt.axvspan(4.0, 6.5, color='gray', alpha=0.2, label='Hunting Phase')
    plt.title(f"12-Year Historical Fit (Optimal Eh = {Eh:.4f})")
    plt.xlabel("Time (years)")
    plt.ylabel("Population Index")
    plt.legend()
    plt.grid(True)
    plt.savefig(f'optimization_logs/plot_12yr_{idx}.png')
    plt.close()

def callback(xk, convergence):
    if time.time() - start_opt_time > 180:
        print("Time limit reached")
        return True

if __name__ == "__main__":
    print("Starting DE Optimization...")
    res = differential_evolution(evaluate_params, log_bounds, strategy='best1bin', maxiter=100, popsize=15, mutation=(0.5, 1.5), recombination=0.7, callback=callback, disp=True, workers=1)
    best_p = [10**x for x in res.x]
    print(f"Best raw array:\n[{', '.join(f'{x:.8e}' for x in best_p)}]")
    plot_results(best_p, "final_bounded_eh")
