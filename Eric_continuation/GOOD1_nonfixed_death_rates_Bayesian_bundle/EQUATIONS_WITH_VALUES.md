# Famine ODE — equations with good #1 **non-fixed** death rates (numeric substitution)

Point values are from `checkpoint.json` (`params_lin`): **\(a_3 = 0.3901147113671109\)**, **\(b_4 = 0.8009464632919426\)** (not \(\tfrac13\) / not \(1\)).

State: **S** (sparrows), **L** (locusts), **G** (grain index).  
Hunting: \(E_h(t) = E_h\) on \(4 \le t \le 6.5\) years, else \(0\).

---

## Locust growth function

\[
f(L) = b_1 + \frac{b_2 L^2}{b_3^2 + L^2}
\]

Numerically:

\[
f(L) = 1.6361140469 + \frac{1.1094748633\, L^2}{0.000126067 + L^2}
\]

---

## ODEs with all coefficients substituted

\[
\begin{aligned}
\frac{\mathrm{d}S}{\mathrm{d}t}
&= \frac{3.2191787879\, S L}{172.2474497928 + L}
 + 0.0707532312\, G S
 - 0.3901147114\, S
 - E_h(t)\, S, \\[0.4em]
\frac{\mathrm{d}L}{\mathrm{d}t}
&= f(L)\,L - 0.8009464633\, L - 0.1791096293\, S L, \\[0.4em]
\frac{\mathrm{d}G}{\mathrm{d}t}
&= 1.8301843871\,(1-G) - 0.0009729512\, G S - 0.0310084835\, G L - G.
\end{aligned}
\]

### Coefficient table (good #1, non-fixed \(a_3,b_4\))

| Symbol | Value |
|--------|------:|
| \(\lambda\) | 3.2191787879 |
| \(a_2\) | 0.0707532312 |
| \(b_1\) | 1.6361140469 |
| \(b_3\) | 0.0112279724 |
| \(b_5\) | 0.1791096293 |
| \(c_1\) | 0.0009729512 |
| \(c_2\) | 0.0310084835 |
| \(r_g\) | 1.8301843871 |
| \(K_\ell\) | 172.2474497928 |
| \(a_3\) | **0.3901147114** |
| \(b_2\) | 1.1094748633 |
| \(b_4\) | **0.8009464633** |
| \(E_h\) | 1.7572075170 |

---

## Initial conditions (\(t=0\))

| State | Value |
|-------|------:|
| \(S(0)\) | 13.1752278667 |
| \(L(0)\) | 28.2478797501 |
| \(G(0)\) | 0.4240653352 |

---

## Observations for Bayesian grain likelihood

Annual Chicago rice \(R_k\) scaled to grain index:

\[
\text{scale} = \frac{G(0)}{R_{\text{pre}}[0]}, \qquad y_k = R_k \cdot \text{scale}, \quad k=0,\ldots,11
\]

using `famine_model.pre_shock_data[0]` and `famine_model.positive_rice_production[k]`.

---

## Bayesian UQ

See **`bayesian_uq_mcmc.py`**: \(16\times \log_{10}\) parameters (including **\(a_3,b_4\)**) + \(\log_{10}\sigma\); Gaussian priors centered on checkpoint `params_log`; Gaussian likelihood on normalized annual grain; `emcee` ensemble MCMC; **`mcmc_uq_traces.png`** = trace for **all** continuous unknowns; corner subset on \(a_3,b_4,\sigma\); PPC grain (`mcmc_uq_*`).
