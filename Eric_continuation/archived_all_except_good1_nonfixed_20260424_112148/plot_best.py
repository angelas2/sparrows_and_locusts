import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

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

best_params = [5.48537843e+01, 7.70110678e-02, 4.39172682e+00, 2.17514993e-02, 1.89531946e-02, 5.33341562e-03, 9.46204101e-03, 3.39770045e-01, 4.38657381e+01, 2.83911328e-01, 1.17968266e-01, 1.81316777e-02, 2.50137221e+00, 5.42606533e+00, 1.65543350e-01, 1.40885470e-03]
plot_results(best_params, "de_check2")
