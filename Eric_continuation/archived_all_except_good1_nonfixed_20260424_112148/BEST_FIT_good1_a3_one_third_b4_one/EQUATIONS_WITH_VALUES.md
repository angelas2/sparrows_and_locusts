# Famine ODE — equations with best-fit parameter values

State: **S** (sparrows), **L** (locusts), **G** (grain index, 0–1 scale).  
Hunting effort on sparrows: \(E_h(t) = E_h\) if \(4 \le t \le 6.5\) years, else \(0\).

Fixed death rates (literature / model constraint): \(a_3 = \tfrac{1}{3}\), \(b_4 = 1\).  
Grain linear closure coefficient is fixed at **1** on \(G\) in \(\mathrm{d}G/\mathrm{d}t\).

---

## Functional form

\[
f(L) \;=\; b_1 + \frac{b_2 L^2}{b_3^2 + L^2}
\]

With **\(b_1 = 1.6361140469\)**, **\(b_2 = 1.1094748633\)**, **\(b_3 = 0.01122797245\)**:

\[
f(L) \;=\; 1.6361140469 + \frac{1.1094748633\, L^2}{0.000126067 + L^2}
\]

---

## ODEs (substituted constants)

\[
\begin{aligned}
\frac{\mathrm{d}S}{\mathrm{d}t}
&= \frac{\lambda S L}{K_\ell + L} + a_2 G S - \tfrac{1}{3}\,S - E_h(t)\,S \\[0.35em]
\frac{\mathrm{d}L}{\mathrm{d}t}
&= f(L)\,L - 1\cdot L - b_5 S L \\[0.35em]
\frac{\mathrm{d}G}{\mathrm{d}t}
&= r_g(1-G) - c_1 G S - c_2 G L - G
\end{aligned}
\]

### Coefficients (numeric)

| Symbol | Value |
|--------|------:|
| \(\lambda\) | 3.2191787879 |
| \(a_2\) | 0.0707532312 |
| \(b_5\) | 0.1791096293 |
| \(c_1\) | 0.0009729512 |
| \(c_2\) | 0.0310084835 |
| \(r_g\) | 1.8301843871 |
| \(K_\ell\) | 172.2474497928 |
| \(E_h\) (constant during hunt window) | 1.7572075170 |

So explicitly,

\[
\begin{aligned}
\frac{\mathrm{d}S}{\mathrm{d}t}
&= \frac{3.2191787879\, S L}{172.2474497928 + L}
 + 0.0707532312\, G S
 - \tfrac{1}{3}\,S - E_h(t)\,S, \\[0.35em]
\frac{\mathrm{d}L}{\mathrm{d}t}
&= f(L)\,L - L - 0.1791096293\, S L, \\[0.35em]
\frac{\mathrm{d}G}{\mathrm{d}t}
&= 1.8301843871\,(1-G) - 0.0009729512\, G S - 0.0310084835\, G L - G.
\end{aligned}
\]

---

## Initial conditions ( \(t=0\) )

| State | Value |
|-------|------:|
| \(S(0)\) | 13.1752278667 |
| \(L(0)\) | 28.2478797501 |
| \(G(0)\) | 0.4240653352 |

---

## Historical grain observation model (Bayesian script)

Annual Chicago rice trajectory \(R_k\) (kg) is scaled to the simulation’s grain index using pre-shock alignment:

\[
\text{scale} = \frac{G(0)}{R_{\text{pre}}[0]}, \qquad
y_k = R_k \times \text{scale}, \quad k=0,\ldots,11
\]

where \(R_{\text{pre}}[0]\) is the first pre-shock synthetic baseline entry from `famine_model.pre_shock_data[0]`, and \(R_k\) are `famine_model.positive_rice_production[k]`.

The MCMC likelihood compares **simulated** \(G(t)\) (interpolated at \(t=k\)) to \(y_k\) with Gaussian noise \(\sigma\) on a **normalized** scale (see `bayesian_uq_mcmc.py`).

---

## Bayesian UQ (protocol `LLM_Bayesian_UQ_ODE_Protocol.md`)

Executable: **`bayesian_uq_mcmc.py`** (repo root: `./venv/bin/python BEST_FIT_good1_a3_one_third_b4_one/bayesian_uq_mcmc.py`).

Outputs in this folder (prefix `mcmc_uq_`):

- `mcmc_uq_chain_flat.npy` — flattened posterior samples \((N,15)\): 14×\(\log_{10}\) dynamic parameters + \(\log_{10}\sigma\).
- `mcmc_uq_traces.png` — trace plots (subset of parameters + noise).
- `mcmc_uq_corner_subset.png` — corner plot for a parameter subset + \(\sigma\).
- `mcmc_uq_ppc_grain.png` — posterior predictive bands vs scaled grain observations.
- `mcmc_uq_run_summary.json` — sampler settings and mean acceptance rate.

Priors: independent Gaussians on \(\log_{10}\) parameters centered at `best_fit.json` → `params_log_14` with scale `0.14`; Gaussian on \(\log_{10}\sigma\) centered at `-1.55`. Likelihood: i.i.d. Gaussian on normalized annual grain. **Short chain** (exploratory); extend `NSTEPS` / `NWALKERS` in the script for production UQ.
