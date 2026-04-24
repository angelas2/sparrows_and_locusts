# LLM Protocol: Transitioning from Point Estimates to Bayesian UQ for ODE Systems

## 1. Objective
This document provides a structured prompt template to feed into a Large Language Model (LLM) when you want it to perform Bayesian Uncertainty Quantification (UQ) on an Ordinary Differential Equation (ODE) system where the baseline parameters have already been identified (e.g., via solver-based optimization or Latin Hypercube Sampling).

## 2. Theoretical Context: Statistical Analysis of ODEs
Because the primary goal is rigorous statistical analysis and mechanistic modeling (rather than just building software), the LLM must be explicitly instructed to focus on statistical validity. This means defining sensible priors around the existing point estimates, properly formulating a likelihood function that interfaces with an ODE solver, and mapping the full posterior landscape to understand parameter identifiability and correlation.

## 3. The LLM Prompt Template
Copy and paste the framework below into the LLM, filling in your specific model details in the bracketed sections.

---
**[START OF PROMPT TEMPLATE]**

**Role:** You are an expert computational statistician specializing in Bayesian inference and mechanistic modeling. 

**Task:** I have a system of ODEs where I have already found the optimal point estimates for the parameters using standard optimization techniques. I now need to perform Bayesian Uncertainty Quantification (UQ) to extract the posterior distributions of these parameters given my historical data.

**1. The ODE System:**
Here is the mathematical model. *(Insert your model here, for example, a multi-variable system tracking interacting population dynamics like Sparrows (S), Locusts (L), and Grain (G) biomass over time).*
[Insert Mathematical Equations or Python ODE function here]

**2. The Known Parameter Estimates:**
I have already identified the following optimal point estimates. You must use these as the initialization points for the Markov Chain Monte Carlo (MCMC) walkers, and center the priors around these values.
[Insert Parameters, e.g., baseline predation rate, intrinsic growth rate, etc.]

**3. The Data:**
[Provide the historical data structure. e.g., "I have 60 days of historical data for Locusts and Grain, but Sparrow populations are unobserved." Provide the array of time points ($t$) and observed values ($y$)].

**4. Bayesian Implementation Requirements:**
Please write the statistical modeling code (using Python, specifically `emcee` combined with `scipy.integrate.odeint` or `solve_ivp`) following these strict steps:
* **Priors:** Define weakly informative Normal or Log-Normal priors centered on my provided point estimates.
* **Likelihood:** Construct a Gaussian likelihood function. The predicted mean should be the output of the ODE solver at the observed time points. Include an unknown noise parameter $\sigma$ to be estimated alongside the ODE parameters.
* **Sampling:** Set up the MCMC sampler. Initialize the walkers in a tight n-dimensional ball around my point estimates to ensure fast convergence.
* **UQ Visualization:** Generate code to plot the **Trace plots** (to check chain mixing) and a **Corner plot** (to visualize parameter correlations and marginal posteriors). 
* **Posterior Predictive Check:** Generate code to sample from the posterior and plot the 95% credible intervals (the uncertainty bands) overlaid on the original source data.

**[END OF PROMPT TEMPLATE]**
---

## 4. Execution Notes
* **Solver Bottlenecks:** ODE solvers within MCMC loops are computationally expensive. The LLM should be instructed to keep the `rtol` and `atol` tolerances of the solver reasonable to prevent infinite integration times in stiff regions of the parameter space.
* **Code Structure:** Be sure to tell the LLM whether you want it to output just the isolated mathematical functions (e.g., `log_prior`, `log_likelihood`, `log_posterior`) or the entire executable script from imports to plotting.
