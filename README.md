# sparrows_and_locusts

## Questions we want to address
1. Can we model the locust population explosion?
2. Can killing sparrows actually increase the grain you end up with?

## Variables
S(t): sparrow population
L(t): locust population
G(t): grain biomass
E_h, E_f: human effort (sparrow hunting) and farm effort (grain production), respectively

## The Mathematical Equations:
$dS/dt = a_1SL + a_2SG - a_3G - a_4E_hS$ \\
$dL/dt = h(L)L - b_4L - b_5SL$ where $h(L)$ \\
\begin{cases}
  b_1 \text{L < b_3} \\
  b_2 \text{L \geq b_3}
\end{cases}
$dG/dt = c_1E_f - c_2GS - c_3GL$


