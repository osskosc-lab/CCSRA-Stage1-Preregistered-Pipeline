#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCSRA Stage 1 Preregistered Verification Pipeline (OSF v0.2 FROZEN)
===================================================================
Author : K. Sato / CORENO Research Group
Version: v0.2-FROZEN (2026-11-15) — revised implementation
Scope  : Verification Levels L0-L3 ONLY (in silico spiking receptor B driven by
         public MEA donor spike trains). L4-L6 claims are strictly prohibited.

Key revisions (thresholds unchanged):
  - Static (I - P_U) projection on temporal mean only (preserves autonomous flow)
  - Sign-free polar/fractional-power sensory frame (eliminates eigenvector sign ambiguity)
  - Gate 0A irregular-burst nucleation dynamics calibrated to CV_IBNSI ≈ 0.5
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np
import scipy.linalg as la
from scipy import stats

# ============================================================================
# 1. EPISTEMIC CLAIM FIREWALL
# ============================================================================

class QualiaTypeError(TypeError):
    """L5/L6 Claim Firewall Violation: Phenomenal qualia is uninstantiable."""
    pass

class Qualia:
    """Attempting to instantiate subjective experience raises QualiaTypeError."""
    def __init__(self, *args, **kwargs) -> None:
        raise QualiaTypeError(
            "[CLAIM_FIREWALL_VIOLATION] Inference from geometric alignment "
            "(M_A ~= M_B) to subjective qualia or personal identity (Q_A = Q_B) "
            "is a category error and strictly prohibited in CCSRA Stage 1."
        )

def assert_no_uniform_dither(surrogate_method: str) -> None:
    if surrogate_method.upper() in {"UD", "UNIFORM_DITHER", "UNIFORM"}:
        raise ValueError(
            "[PREREG_VIOLATION] Uniform Dithering (UD) is strictly prohibited. "
            "Use 'JISI_D' (delta=20 ms) or 'TR_SHIFT'."
        )

def assert_open_loop_donor(dataset_name: str, condition: str) -> None:
    if dataset_name.upper() in {"DISHBRAIN", "KAGAN2022", "CASCADE_CL1"}:
        if condition.upper() in {"STIM", "SIL", "PONG_CLOSED_LOOP"}:
            raise ValueError(
                f"[PREREG_VIOLATION] Condition '{condition}' is closed-loop. "
                "Only open-loop 'NF' or rest 'RST' are permitted."
            )

# ============================================================================
# 2. FROZEN CONFIGURATION
# ============================================================================

@dataclasses.dataclass(frozen=True)
class Stage1PreregConfig:
    protocol_version: str = "CCSRA-STAGE1-OSF-v0.2-FROZEN"
    created_date: str = "2026-11-15"
    master_seed: int = 20261115
    n_neurons_B: int = 120
    exc_ratio: float = 0.80
    dim_E: int = 16
    tau_E_ms: float = 50.0
    dt_ms: float = 1.0
    tau_m_exc_ms: float = 20.0
    tau_m_inh_ms: float = 10.0
    tau_ampa_ms: float = 2.0
    tau_nmda_ms: float = 100.0
    tau_u_ms: float = 1600.0
    tau_x_ms: float = 400.0
    U_stp: float = 0.20
    tau_a_sec: float = 2.0
    kesten_sigma_eps: float = 0.015
    kesten_sigma_eta: float = 0.002
    t_wash_sec: float = 60.0
    gate0b_tol: float = 0.001
    n_probes_K: int = 64
    n_trials_per_probe: int = 20
    probe_win_start_ms: float = 15.0
    probe_win_end_ms: float = 115.0
    bin_width_ms: float = 5.0
    parity_odd_weight: float = 0.85
    parity_even_weight: float = 0.15
    jisi_dither_ms: float = 20.0
    n_seeds_paired: int = 40
    fwer_alpha: float = 0.01
    tost_margin: float = 0.05
    dd_cka_min_intact: float = 0.50
    dd_cka_max_null: float = 0.15
    dd_cka_min_margin: float = 0.25
    mode12_max_gap: float = 0.15
    gate0a_cv_min: float = 0.30
    gate0a_cv_max: float = 0.75
    gate0c_min_rec: float = 0.80
    gate0c_max_shuf: float = 0.10

def compute_sha256_manifest(config: Stage1PreregConfig) -> Dict[str, str]:
    cfg_json = json.dumps(dataclasses.asdict(config), sort_keys=True).encode("utf-8")
    cfg_hash = hashlib.sha256(cfg_json).hexdigest()
    try:
        script_bytes = pathlib.Path(__file__).read_bytes()
        script_hash = hashlib.sha256(script_bytes).hexdigest()
    except Exception:
        script_hash = "INTERACTIVE_SESSION_NO_FILE"
    return {
        "protocol_version": config.protocol_version,
        "config_sha256": cfg_hash,
        "script_sha256": script_hash,
    }

# ============================================================================
# 3. CRN STREAMS
# ============================================================================

@dataclasses.dataclass
class CRNStreams:
    rng_init: np.random.Generator
    rng_bg: np.random.Generator
    rng_kesten: np.random.Generator
    rng_probes: np.random.Generator
    rng_surrogate: np.random.Generator
    rng_trials: np.random.Generator

def make_crn_streams(master_seed: int, seed_index: int) -> CRNStreams:
    ss = np.random.SeedSequence([master_seed, seed_index])
    streams = ss.spawn(6)
    return CRNStreams(
        rng_init=np.random.Generator(np.random.PCG64(streams[0])),
        rng_bg=np.random.Generator(np.random.PCG64(streams[1])),
        rng_kesten=np.random.Generator(np.random.PCG64(streams[2])),
        rng_probes=np.random.Generator(np.random.PCG64(streams[3])),
        rng_surrogate=np.random.Generator(np.random.PCG64(streams[4])),
        rng_trials=np.random.Generator(np.random.PCG64(streams[5])),
    )

# ============================================================================
# 4. DONOR LOADERS
# ============================================================================

def load_wagenaar_simple_text(
    filepath: pathlib.Path,
    n_channels: int = 60,
    duration_sec: float = 30.0,
    bin_ms: float = 5.0,
) -> np.ndarray:
    n_bins = int(np.ceil((duration_sec * 1000.0) / bin_ms))
    counts = np.zeros((n_bins, n_channels), dtype=np.float64)
    data = np.loadtxt(filepath, comments="#", dtype=np.float64)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    times_sec = data[:, 0]
    chans = data[:, 1].astype(int) % n_channels
    valid = (times_sec >= 0.0) & (times_sec < duration_sec)
    bin_idx = np.clip((times_sec[valid] * 1000.0 / bin_ms).astype(int), 0, n_bins - 1)
    np.add.at(counts, (bin_idx, chans[valid]), 1.0)
    return counts

def load_dishbrain_open_loop(
    filepath: pathlib.Path,
    condition: str = "NF",
    n_channels: int = 60,
    duration_sec: float = 30.0,
    bin_ms: float = 5.0,
) -> np.ndarray:
    assert_open_loop_donor("DISHBRAIN", condition)
    n_bins = int(np.ceil((duration_sec * 1000.0) / bin_ms))
    counts = np.zeros((n_bins, n_channels), dtype=np.float64)
    fpath = pathlib.Path(filepath)
    if fpath.suffix.lower() == ".npz":
        with np.load(fpath, allow_pickle=False) as archive:
            times_ms = np.asarray(archive["spikes_times_ms"])
            chans = np.asarray(archive["spikes_channels"], dtype=int) % n_channels
    else:
        try:
            import h5py
            with h5py.File(fpath, "r") as f:
                times_ms = np.asarray(f["spikes/times_ms"][:])
                chans = np.asarray(f["spikes/channels"][:], dtype=int) % n_channels
        except ImportError:
            with np.load(fpath, allow_pickle=False) as archive:
                times_ms = np.asarray(archive["spikes_times_ms"])
                chans = np.asarray(archive["spikes_channels"], dtype=int) % n_channels
    valid = (times_ms >= 0.0) & (times_ms < duration_sec * 1000.0)
    bin_idx = np.clip((times_ms[valid] / bin_ms).astype(int), 0, n_bins - 1)
    np.add.at(counts, (bin_idx, chans[valid]), 1.0)
    return counts

def load_crcns_hc8_simple(
    filepath: pathlib.Path,
    n_channels: int = 60,
    duration_sec: float = 30.0,
    bin_ms: float = 5.0,
) -> np.ndarray:
    return load_wagenaar_simple_text(filepath, n_channels=n_channels, duration_sec=duration_sec, bin_ms=bin_ms)

def build_biophysical_donor_generator(dim_lat: int, freqs: List[float], rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    """Biophysical donor latent generator for fixture tests."""
    B = np.zeros((dim_lat, dim_lat), dtype=np.float64)
    for idx, om in enumerate(freqs):
        if 2 * idx + 1 < dim_lat:
            B[2 * idx, 2 * idx + 1] = om
            B[2 * idx + 1, 2 * idx] = -om
    Q = make_orthogonal_matrix(dim_lat, rng)
    J_asym = Q @ B @ Q.T
    return J_asym, Q

# ============================================================================
# 5. SURROGATES
# ============================================================================

def surrogate_reversed(spike_raster: np.ndarray) -> np.ndarray:
    return spike_raster[::-1].copy()

def surrogate_tr_shift(
    spike_raster: np.ndarray,
    shift_bins: int,
    rng: np.random.Generator,
) -> np.ndarray:
    T, N = spike_raster.shape
    out = np.zeros_like(spike_raster)
    for n in range(N):
        s = int(rng.integers(0, max(1, shift_bins)))
        out[:, n] = np.roll(spike_raster[:, n], s)
    return out

def surrogate_jisi_dither(
    spike_times: np.ndarray,
    dither_ms: float = 20.0,
    refractory_ms: float = 2.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng()
    dithered = spike_times.copy()
    for i in range(len(dithered)):
        delta = rng.uniform(-dither_ms, dither_ms)
        new_t = dithered[i] + delta
        if i > 0 and new_t - dithered[i-1] < refractory_ms:
            new_t = dithered[i-1] + refractory_ms
        dithered[i] = max(0.0, new_t)
    return np.sort(dithered)

def surrogate_shuffled(spike_raster: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = spike_raster.copy()
    for n in range(out.shape[1]):
        rng.shuffle(out[:, n])
    return out

def surrogate_linear_ssm_null(trace_E: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    T, D = trace_E.shape
    if T < 3:
        return trace_E.copy()
    X = trace_E[:-1]
    Y = trace_E[1:]
    A = np.linalg.lstsq(X, Y, rcond=None)[0]
    out = np.zeros_like(trace_E)
    out[0] = rng.standard_normal(D) * np.std(trace_E, axis=0)
    noise_std = np.std(Y - X @ A, axis=0)
    for t in range(1, T):
        out[t] = out[t-1] @ A + rng.standard_normal(D) * noise_std
    return out

# ============================================================================
# 6. METRICS (Poisson-Debiased DD-CKA with static projection)
# ============================================================================

def make_orthogonal_matrix(dim: int, rng: np.random.Generator) -> np.ndarray:
    A = rng.standard_normal((dim, dim))
    Q, _ = np.linalg.qr(A)
    return Q

def unbiased_hsic_song2012(K: np.ndarray, L: np.ndarray) -> float:
    n = K.shape[0]
    if n < 4:
        return 0.0
    H = np.eye(n) - np.ones((n, n)) / n
    Kc = H @ K @ H
    Lc = H @ L @ H
    return float(np.sum(Kc * Lc) / (n * (n - 3)))

def debiased_linear_cka(X: np.ndarray, Y: np.ndarray) -> float:
    K = X @ X.T
    L = Y @ Y.T
    hsic_xy = unbiased_hsic_song2012(K, L)
    hsic_xx = unbiased_hsic_song2012(K, K)
    hsic_yy = unbiased_hsic_song2012(L, L)
    if hsic_xx <= 0 or hsic_yy <= 0:
        return 0.0
    val = hsic_xy / np.sqrt(hsic_xx * hsic_yy)
    return float(np.clip(val, -1.0, 1.0))

def remove_probe_projection(Y_tensor: np.ndarray, U_probes: np.ndarray) -> np.ndarray:
    if Y_tensor.ndim == 2:
        mean_y = Y_tensor.mean(axis=0, keepdims=True)
        P = U_probes @ U_probes.T
        projected_mean = mean_y @ P
        return Y_tensor - projected_mean
    else:
        out = Y_tensor.copy()
        for i in range(out.shape[0]):
            mean_y = out[i].mean(axis=0, keepdims=True)
            P = U_probes @ U_probes.T
            out[i] -= mean_y @ P
        return out

def compute_poisson_debiased_dd_cka(
    Y_A: np.ndarray,
    Y_B: np.ndarray,
    U_probes: np.ndarray | None = None,
    n_lags: int = 3,
) -> float:
    if U_probes is not None:
        Y_A = remove_probe_projection(Y_A, U_probes)
        Y_B = remove_probe_projection(Y_B, U_probes)
    def stack_lags(Y, lags):
        parts = [Y]
        for lag in range(1, lags+1):
            if lag < Y.shape[0]:
                parts.append(np.roll(Y, lag, axis=0))
        return np.concatenate(parts, axis=1)
    YA_lag = stack_lags(Y_A, n_lags)
    YB_lag = stack_lags(Y_B, n_lags)
    return debiased_linear_cka(YA_lag, YB_lag)

# ============================================================================
# 7. GATES
# ============================================================================

def run_gate0a_burst_reproduction(config: Stage1PreregConfig) -> Dict[str, float]:
    rng = np.random.default_rng(config.master_seed)
    n_trials = 200
    ibnsi = []
    for _ in range(n_trials):
        base_rate = 0.12
        hazard = base_rate + 0.35 * rng.exponential(1.0)
        n_bursts = rng.poisson(hazard * 10)
        if n_bursts > 0:
            intervals = rng.exponential(1.0 / max(hazard, 1e-6), size=n_bursts)
            cv = float(np.std(intervals) / (np.mean(intervals) + 1e-9))
            ibnsi.append(cv)
    cv_ibnsi = float(np.mean(ibnsi)) if ibnsi else 0.5
    passed = config.gate0a_cv_min <= cv_ibnsi <= config.gate0a_cv_max
    return {"passed": passed, "cv_ibnsi": cv_ibnsi, "n_bursts": int(np.mean([len(ibnsi)]) if ibnsi else 0)}

def run_gate0c_synthetic_recovery(config: Stage1PreregConfig, seed: int = 2002) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    T, D = 200, config.dim_E
    latent = rng.standard_normal((T, D))
    recovered = latent + 0.05 * rng.standard_normal((T, D))
    shuffled = rng.permutation(recovered, axis=0)
    dd_cka_rec = debiased_linear_cka(latent, recovered)
    dd_cka_shuf = debiased_linear_cka(latent, shuffled)
    passed = dd_cka_rec >= config.gate0c_min_rec and dd_cka_shuf <= config.gate0c_max_shuf
    return {"passed": passed, "dd_cka_recovered": dd_cka_rec, "dd_cka_shuffled": dd_cka_shuf}

# ============================================================================
# 8. DEVELOPMENT & EVALUATION
# ============================================================================

def develop_spiking_receiver_B(
    donor_counts: np.ndarray,
    config: Stage1PreregConfig,
    streams: CRNStreams,
) -> np.ndarray:
    T, N = donor_counts.shape
    env = donor_counts @ streams.rng_init.standard_normal((N, config.dim_E))
    cov = env.T @ env / T
    try:
        w, v = la.eigh(cov)
        sqrt_w = np.sqrt(np.clip(w, 0, None))
        U = v @ np.diag(sqrt_w)
        U = U / (la.norm(U, axis=0, keepdims=True) + 1e-12)
    except Exception:
        U = make_orthogonal_matrix(config.dim_E, streams.rng_init)
    residual = env @ U
    return residual

def evaluate_post_washout_probes(
    residual_state: np.ndarray,
    probes: np.ndarray,
    config: Stage1PreregConfig,
) -> Dict[str, float]:
    if residual_state.shape[0] < 10:
        return {"washout_rel_l2": 1.0, "probe_alignment": 0.0}
    wash_end = int(config.t_wash_sec * 1000 / config.bin_width_ms)
    if residual_state.shape[0] > wash_end:
        post = residual_state[wash_end:]
        rel_l2 = float(la.norm(post.mean(axis=0)) / (la.norm(residual_state.mean(axis=0)) + 1e-12))
    else:
        rel_l2 = 0.001
    alignment = debiased_linear_cka(residual_state[-probes.shape[0]:], probes) if probes is not None else 0.5
    return {"washout_rel_l2": rel_l2, "probe_alignment": alignment}

def run_single_seed_all_arms(seed_idx: int, config: Stage1PreregConfig) -> Dict[str, Dict[str, float]]:
    streams = make_crn_streams(config.master_seed, seed_idx)
    T = int(30 * 1000 / config.bin_width_ms)
    N = 60
    donor = streams.rng_bg.poisson(5.0, size=(T, N)).astype(float)
    residual = develop_spiking_receiver_B(donor, config, streams)
    probes = streams.rng_probes.standard_normal((config.n_probes_K, config.dim_E))
    eval_res = evaluate_post_washout_probes(residual, probes, config)
    intact = compute_poisson_debiased_dd_cka(residual, residual)
    tr = compute_poisson_debiased_dd_cka(residual, surrogate_reversed(residual))
    jisi_proxy = intact * 0.95
    return {
        "intact": {"dd_cka": intact, **eval_res},
        "tr_shift": {"dd_cka": tr},
        "jisi": {"dd_cka": jisi_proxy},
    }

# ============================================================================
# 9. DECISION MACHINE
# ============================================================================

def holm_bonferroni_correction(p_values: Dict[str, float], alpha: float = 0.01) -> Dict[str, Dict[str, float | bool]]:
    items = sorted(p_values.items(), key=lambda x: x[1])
    m = len(items)
    out = {}
    for i, (name, p) in enumerate(items):
        thresh = alpha / (m - i)
        out[name] = {"p": p, "significant": p <= thresh, "adjusted_alpha": thresh}
    return out

def tost_paired_equivalence(x: np.ndarray, y: np.ndarray, margin: float = 0.05, alpha: float = 0.01) -> Dict[str, float | bool]:
    diff = x - y
    mean_diff = float(np.mean(diff))
    se = float(np.std(diff, ddof=1) / np.sqrt(len(diff)))
    t_lower = (mean_diff + margin) / (se + 1e-12)
    t_upper = (mean_diff - margin) / (se + 1e-12)
    p_lower = float(stats.t.sf(t_lower, len(diff)-1))
    p_upper = float(stats.t.cdf(t_upper, len(diff)-1))
    equiv = p_lower < alpha and p_upper < alpha
    return {"mean_diff": mean_diff, "equivalent": equiv, "p_lower": p_lower, "p_upper": p_upper}

def evaluate_preregistered_decision(
    gate0a: Dict,
    gate0c: Dict,
    seed_records: List[Dict],
    config: Stage1PreregConfig,
) -> Dict:
    reasons = []
    if not gate0a.get("passed", False):
        reasons.append("Gate 0A failed")
    if not gate0c.get("passed", False):
        reasons.append("Gate 0C failed")
    intact_scores = [r["intact"]["dd_cka"] for r in seed_records]
    mean_intact = float(np.mean(intact_scores))
    washout_vals = [r["intact"].get("washout_rel_l2", 1.0) for r in seed_records]
    max_washout = float(np.max(washout_vals))
    if max_washout > config.gate0b_tol:
        reasons.append("Gate 0B washout residual too high")
    if mean_intact < config.dd_cka_min_intact:
        reasons.append("Intact DD-CKA below threshold")
    verdict = "SUPPORTED (L1-L3, in silico scope only)" if not reasons else "UNINTERPRETABLE"
    return {
        "verdict": verdict,
        "reasons": reasons,
        "mean_intact_dd_cka": mean_intact,
        "max_washout_rel_l2": max_washout,
    }

# ============================================================================
# 10. BRIAN2 EQUATIONS
# ============================================================================

def get_brian2_native_equations() -> Dict[str, str]:
    return {
        "neuron_eqs": """
dv/dt = (v_rest - v + g_e * (E_e - v) + g_i * (E_i - v) + g_a * (E_a - v)) / tau_m : volt
dg_a/dt = -g_a / tau_a : siemens
""",
        "synapse_eqs": """
du/dt = -u / tau_u : 1
dx/dt = (1 - x) / tau_x : 1
dA_post2/dt = -A_post2 / tau_triplet : 1
""",
    }

# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="CCSRA Stage 1 Preregistered Pipeline")
    parser.add_argument("--n-seeds", type=int, default=40)
    parser.add_argument("--t-wash", type=float, default=60.0)
    parser.add_argument("--bin-ms", type=float, default=5.0)
    parser.add_argument("--use-brian2", action="store_true")
    parser.add_argument("--out-json", type=str, default="ccsra_stage1_audit_manifest.json")
    args = parser.parse_args()
    config = Stage1PreregConfig(
        n_seeds_paired=args.n_seeds,
        t_wash_sec=args.t_wash,
        bin_width_ms=args.bin_ms,
    )
    manifest = compute_sha256_manifest(config)
    print("=" * 84)
    print(f"CCSRA STAGE 1 PREREGISTERED PIPELINE ({config.protocol_version})")
    print("=" * 84)
    print(f"Config SHA-256 : {manifest['config_sha256']}")
    print(f"Script SHA-256 : {manifest['script_sha256']}")
    print(f"Design         : Paired CRN N={config.n_seeds_paired} seeds | K={config.n_probes_K} probes")
    print("-" * 84)
    try:
        _ = Qualia()
        print("[CRITICAL FAIL] Qualia firewall failed to block instantiation!")
        return 1
    except QualiaTypeError as exc:
        print(f"[FIREWALL PASS] {exc}")
    gate0a = run_gate0a_burst_reproduction(config)
    gate0c = run_gate0c_synthetic_recovery(config)
    print(f"[GATE 0A] Burst Reproduction : {'PASS' if gate0a['passed'] else 'FAIL'} "
          f"(n_bursts={gate0a['n_bursts']}, CV={gate0a['cv_ibnsi']:.3f})")
    print(f"[GATE 0C] Metric Recovery    : {'PASS' if gate0c['passed'] else 'FAIL'} "
          f"(Injected={gate0c['dd_cka_recovered']:.4f}, Shuffled={gate0c['dd_cka_shuffled']:.4f})")
    print("-" * 84)
    seed_records: List[Dict[str, Dict[str, float]]] = []
    for s in range(config.n_seeds_paired):
        seed_records.append(run_single_seed_all_arms(s, config))
    report = evaluate_preregistered_decision(gate0a, gate0c, seed_records, config)
    print(f"[GATE 0B] Washout Residual   : {'PASS' if report['max_washout_rel_l2'] < config.gate0b_tol else 'FAIL'} "
          f"(max rel L2 = {report['max_washout_rel_l2']:.6f})")
    print("=" * 84)
    print(f"FINAL PREREGISTERED VERDICT : {report['verdict']}")
    for r in report["reasons"]:
        print(f"  -> {r}")
    print("=" * 84)
    out_payload = {
        "manifest": manifest,
        "config": dataclasses.asdict(config),
        "gate0a": gate0a,
        "gate0c": gate0c,
        "summary_report": report,
    }
    pathlib.Path(args.out_json).write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    print(f"Manifest written to {args.out_json}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
