# sparrows_and_locusts

## Questions we want to address
1. Can we model the locust population explosion?
2. Can killing sparrows actually increase the grain you end up with?

## Variables
- **S(t):** sparrow population  
- **L(t):** locust population  
- **G(t):** grain amount   
- **$E_h, E_f$:** human effort (sparrow hunting) and farm effort (grain production)

## The Mathematical Equations

### Sparrows
$\frac{dS}{dt} = a_1 S L + a_2 S G - a_3 G - a_4 E_h S$

### Locusts
$\frac{dL}{dt} = h(L)\,L - b_4 L - b_5 S L$

with a piecewise growth function  
$h(L) = 
\begin{cases}
b_1, & L < b_3 \\
b_2, & L \ge b_3
\end{cases}$

### Grain
$\frac{dG}{dt} = c_1 E_f - c_2 G S - c_3 G L$
