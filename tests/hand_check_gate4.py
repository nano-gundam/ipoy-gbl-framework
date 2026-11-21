"""Independent hand check for PW03-MV-00 (spec v1 and metric dictionary v1).

Recomputes the known answers in the two v1 notes, so an engine implementation
can be checked against them. Plain Python plus numpy only.

Usage
  python tests/hand_check_gate4.py --selftest
      Fixture G (EV, ES95, implied risk premium), the capture-rate erosion
      check, the Gate 2 threshold table (SE3 as the only reference) and
      the Gate 4 G4-01 scoring rule. Asserts every answer.
"""
import math
import sys

import numpy as np

TOL = 1e-6


# Reference portfolio spec v1, section 4
def ev(returns):
    return float(np.mean(returns))


def es95(returns):
    """Positive number = loss. k = ceil(0.05 N), no interpolation."""
    r = np.sort(np.asarray(returns, float))
    k = math.ceil(0.05 * len(r))
    return float(-r[:k].mean())


def rp_closed_form(es0, limit, p_ppa, s):
    """Every year has the same P_PPA: all returns shift by m * s / P_PPA."""
    return max(0.0, (es0 - limit) * p_ppa / s)


def rp_bisection(returns, p_ppa_by_year, s, limit, hi=200.0, tol=1e-3):
    """P_PPA differs by year: find the smallest m with ES95(m) <= limit."""
    r = np.asarray(returns, float)
    p = np.asarray(p_ppa_by_year, float)

    def es_at(m):
        return es95(r + m * s / p)

    if es_at(0.0) <= limit:
        return 0.0
    lo = 0.0
    while hi - lo > tol / 10:
        mid = (lo + hi) / 2
        if es_at(mid) <= limit:
            hi = mid
        else:
            lo = mid
    return hi


# Metric dictionary v1, section 4b
def cr_erosion(years, cr, min_years=5):
    y = np.asarray(years, float)
    c = np.asarray(cr, float)
    if len(y) < min_years:
        return float("nan")
    return float(((y - y.mean()) * (c - c.mean())).sum() / ((y - y.mean()) ** 2).sum())


# Metric dictionary v1, section 8.2. SE3 is the reference value. Higher is
# better for all three as stored: capture rate, erosion slope, spread.
def gate2_score(value, bound, margin, tol=1e-9):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "ND"
    worse = bound - value
    if worse <= tol:
        return 2
    if worse <= margin + tol:
        return 1
    return 0


# Reference portfolio spec v1, section 4.6 (G4-01): lower RP* is better.
def gate4_score(rp_zone, rp_se3, tol=1e-9):
    if rp_zone is None or (isinstance(rp_zone, float) and math.isnan(rp_zone)):
        return "ND"
    margin = max(0.25 * rp_se3, 1.0)
    worse = rp_zone - rp_se3
    if worse <= tol:
        return 2
    if worse <= margin + tol:
        return 1
    return 0


FIXTURE_G = [0.12, 0.08, 0.05, 0.10, -0.02, 0.03, 0.07, -0.30, 0.01, 0.04,
             0.09, -0.06, 0.02, 0.06, 0.11, -0.10, 0.00, 0.05, 0.03, 0.08,
             0.04, -0.18, 0.06, 0.02, 0.07, 0.01, 0.09, -0.04, 0.05, 0.03]


def selftest():
    s, p_ppa, v_p50 = 0.4, 42.5, 100_000

    assert abs(ev(FIXTURE_G) - 0.020333) < TOL
    assert math.ceil(0.05 * len(FIXTURE_G)) == 2
    es0 = es95(FIXTURE_G)
    assert abs(es0 - 0.24) < TOL

    rp0 = rp_closed_form(es0, 0.0, p_ppa, s)
    rp10 = rp_closed_form(es0, 0.10, p_ppa, s)
    assert abs(rp0 - 25.5) < TOL and abs(rp10 - 14.875) < TOL
    assert abs(rp0 * s * v_p50 - 1_020_000) < 1e-3
    assert abs(rp10 * s * v_p50 - 595_000) < 1e-3
    shifted = np.asarray(FIXTURE_G) + rp0 * s / p_ppa
    assert abs(es95(shifted) - 0.0) < TOL

    p_by_year = [40 + (i % 5) * 2.5 for i in range(len(FIXTURE_G))]
    rp_b = rp_bisection(FIXTURE_G, p_by_year, s, 0.0)
    assert abs(rp_b - 26.228571) < 1e-3, rp_b
    # Same P_PPA in every year: bisection must agree with the closed form.
    assert abs(rp_bisection(FIXTURE_G, [p_ppa] * 30, s, 0.0) - rp0) < 1e-3

    years = list(range(2019, 2026))
    cr = [0.90, 0.88, 0.87, 0.85, 0.86, 0.83, 0.81]
    assert abs(cr_erosion(years, cr) - (-0.013571)) < TOL
    assert abs(cr_erosion([2019, 2020, 2022, 2023, 2024, 2025],
                          [0.90, 0.88, 0.85, 0.86, 0.83, 0.81]) - (-0.013602)) < TOL
    assert math.isnan(cr_erosion([2022, 2023, 2024, 2025], [0.9, 0.88, 0.86, 0.85]))

    # Gate 2: SE3 is the only reference (21 Nov revision).
    se3 = {"cr": 0.82, "er": -0.010, "sp": 45}
    margin = {"cr": 0.05, "er": 0.01, "sp": 0.2 * se3["sp"]}
    cases = {"X": ((0.86, -0.005, 50), [2, 2, 2]),
             "Y": ((0.79, -0.015, 40), [1, 1, 1]),
             "Z": ((0.75, -0.025, 30), [0, 0, 0]),
             "edge_se3": ((0.82, -0.010, 45), [2, 2, 2]),
             "edge_margin": ((0.77, -0.020, 36), [1, 1, 1])}
    for name, (vals, expected) in cases.items():
        got = [gate2_score(v, se3[k], margin[k]) for v, k in zip(vals, ["cr", "er", "sp"])]
        assert got == expected, (name, got, expected)

    # Gate 4 G4-01: lower RP* is better, margin = max(25% of SE3's RP*, 1 EUR/MWh).
    for rp_se3, rp_zone, expected in [(20, 18, 2), (20, 24, 1), (20, 25, 1), (20, 26, 0),
                                      (0, 0.8, 1), (0, 1.5, 0), (0, 0, 2)]:
        assert gate4_score(rp_zone, rp_se3) == expected, (rp_se3, rp_zone)
    assert gate2_score(float("nan"), 0.74, 0.05) == "ND"

    print("All PW03-MV-00 hand checks pass.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(__doc__)
