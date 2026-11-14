# CCSRA Stage 1 Preregistration Frozen Specification (OSF v0.2)

**Status**: FROZEN  
**Date**: 2026-11-15  
**SHA-256 of this document and the companion pipeline will be recorded in the run manifests.**

## Scope (L0–L3 only)

This stage verifies whether a biophysically grounded spiking receptor network B can recover directed dynamical geometry from open-loop public MEA donor spike trains. Claims about subjective experience, personal identity, or phenomenal qualia are category errors and are blocked at the type level.

## Gates

- **Gate 0A**: Spontaneous burst statistics (CV of IBNSI ≈ 0.5) with STDP and Kesten disabled.
- **Gate 0B**: After T_wash = 60 s natural relaxation, relative L2 residual of (u, x, g_a) < 0.001; SEVER arm records pure Kesten drift.
- **Gate 0C**: Synthetic known orthogonal directed structure recovered by Poisson-debiased DD-CKA ≥ 0.80; shuffled ≤ 0.10.

## Arms & Surrogates

INTACT + 7 Family-1 controls + LINEAR_SSM_NULL + CODE_SWAP.  
Uniform dither is prohibited. JISI-D (20 ms), TR_SHIFT, and commutative Gaussian LINEAR_SSM_NULL are implemented.  
Closed-loop DishBrain conditions raise an immediate exception.

## Statistics

Paired CRN N=40. Holm FWER α=0.01 on 7 contrasts. TOST equivalence margin ±0.05 for CODE_SWAP. Decision is produced solely from empirical statistics (UNINTERPRETABLE / MECHANISM_REFUTED / EXISTING_THEORY_SUFFICIENT / SUPPORTED).

## Implementation

The companion script `ccsra_stage1_preregistered_pipeline.py` is the executable embodiment of this specification.
