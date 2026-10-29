#!/usr/bin/env python3
"""Reproduce the manuscript's synthetic gated inverse-variance example.

These are deliberately specified numbers, not measurements from the CEN reports.
The estimator assumes a common measurand and aligned support, unbiased,
independent errors, and known positive standard uncertainties. Gates are fixed
independently of the current errors. Expanded uncertainty at a certificate limit
is not automatically a per-observation standard uncertainty.
"""
import json
import math


def fuse(values, standard_uncertainties, gates):
    if not (len(values) == len(standard_uncertainties) == len(gates)):
        raise ValueError("Input lengths differ")
    if not values:
        raise ValueError("At least one input is required")
    if any(g not in (0, 1) for g in gates):
        raise ValueError("Gates must be binary")
    if any(not math.isfinite(x) for x in values):
        raise ValueError("Input values must be finite")
    if any(not math.isfinite(s) or s <= 0 for s in standard_uncertainties):
        raise ValueError("Standard uncertainties must be finite and positive")
    raw = [g / s**2 for g, s in zip(gates, standard_uncertainties)]
    total = sum(raw)
    if total == 0:
        return {"status": "no_eligible_source", "weights": None,
                "estimate": None, "variance": None, "standard_uncertainty": None}
    alpha = [w / total for w in raw]
    estimate = sum(a * x for a, x in zip(alpha, values))
    variance = sum(a*a*s*s for a, s in zip(alpha, standard_uncertainties))
    return {"status": "computed", "weights": alpha,
            "estimate": estimate, "variance": variance,
            "standard_uncertainty": math.sqrt(variance)}


def main():
    cases = [
        ("initial", [20.0, 22.0], [2.0, 4.0], [1, 1]),
        ("increased_uncertainty_source_1", [20.0, 22.0], [4.0, 4.0], [1, 1]),
        ("expired_calibration_source_1", [20.0, 22.0], [4.0, 4.0], [0, 1]),
        ("both_ineligible", [20.0, 22.0], [4.0, 4.0], [0, 0]),
    ]
    rows = []
    for name, values, sigma, gates in cases:
        rows.append({"scenario": name, "synthetic": True,
                     "concentration_unit": "ug/m3", "values": values,
                     "standard_uncertainties": sigma, "gates": gates,
                     **fuse(values, sigma, gates)})
    expected = [20.4, 21.0, 22.0, None]
    for row, want in zip(rows, expected):
        if want is None:
            assert row["estimate"] is None
        else:
            assert math.isclose(row["estimate"], want, abs_tol=1e-12)
            assert math.isclose(sum(row["weights"]), 1.0, abs_tol=1e-12)
    print(json.dumps({"kind": "synthetic_worked_example", "cases": rows}, indent=2))


if __name__ == "__main__":
    main()
