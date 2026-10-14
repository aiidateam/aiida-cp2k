# OT output at successive geometry steps

`OT_RKS_multiple_steps.out` and `OT_UKS_multiple_steps.out` contain native
CP2K 2023.1 output excerpts captured on October 14, 2026. Only the version,
DFT type, initial electron counts, and three successive MO/energy output
groups are retained; trailing whitespace is removed. Numerical values and
the order of occupied blocks, unoccupied blocks, and printed gaps are unchanged.

The RKS run used H2 at `(4, 4, 3.4)` and `(4, 4, 4.6)` Å. The UKS run used
H3 at `(4, 4, 2.8)`, `(4, 4, 4.0)`, and `(4, 4, 5.2)` Å, multiplicity 2,
so the two spin channels have distinct gaps and electron counts.

Both used an 8 Å cubic nonperiodic cell, GPW/PBE, DZVP-MOLOPT-SR-GTH basis
sets, GTH-PBE-q1 potentials, a 200 Ry cutoff, the MT Poisson solver, OT/DIIS
with `FULL_SINGLE_INVERSE`, `EPS_SCF 1e-7`, and an atomic SCF guess.
`GEO_OPT/BFGS` was deliberately limited to two iterations. All three SCFs
(initial geometry and the two subsequent steps) converged in each run.
`DFT/PRINT/MO_CUBES` was explicitly enabled with `NHOMO 1`, `NLUMO 1`,
`WRITE_CUBE F`, and `EACH/GEO_OPT 1`.

These are parser regression fixtures, not converged geometry benchmarks.
Tests also truncate the final group to represent interrupted output without
inventing eigenvalues or gap values.
