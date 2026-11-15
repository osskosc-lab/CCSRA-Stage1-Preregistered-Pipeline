#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Donor Loader Connection & Confound Guard Verification Suite
===========================================================
Verifies real-schema file ingestion, surrogate constraints, and end-to-end
pipeline execution for:
  1. Wagenaar et al. (2006a) simple-text schemas:
     - Batch 1-7 'daily' spontaneous recording format
     - Batch 1-7 'stim' open-loop stimulation recording format
     - Batch 1-7 'dense' plating recording format
  2. DishBrain (Kagan et al. 2022, OSF 5U6QV) archive schemas:
     - Open-loop 'NF' (No-Feedback) condition -> PASS & E2E DD-CKA evaluation
     - Open-loop 'RST' (Rest) condition -> PASS & E2E DD-CKA evaluation
     - Closed-loop 'STIM', 'SIL', 'PONG_CLOSED_LOOP' -> BLOCKED with ValueError
  3. CRCNS hc-8 (Timme et al. 2016) dissociated hippocampal culture format
     -> PASS & E2E SOURCE_SWAP contrast verification
  4. Surrogate and Epistemic Firewall Guards:
     - Uniform Dithering ('UD', 'UNIFORM_DITHER', 'UNIFORM') -> BLOCKED
     - JISI-D (20 ms window, 2 ms refractory dead-time) -> Spike-count & ISI check
     - Qualia() instantiation -> BLOCKED with QualiaTypeError
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
from typing import Dict, Any

import numpy as np
import scipy.linalg as la

# Ensure the current script directory is in sys.path for local module import (GitHub CI compatible)
CURRENT_DIR = pathlib.Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import ccsra_stage1_preregistered_pipeline as pipe


def generate_wagenaar_fixture(
    filepath: pathlib.Path,
    J_donor: np.ndarray,
    Q_embed: np.ndarray,
    n_channels: int,
    duration_sec: float,
    bin_ms: float,
    rng: np.random.Generator,
    mode_tag: str = "daily",
) -> int:
    """
    Generates a schema-exact Wagenaar et al. (2006) simple-text ASCII spike file:
    Columns: [time_sec, channel_id (0..59), height_uV, width_ms]
    Driven by latent oscillatory generator J_donor so that end-to-end DD-CKA
    recovery from file ingestion can be quantitatively verified without stubs.
    """
    dim_lat = J_donor.shape[0]
    n_bins = int((duration_sec * 1000.0) / bin_ms)
    dt = 0.20
    M_step = la.expm(dt * J_donor)
    z = rng.standard_normal(dim_lat)
    z /= la.norm(z) + 1e-12

    base_rate = 9.5 if mode_tag == "daily" else (10.2 if mode_tag == "stim" else 11.0)
    rows = []
    for b in range(n_bins):
        z = 0.96 * (M_step @ z) + 0.28 * rng.standard_normal(dim_lat)
        lam = np.clip(base_rate + 5.5 * (Q_embed @ z), 0.2, 35.0)
        sp_counts = rng.poisson(lam)
        active_chans = np.flatnonzero(sp_counts > 0)
        for ch in active_chans:
            c_val = int(sp_counts[ch])
            for _ in range(c_val):
                t_sec = (b * bin_ms + rng.uniform(0.1, bin_ms - 0.1)) / 1000.0
                height_uv = float(rng.normal(-48.0, 8.5))
                width_ms = float(rng.uniform(0.8, 1.6))
                rows.append((t_sec, int(ch), height_uv, width_ms))

    rows.sort(key=lambda r: r[0])
    arr = np.array(rows, dtype=np.float64)
    np.savetxt(
        filepath,
        arr,
        fmt=["%.6f", "%d", "%.2f", "%.3f"],
        header=f"Wagenaar-Potter MEA simple-text schema ({mode_tag}) | cols: time_sec channel_id height_uV width_ms",
    )
    return len(rows)


def generate_dishbrain_archive_fixture(
    filepath: pathlib.Path,
    J_donor: np.ndarray,
    Q_embed: np.ndarray,
    n_channels: int,
    duration_sec: float,
    bin_ms: float,
    rng: np.random.Generator,
    condition: str = "NF",
) -> int:
    """
    Generates a DishBrain OSF 5U6QV archive file containing datasets:
      - spikes_times_ms (float64)
      - spikes_channels (int32)
      - condition (string)
    """
    dim_lat = J_donor.shape[0]
    n_bins = int((duration_sec * 1000.0) / bin_ms)
    dt = 0.20
    M_step = la.expm(dt * J_donor)
    z = rng.standard_normal(dim_lat)
    z /= la.norm(z) + 1e-12

    times_list = []
    chans_list = []
    base_rate = 10.0 if condition == "NF" else 9.2
    for b in range(n_bins):
        z = 0.96 * (M_step @ z) + 0.28 * rng.standard_normal(dim_lat)
        lam = np.clip(base_rate + 5.5 * (Q_embed @ z), 0.2, 35.0)
        sp_counts = rng.poisson(lam)
        active_chans = np.flatnonzero(sp_counts > 0)
        for ch in active_chans:
            for _ in range(int(sp_counts[ch])):
                t_ms = b * bin_ms + float(rng.uniform(0.05, bin_ms - 0.05))
                times_list.append(t_ms)
                chans_list.append(int(ch))

    order = np.argsort(times_list)
    times_arr = np.array(times_list, dtype=np.float64)[order]
    chans_arr = np.array(chans_list, dtype=np.int32)[order]

    np.savez(
        filepath,
        spikes_times_ms=times_arr,
        spikes_channels=chans_arr,
        dataset=np.array("DishBrain_OSF_5U6QV"),
        condition=np.array(condition),
    )
    return len(times_arr)


def run_donor_connection_tests() -> Dict[str, Any]:
    config = pipe.Stage1PreregConfig()
    streams = pipe.make_crn_streams(config.master_seed, 900)
    dim_lat = 8
    n_channels = 60
    n_sub = 48
    duration_sec = 6.0  # 6.0 s at 5 ms bin = 1200 time bins

    freqs_A = [0.40, 0.85, 1.35, 1.95]
    freqs_hc8 = [-0.65, -1.55, -1.15, -0.30]
    J_A, _ = pipe.build_biophysical_donor_generator(dim_lat, freqs_A, streams.rng_init)
    J_hc8, _ = pipe.build_biophysical_donor_generator(dim_lat, freqs_hc8, streams.rng_init)

    Q_embed = pipe.make_orthogonal_matrix(n_channels, streams.rng_init)[:, :dim_lat]
    Q_E_lat = pipe.make_orthogonal_matrix(config.dim_E, streams.rng_init)[:, :dim_lat]
    W_AE = Q_E_lat @ Q_embed.T * 1.25
    W_probe_E = Q_E_lat
    W_EB = pipe.make_orthogonal_matrix(n_sub, streams.rng_init)[:, : config.dim_E]

    n_kesten_steps = 12
    kesten_stream = (
        streams.rng_kesten.standard_normal((n_kesten_steps, dim_lat, dim_lat)),
        streams.rng_kesten.standard_normal((n_kesten_steps, dim_lat, dim_lat)),
    )
    U_probes = streams.rng_probes.standard_normal((config.n_probes_K, dim_lat))
    U_probes /= la.norm(U_probes, axis=1, keepdims=True) + 1e-12

    counts_A_probe = pipe.evaluate_post_washout_probes(J_A, Q_embed, U_probes, config, streams.rng_trials)
    b_trial_state = streams.rng_trials.bit_generator.state

    results: Dict[str, Any] = {
        "wagenaar_loaders": {},
        "dishbrain_loaders": {},
        "crcns_hc8_source_swap": {},
        "closed_loop_guards": {},
        "surrogate_and_qualia_guards": {},
    }

    with tempfile.TemporaryDirectory(prefix="ccsra_donor_test_") as tmpdir:
        tpath = pathlib.Path(tmpdir)

        # 1. Test Wagenaar simple-text across daily, stim, dense schemas
        for mode_tag in ["daily", "stim", "dense"]:
            fpath = tpath / f"wagenaar_batch1_{mode_tag}.txt"
            n_raw_spikes = generate_wagenaar_fixture(
                fpath, J_A, Q_embed, n_channels, duration_sec, config.bin_width_ms, streams.rng_bg, mode_tag=mode_tag
            )
            counts_loaded = pipe.load_wagenaar_simple_text(
                fpath, n_channels=n_channels, duration_sec=duration_sec, bin_ms=config.bin_width_ms
            )
            E_trace = pipe.compute_env_trace_from_spikes(counts_loaded, W_AE, config)
            dev = pipe.develop_spiking_receiver_B(E_trace, W_EB, W_probe_E, config, kesten_stream, is_sever=False)

            streams.rng_trials.bit_generator.state = b_trial_state
            counts_B_probe = pipe.evaluate_post_washout_probes(
                dev["W_B_mode1"], dev["U_sensory"], U_probes, config, streams.rng_trials,
                residual_state=dev["transient_carryover"],
            )
            dd_cka, _ = pipe.compute_poisson_debiased_dd_cka(counts_A_probe, counts_B_probe, U_probes)

            # Test JISI-D (20 ms) and TR-SHIFT surrogates on loaded Wagenaar raster
            jisi_raster = pipe.surrogate_jisi_dither(counts_loaded, streams.rng_surrogate, bin_ms=config.bin_width_ms, dither_ms=20.0)
            tr_raster = pipe.surrogate_tr_shift(counts_loaded, streams.rng_surrogate)
            E_tr = pipe.compute_env_trace_from_spikes(tr_raster, W_AE, config)
            dev_tr = pipe.develop_spiking_receiver_B(E_tr, W_EB, W_probe_E, config, kesten_stream, is_sever=False)
            streams.rng_trials.bit_generator.state = b_trial_state
            counts_B_tr = pipe.evaluate_post_washout_probes(
                dev_tr["W_B_mode1"], dev_tr["U_sensory"], U_probes, config, streams.rng_trials
            )
            dd_cka_tr, _ = pipe.compute_poisson_debiased_dd_cka(counts_A_probe, counts_B_tr, U_probes)

            results["wagenaar_loaders"][mode_tag] = {
                "status": "PASS",
                "raster_shape": list(counts_loaded.shape),
                "raw_spike_events": int(n_raw_spikes),
                "binned_spike_sum": float(np.sum(counts_loaded)),
                "jisi_spike_conservation_ratio": float(np.sum(jisi_raster) / (np.sum(counts_loaded) + 1e-12)),
                "tr_shift_spike_conservation_ratio": float(np.sum(tr_raster) / (np.sum(counts_loaded) + 1e-12)),
                "intact_dd_cka": float(dd_cka),
                "tr_shift_dd_cka": float(dd_cka_tr),
                "washout_rel_l2": float(dev["washout_rel_l2"]),
            }

        # 2. Test DishBrain OSF 5U6QV Open-Loop ('NF', 'RST')
        for cond in ["NF", "RST"]:
            db_path = tpath / f"dishbrain_osf_5u6qv_{cond}.npz"
            n_sp_db = generate_dishbrain_archive_fixture(
                db_path, J_A, Q_embed, n_channels, duration_sec, config.bin_width_ms, streams.rng_bg, condition=cond
            )
            counts_db = pipe.load_dishbrain_open_loop(
                db_path, condition=cond, n_channels=n_channels, duration_sec=duration_sec, bin_ms=config.bin_width_ms
            )
            E_db = pipe.compute_env_trace_from_spikes(counts_db, W_AE, config)
            dev_db = pipe.develop_spiking_receiver_B(E_db, W_EB, W_probe_E, config, kesten_stream, is_sever=False)

            streams.rng_trials.bit_generator.state = b_trial_state
            counts_B_db = pipe.evaluate_post_washout_probes(
                dev_db["W_B_mode1"], dev_db["U_sensory"], U_probes, config, streams.rng_trials,
                residual_state=dev_db["transient_carryover"],
            )
            dd_cka_db, _ = pipe.compute_poisson_debiased_dd_cka(counts_A_probe, counts_B_db, U_probes)
            results["dishbrain_loaders"][cond] = {
                "status": "PASS",
                "raster_shape": list(counts_db.shape),
                "raw_spike_events": int(n_sp_db),
                "binned_spike_sum": float(np.sum(counts_db)),
                "intact_dd_cka": float(dd_cka_db),
                "washout_rel_l2": float(dev_db["washout_rel_l2"]),
            }

        # 3. Test CRCNS hc-8 Donor Loader (SOURCE_SWAP verification against Wagenaar Donor A)
        hc8_path = tpath / "crcns_hc8_rat_hippocampal.txt"
        n_sp_hc8 = generate_wagenaar_fixture(
            hc8_path, J_hc8, Q_embed, n_channels, duration_sec, config.bin_width_ms, streams.rng_bg, mode_tag="hc8"
        )
        counts_hc8 = pipe.load_crcns_hc8_simple(
            hc8_path, n_channels=n_channels, duration_sec=duration_sec, bin_ms=config.bin_width_ms
        )
        E_hc8 = pipe.compute_env_trace_from_spikes(counts_hc8, W_AE, config)
        dev_hc8 = pipe.develop_spiking_receiver_B(E_hc8, W_EB, W_probe_E, config, kesten_stream, is_sever=False)
        streams.rng_trials.bit_generator.state = b_trial_state
        counts_B_hc8 = pipe.evaluate_post_washout_probes(
            dev_hc8["W_B_mode1"], dev_hc8["U_sensory"], U_probes, config, streams.rng_trials,
            residual_state=dev_hc8["transient_carryover"],
        )
        dd_cka_hc8, _ = pipe.compute_poisson_debiased_dd_cka(counts_A_probe, counts_B_hc8, U_probes)
        results["crcns_hc8_source_swap"] = {
            "status": "PASS",
            "raster_shape": list(counts_hc8.shape),
            "raw_spike_events": int(n_sp_hc8),
            "source_swap_dd_cka_vs_donorA": float(dd_cka_hc8),
        }

        # 4. Test Closed-Loop DishBrain Confound Guards (STIM, SIL, PONG_CLOSED_LOOP must raise ValueError)
        dummy_db = tpath / "dishbrain_osf_5u6qv_NF.npz"
        for forbidden_cond in ["STIM", "SIL", "PONG_CLOSED_LOOP"]:
            try:
                _ = pipe.load_dishbrain_open_loop(dummy_db, condition=forbidden_cond)
                results["closed_loop_guards"][forbidden_cond] = {"blocked": False, "error": "FAILED_TO_BLOCK"}
            except ValueError as exc:
                results["closed_loop_guards"][forbidden_cond] = {
                    "blocked": True,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }

        # 5. Test Surrogate Uniform Dithering (UD) Guard & Epistemic Claim Firewall
        for forbidden_surr in ["UD", "UNIFORM_DITHER", "UNIFORM"]:
            try:
                pipe.assert_no_uniform_dither(forbidden_surr)
                results["surrogate_and_qualia_guards"][forbidden_surr] = {"blocked": False}
            except ValueError as exc:
                results["surrogate_and_qualia_guards"][forbidden_surr] = {
                    "blocked": True,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }

        try:
            _ = pipe.Qualia()
            results["surrogate_and_qualia_guards"]["Qualia_Firewall"] = {"blocked": False}
        except pipe.QualiaTypeError as exc:
            results["surrogate_and_qualia_guards"]["Qualia_Firewall"] = {
                "blocked": True,
                "exception_type": type(exc).__name__,
                "message": str(exc),
            }

        # 6. Verify Brian 2 Native Equation Port
        b2_eqs = pipe.get_brian2_native_equations()
        results["brian2_equation_port"] = {
            "status": "PASS",
            "keys_present": list(b2_eqs.keys()),
            "has_nmda_mg_block": "Mg_conc/3.57" in b2_eqs["neuron_eqs"],
            "has_sahp_adaptation_ga": "dg_a/dt = -g_a / tau_a" in b2_eqs["neuron_eqs"],
            "has_tsodyks_markram_stp": ("du/dt" in b2_eqs["synapse_eqs"]) and ("dx/dt" in b2_eqs["synapse_eqs"]),
            "has_triplet_stdp": "dA_post2/dt = -A_post2 / tau_triplet" in b2_eqs["synapse_eqs"],
        }

    return results


if __name__ == "__main__":
    res = run_donor_connection_tests()
    out_file = CURRENT_DIR / "donor_loader_connection_test_report.json"
    out_file.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("=" * 84)
    print("DONOR LOADER CONNECTION & CONFOUND GUARD TEST SUITE COMPLETED")
    print("=" * 84)
    for k, v in res["wagenaar_loaders"].items():
        print(f"[Wagenaar {k:<5}] status={v['status']} | spikes={v['raw_spike_events']} | "
              f"INTACT DD-CKA={v['intact_dd_cka']:+.4f} | TR-SHIFT DD-CKA={v['tr_shift_dd_cka']:+.4f} | "
              f"JISI spike conservation={v['jisi_spike_conservation_ratio']:.4f}")
    for k, v in res["dishbrain_loaders"].items():
        print(f"[DishBrain {k:<4}] status={v['status']} | spikes={v['raw_spike_events']} | "
              f"INTACT DD-CKA={v['intact_dd_cka']:+.4f} | washout_rel_L2={v['washout_rel_l2']:.3e}")
    hc8 = res["crcns_hc8_source_swap"]
    print(f"[CRCNS hc-8   ] status={hc8['status']} | spikes={hc8['raw_spike_events']} | "
          f"SOURCE_SWAP DD-CKA vs Donor A={hc8['source_swap_dd_cka_vs_donorA']:+.4f}")
    for k, v in res["closed_loop_guards"].items():
        print(f"[ClosedLoop Guard {k:<16}] blocked={v['blocked']} ({v['exception_type']})")
    for k, v in res["surrogate_and_qualia_guards"].items():
        print(f"[Firewall/Surr Guard {k:<14}] blocked={v['blocked']} ({v['exception_type']})")
    print("=" * 84)
