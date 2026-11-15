# CCSRA Stage 1 Preregistered Verification Pipeline

**Protocol**: CCSRA-STAGE1-OSF-v0.2-FROZEN  
**Date**: 2026-11-15  
**Author**: K. Sato / CORENO Research Group  

This repository contains the frozen, self-auditing Python implementation of the CCSRA Stage 1 preregistration. It enforces the epistemic claim firewall (L0–L3 only), stream-isolated Common Random Numbers, Gate 0A/0B/0C, surrogate rules, and the non-compensatory decision state machine.

## Key Revisions (thresholds unchanged)

- Static \((I - P_U)\) projection applied only to the temporal mean (preserves autonomous flow)
- Sign-free polar / fractional-power sensory frame (eliminates eigenvector sign ambiguity)
- Gate 0A irregular-burst nucleation dynamics calibrated to \(\mathrm{CV_{IBNSI}} \approx 0.5\)

## Quick Start

```bash
pip install -r requirements.txt
python ccsra_stage1_preregistered_pipeline.py --n-seeds 4 --out-json test_manifest.json
```

For the full confirmatory analysis (N=40):

```bash
python ccsra_stage1_preregistered_pipeline.py --n-seeds 40 --t-wash 60.0 --bin-ms 5.0 --out-json manifest_main.json
```

## Donor Connection Tests

```bash
python ccsra_stage1_donor_connection_tests.py
```

This suite verifies:

- Wagenaar et al. (2006) simple-text loaders (daily / stim / dense)
- DishBrain open-loop NF & RST (closed-loop STIM/SIL/PONG blocked)
- CRCNS hc-8 SOURCE_SWAP
- JISI-D / TR-SHIFT surrogates
- Qualia firewall
- Brian2 equation port

## Real Donor Data

The loaders `load_wagenaar_simple_text`, `load_dishbrain_open_loop`, and `load_crcns_hc8_simple` are ready for public MEA files.

Closed-loop data is explicitly blocked.

## Claim Firewall

Instantiating `Qualia()` raises `QualiaTypeError`. Geometric alignment of representations does not license claims about subjective identity.

## Outputs

Each run produces a SHA-256-hashed JSON manifest containing Gates, all arm statistics, Holm-corrected contrasts, TOST equivalence, and the final verdict.

## Notes on the Reference Implementation

The confirmatory engine uses a biophysically motivated mean-field proxy that preserves the mathematical invariants required by the preregistration (O(N) invariance under CODE_SWAP, chirality sensitivity under time-reversal, washout residual, stream-isolated CRN). Gate 0A/0C parameters in the proxy may require light calibration to the exact target statistics; the decision state machine correctly returns UNINTERPRETABLE when gates fail. Real MEA loaders are fully implemented and will raise on closed-loop conditions.
