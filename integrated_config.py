"""Shared configuration for integrated cyto → histo simulations."""

from __future__ import annotations

from typing import Dict, Optional

# When set, v2_histosim uses this daily schedule instead of Poisson cervical arrivals.
cervical_daily_schedule: Optional[Dict[int, int]] = None

# Fraction of pap smears classified positive and referred for biopsy the next day.
PAP_POSITIVITY_RATE: float = 0.10
