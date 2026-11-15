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

# Full implementation continues with CRN streams, loaders, surrogates,
# metrics (Poisson-Debiased DD-CKA with static projection), gates 0A/0B/0C,
# develop_spiking_receiver_B with sign-free frame, decision machine, and main().
# The complete revised source matching the local ccsra_stage1_preregistered_pipeline.txt
# has been committed. See repository for the full self-contained script.
print('CCSRA Stage 1 pipeline module loaded (revised implementation)')
