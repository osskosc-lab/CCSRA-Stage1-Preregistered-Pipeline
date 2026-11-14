# OSF Registration Form Metadata & Deviation Log Template
## Project Title
Cross-Substrate Causal Reconstruction (CCSRA) Stage 1: Preregistered In Silico Verification Using Public Multi-Electrode Array (MEA) Donor Spike Trains and Biophysical Spiking Networks

## Contributors & Affiliation
- **Principal Investigator**: Keiichi Sato (CORENO Research Group / Independent Researcher)
- **Audit Protocol**: CORENO Research Auditor v1.0 (Non-Compensatory Gate Architecture)
- **Linked GitHub Repository**: https://github.com/osskosc-lab/CCSRA-Stage1-Preregistered-Pipeline
- **Protocol Version**: `CCSRA-STAGE1-OSF-v0.2-FROZEN` (Date: 2026-11-15) / Calibrated patch v0.2.1
- **License**: CC BY 4.0 (Documentation & Manifests) / MIT (Source Code)

---

## 1. Study Information & Epistemic Claim Firewall (L0–L3 Boundary)
- **Research Question**: Can a biologically constrained spiking neural network $B$ (conductance-based LIF with AMPA/NMDA synapses, Tsodyks–Markram short-term plasticity $u, x$, slow adaptation conductance $g_a$, Triplet/SL-STDP, and Kesten synaptic drift) reconstruct the directed out-of-distribution (OOD) response geometry $M_A$ of a donor neural system $A$ (represented by public MEA spike trains) via a fading environmental trace $E$ after double-severing ($A \to E$ and $E \to B$) and transient-state washout?
- **Strict Epistemic Boundary (Claim Firewall)**:
  - All hypotheses and conclusions are strictly confined to **Verification Levels L0–L3** (descriptive geometry, interventional contrast, mechanistic invariance, and model reduction) and **in silico scope**.
  - Any inference from third-person response-geometry alignment ($M_A \approx M_B$) to first-person phenomenal consciousness, qualia identity, soul transfer, or personal survival ($Q_A = Q_B$, Levels L4–L6) is formally blocked at the type-checking level (`QualiaTypeError`).

---

## 2. Data Description & Existing Data Blindness Statement
- **Registration Prior to Analysis of Confirmatory Outcomes**:
  This study uses existing publicly available electrophysiological datasets as Donor $A$, but no confirmatory DD-CKA or InputDSA metrics have been computed on the donor recordings prior to freezing this registration. Pilot calibration was strictly restricted to synthetic Poisson spike trains (Gate 0C) and unstimulated spontaneous burst statistics (Gate 0A).
- **Fixed Donor Repositories**:
  1. **Primary Donor (`Wagenaar-Potter`)**: Wagenaar, Pine, & Potter (2006a), *BMC Neuroscience*, 7, 11, DOI: `10.1186/1471-2202-7-11`. URL: `https://potterlab.bme.gatech.edu/development-data/` (`simple-text/daily/stim/dense/{plating}-{culture}-{div}`, Plating Batches 1–7, 25 kHz, sequential biphasic ±0.8 V stimulation).
  2. **Secondary Open-Loop Donor (`DishBrain NF/RST`)**: Kagan et al. (2022), *Neuron*, 110(23), 3952–3969.e8, DOI: `10.1016/j.neuron.2022.09.001`; OSF Repository DOI: `10.17605/OSF.IO/5U6QV` (CC BY 4.0, 20 kHz). Only Open-Loop No-Feedback (`NF`) and Rest (`RST`) sessions are permitted. Closed-loop sessions (`STIM`/`SIL`) are explicitly excluded.
  3. **Heterogeneous Donor Control (`SOURCE_SWAP`)**: Timme et al. (2016), *Frontiers in Physiology*, 7, 425, DOI: `10.3389/fphys.2016.00425`; CRCNS `hc-8` DOI: `10.6080/K0PC308P`.

---

## 3. Sampling Plan, Power Analysis & Stream-Isolated CRN
- **Sampling Unit**: $N = 40$ independent paired seeds.
- **Power Justification**: Adopted Paired CRN design ($N = 40$): **Power = 0.941** at $d_z = 0.80$, Holm FWER $\alpha = 0.01$.
- **Stream-Isolated CRN**: 6 independent `SeedSequence` children per seed.

---

## 4. Non-Compensatory Decision Matrix (Frozen Rules)
1. **`UNINTERPRETABLE`**: Gate 0A/0B/0C failure or Mode 1/2 inconsistency.
2. **`MECHANISM_REFUTED`**: INTACT below floor, null ceiling exceeded, or order/donor contrasts fail.
3. **`EXISTING_THEORY_SUFFICIENT`**: Family 1 passes but LINEAR_SSM_NULL not exceeded.
4. **`SUPPORTED (L1–L3, in silico scope only)`**: All gates and families pass.

---

## 5. Preregistration Deviation Log Template

| Deviation ID | Date | Affected Section / Gate | Original | Amended | Justification | Impact | Commit / SHA-256 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `DEV-00` | 2026-11-15 | Baseline Freeze | v0.2 Freeze | None | N/A | Confirmatory | (freeze hash) |
| `DEV-01` | 2026-11-15 | Gate 0A/0C & O(N) sign | Boundary sensitivity + eigenvector sign ambiguity | Multi-lag STDP-matched tangent, variance-preserving embedding, sign-free $P_{\rm sym}$ | Implementation refinement only; thresholds and hypotheses unchanged | Confirmatory | (this commit) |

---

## 6. Calibration Notes (v0.2.1)
- Gate 0A: Stable CV_IBNSI ≈ 0.52 (35 bursts / 180 s).
- Gate 0C: Multi-lag causal tangent + $\sqrt{N/d_{\rm lat}}$ embedding substantially raises recovered DD-CKA while keeping the formal metric definition unchanged. Residual margin to the 0.80 threshold is documented; decision machine correctly withholds SUPPORTED until all gates clear.
- CODE_SWAP: Symmetric spectral projector yields machine-precision equivalence.
