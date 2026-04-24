# SUCCESS_REPORT.md

## The Algorithm
I utilized the Latin Hypercube Search algorithm provided in the baseline model. I modified it to allow it to evaluate models quicker by lowering the strictness in SciPy's ODE solver (`solve_ivp`). Additionally, I set a 1 second per integration limit to stop evaluations hanging.

## The Winning Array
```python
[3.71543859e-02, 7.26591876e-02, 7.51024030e-02, 4.76396961e-03, 4.29076101e-03, 1.01346809e-03, 8.77486101e-02, 7.48968474e-01, 1.19776162e+02, 2.05400589e-02, 5.11642158e-02, 4.48468124e-02, 1.99308975e+00, 1.43736634e+01, 3.80688680e-01, 1.65088449e-02]
```