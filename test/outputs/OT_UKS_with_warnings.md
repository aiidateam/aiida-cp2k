# OT UKS output with non-numeric lines in eigenvalue blocks

`OT_UKS_with_warnings.out` is an excerpt of a CP2K 2024.3 GPU run from
June 22, 2026 (UKS, OT, multiplicity 2, 20 and 19 electrons). Only the
version, DFT type, initial electron counts, and the final MO/energy output
group are retained; trailing whitespace is removed. Numerical values and
line order are unchanged.

Several lines were inserted by hand, including the two containing
`synthetic`, to check that non-numeric lines inside occupied and unoccupied
blocks do not end eigenvalue parsing. `Skipping GPU init` is native
GPU-build output.
