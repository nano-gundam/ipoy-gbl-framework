"""Independent hand check for the metric dictionary (PW01-MV-03).

Written separately from the main pipeline on purpose, so it can be used to
test Lingyu's implementation. Plain pandas/numpy only.

Usage
  python hand_check_se3_2024.py --selftest
      Recompute fixtures A and B from metric-dictionary-v0.md and assert the answers.

  python hand_check_se3_2024.py data/raw/entsoe/prices/SE3/2024.parquet
      Print the SE3 reference values for local days 27-29 July 2024.
      Also accepts a .csv. The file needs a UTC timestamp column (index or a column
      whose name contains "time") and a column named price_eur_mwh.
"""
import sys
import numpy as np
import pandas as pd

MARKET_TZ = "Europe/Berlin"  # SDAC delivery day, harmonisation.md section 2


def daily_spread(prices, k):
    s = np.sort(np.asarray(prices, dtype=float))
    return s[-k:].mean() - s[:k].mean()


def capture(price, gen, nonneg=False):
    p = np.asarray(price, float)
    g = np.clip(np.asarray(gen, float), 0, None)
    base = p.mean()
    m = p >= 0 if nonneg else np.ones_like(p, bool)
    cap_price = (g[m] * p[m]).sum() / g[m].sum()
    return cap_price, cap_price / base


def selftest():
    p = [18.0, 15.5, 14.0, 12.0, 10.5, 8.0, 5.0, 2.0, 0.5, -1.5, -6.0, -3.5,
         0.0, 1.0, 4.0, 9.0, 16.0, 24.0, 32.0, 38.5, 35.0, 28.0, 22.0, 19.0]
    solar = [0, 0, 0, 0, 0, 10, 40, 90, 150, 200, 240, 260,
             260, 240, 200, 150, 90, 40, 10, 0, 0, 0, 0, 0]
    wind = [800, 820, 850, 870, 900, 950, 1000, 1050, 1100, 1150, 1180, 1200,
            1150, 1100, 1000, 900, 800, 700, 600, 550, 500, 520, 560, 600]
    s = pd.Series(p)
    neg = s[s < 0]
    checks = {
        "price_mean": (s.mean(), 12.625),
        "std_hourly": (s.std(), 12.550983),
        "neg_hours": (len(neg), 3),
        "neg_mean": (neg.mean(), -3.666667),
        "spread_2h": (daily_spread(p, 2), 41.5),
        "spread_4h": (daily_spread(p, 4), 36.125),
        "cr_solar": (capture(p, solar)[1], 0.119812),
        "cr_solar_nonneg": (capture(p, solar, True)[1], 0.349319),
        "cr_wind": (capture(p, wind)[1], 0.760168),
        "cr_wind_nonneg": (capture(p, wind, True)[1], 0.974573),
        "std_daily_change": (pd.Series([20.0, 35.0, 30.0, 12.0]).diff().dropna().std(), 16.623277),
    }
    ok = True
    for name, (got, want) in checks.items():
        good = abs(got - want) < 1e-6 if isinstance(want, float) else got == want
        ok &= good
        print(f"{'OK ' if good else 'FAIL'} {name:18s} got {got:.6f}  expected {want}")
    sys.exit(0 if ok else 1)


def load(path):
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        tcol = next(c for c in df.columns if "time" in c.lower())
        df = df.set_index(pd.to_datetime(df[tcol], utc=True))
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    price = df["price_eur_mwh"].sort_index()
    # 15-minute data (not expected for 2024) -> hourly mean, only complete hours
    step = price.index.to_series().diff().dropna().min()
    if step < pd.Timedelta("1h"):
        g = price.resample("1h")
        price = g.mean().where(g.count() == 4)
    return price


def se3_window(path):
    price = load(path).tz_convert(MARKET_TZ)
    w = price["2024-07-27":"2024-07-29"]
    print(f"hours in window: {len(w)} (expected 72), missing: {w.isna().sum()}")
    print("\nhourly prices (local time):")
    print(w.to_string())
    days = w.groupby(w.index.date)
    daily = days.mean()
    neg = w[w < 0]
    print("\n--- reference values, SE3, 27-29 Jul 2024 ---")
    print(f"price mean (72 h)          {w.mean():.6f} EUR/MWh")
    print(f"hourly std (n-1)           {w.std():.6f} EUR/MWh")
    print(f"daily means                {', '.join(f'{v:.6f}' for v in daily)}")
    print(f"std of daily change (n-1)  {daily.diff().dropna().std():.6f} EUR/MWh")
    print(f"negative hours             {len(neg)}")
    print(f"mean negative price        {neg.mean():.6f} EUR/MWh")
    print(f"spread 2h (mean of days)   {days.apply(lambda x: daily_spread(x, 2)).mean():.6f} EUR/MWh")
    print(f"spread 4h (mean of days)   {days.apply(lambda x: daily_spread(x, 4)).mean():.6f} EUR/MWh")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    selftest() if sys.argv[1] == "--selftest" else se3_window(sys.argv[1])
