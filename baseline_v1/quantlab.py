#!/usr/bin/env python3
"""Reproducible, public-data-only Binance Spot research and paper simulator."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
API = "https://data-api.binance.vision"
FIELDS = ["open_time", "open", "high", "low", "close", "volume", "close_time"]
STRATEGIES = tuple(CONFIG["strategies"])
FRICTION = CONFIG["fees_per_side"] + CONFIG["spread_per_side"] + CONFIG["slippage_per_side"]
IMPACT = CONFIG["spread_per_side"] + CONFIG["slippage_per_side"]
FX = CONFIG["brl_per_usdt_reference"]
INITIAL_BRL = CONFIG["initial_capital_brl"]
INITIAL_USDT = INITIAL_BRL / FX


def utc_ms(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)


def get_json(path: str, params: dict | None = None, timeout: int = 20):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-quant-lab/1.0"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), dict(response.headers)
        except urllib.error.HTTPError as e:
            if e.code not in (418, 429, 500, 502, 503, 504) or attempt == 5: raise
            delay = float(e.headers.get("Retry-After", min(60, 2**attempt)))
            time.sleep(max(1, min(delay, 120)))
        except urllib.error.URLError:
            if attempt == 5: raise
            time.sleep(min(60, 2**attempt))


def download(args):
    out = Path(args.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    start, end = utc_ms(args.start), utc_ms(args.end)
    info, _ = get_json("/api/v3/exchangeInfo")
    ticker, _ = get_json("/api/v3/ticker/24hr")
    ticker_by_symbol = {x["symbol"]: x for x in ticker}
    meta = {"source": API + "/api/v3/klines", "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "interval": "1h", "start_utc": args.start, "end_exclusive_utc": args.end, "symbols": {}}
    meta["brl_usdt_reference"] = {"brl_per_usdt": FX, "reference_date": CONFIG["brl_per_usdt_reference_date"],
        "source": "Banco Central do Brasil PTAX USD venda; USDT aproximado como USD; não é cotação executável."}
    for symbol in CONFIG["symbols"]:
        exchange_symbol = next((s for s in info["symbols"] if s["symbol"] == symbol), None)
        if not exchange_symbol or exchange_symbol.get("status") != "TRADING":
            raise RuntimeError(f"{symbol} não consta como TRADING em exchangeInfo.")
        dest = out / f"{symbol}_1h.csv"
        rows, cursor = [], start
        while cursor < end:
            batch, _ = get_json("/api/v3/klines", {"symbol": symbol, "interval": "1h", "startTime": cursor,
                                                           "endTime": end - 1, "limit": 1000})
            if not batch:
                break
            for k in batch:
                if start <= k[0] < end and k[6] < int(time.time() * 1000):
                    rows.append([k[0], k[1], k[2], k[3], k[4], k[5], k[6]])
            cursor = batch[-1][0] + 3_600_000
            if len(batch) < 1000:
                break
            time.sleep(0.12)
        rows.sort(key=lambda x: int(x[0]))
        with dest.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(FIELDS); w.writerows(rows)
        gaps = sum(int(rows[i][0]) - int(rows[i-1][0]) != 3_600_000 for i in range(1, len(rows)))
        tick = ticker_by_symbol.get(symbol, {})
        meta["symbols"][symbol] = {"file": dest.name, "bars": len(rows), "gaps": gaps,
            "first_open_utc": datetime.fromtimestamp(int(rows[0][0])/1000, timezone.utc).isoformat() if rows else None,
            "last_open_utc": datetime.fromtimestamp(int(rows[-1][0])/1000, timezone.utc).isoformat() if rows else None,
            "current_24h_quote_volume_usdt": tick.get("quoteVolume"), "exchange_status": exchange_symbol["status"],
            "filters": exchange_symbol.get("filters", [])}
        print(f"{symbol}: {len(rows):,} candles; {gaps} lacunas; volume 24h (consulta): {tick.get('quoteVolume', 'n/d')} USDT")
    (out / "source_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Metadados e CSV gravados em {out.resolve()}")


def read_bars(data_dir: Path, symbol: str):
    with (data_dir / f"{symbol}_1h.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    bars = []
    for r in rows:
        bars.append({"t": int(r["open_time"]), "o": float(r["open"]), "h": float(r["high"]),
                     "l": float(r["low"]), "c": float(r["close"]), "v": float(r["volume"]), "ct": int(r["close_time"])})
    return bars


def ema(xs, n):
    out, alpha, value = [None] * len(xs), 2 / (n + 1), None
    for i, x in enumerate(xs):
        value = x if value is None else alpha * x + (1-alpha) * value
        if i >= n - 1: out[i] = value
    return out


def rolling_mean(xs, n):
    out, total = [None] * len(xs), 0.0
    for i, x in enumerate(xs):
        total += x
        if i >= n: total -= xs[i-n]
        if i >= n-1: out[i] = total/n
    return out


def rolling_std(xs, n):
    out = [None] * len(xs)
    for i in range(n-1, len(xs)):
        w = xs[i-n+1:i+1]
        out[i] = statistics.pstdev(w)
    return out


def rsi(xs, n):
    out = [None] * len(xs)
    if len(xs) <= n: return out
    gains = [max(xs[i]-xs[i-1], 0) for i in range(1, n+1)]
    losses = [max(xs[i-1]-xs[i], 0) for i in range(1, n+1)]
    ag, al = sum(gains)/n, sum(losses)/n
    for i in range(n, len(xs)):
        if i > n:
            gain, loss = max(xs[i]-xs[i-1], 0), max(xs[i-1]-xs[i], 0)
            ag, al = ((n-1)*ag+gain)/n, ((n-1)*al+loss)/n
        out[i] = 100.0 if al == 0 else 100 - 100/(1+ag/al)
    return out


def features(bars, name):
    p = CONFIG["strategies"][name]
    closes = [b["c"] for b in bars]
    tr = []
    for i, b in enumerate(bars):
        tr.append(b["h"]-b["l"] if i == 0 else max(b["h"]-b["l"], abs(b["h"]-closes[i-1]), abs(b["l"]-closes[i-1])))
    atr = rolling_mean(tr, p.get("atr_period", 14))
    rs = rsi(closes, p.get("rsi_period", 14))
    fast = ema(closes, p.get("ema_fast", 50)) if name == "momentum_pullback" else None
    slow = ema(closes, p.get("ema_slow", 200)) if name == "momentum_pullback" else None
    mid = rolling_mean(closes, p.get("band_period", 20)) if name == "mean_reversion" else None
    sd = rolling_std(closes, p.get("band_period", 20)) if name == "mean_reversion" else None
    signal = [False] * len(bars)
    for i in range(1, len(bars)):
        # A signal is only actionable on the next hourly open. No current-bar close fill.
        if name == "momentum_pullback":
            signal[i] = bool(fast[i] and slow[i] and rs[i-1] is not None and rs[i] is not None
                             and fast[i] > slow[i] and closes[i] > fast[i]
                             and rs[i-1] < p["rsi_cross"] <= rs[i])
        elif name == "volatility_breakout":
            n = p["breakout_lookback"]
            prev_high = max(b["h"] for b in bars[i-n:i]) if i >= n else None
            signal[i] = bool(prev_high and atr[i] and closes[i] > prev_high and 0.002 <= atr[i]/closes[i] <= 0.05)
        else:
            lower = mid[i] - p["band_std"] * sd[i] if mid[i] is not None and sd[i] is not None else None
            signal[i] = bool(lower is not None and rs[i] is not None and closes[i] < lower and rs[i] <= p["rsi_max"])
    return [{**b, "atr": atr[i], "rsi": rs[i], "fast": fast[i] if fast else None,
             "slow": slow[i] if slow else None, "mid": mid[i] if mid else None,
             "signal": signal[i]} for i, b in enumerate(bars)]


def iso(ts):
    return datetime.fromtimestamp(ts/1000, timezone.utc).isoformat().replace("+00:00", "Z")


def stop_for(name, row):
    p = CONFIG["strategies"][name]
    return row["c"] - p["stop_atr"]*row["atr"]


def outage_at(ts):
    """Deterministic 6h service outage in each 30d block, for stress scenario only."""
    block = 30*24*3_600_000
    n = int(CONFIG["simulated_data_outage_hours_per_30d"])
    cycle = ts // block
    rng = random.Random(CONFIG["simulated_data_outage_seed"] + cycle)
    offset = rng.randrange(30*24-n)
    start = cycle*block + offset*3_600_000
    return start <= ts < start + n*3_600_000


def backtest_strategy(name, data_dir, initial=500.0, start="2021-07-01", end="2026-10-08", prepared=None, outage=False):
    series = prepared or {s: features(read_bars(data_dir, s), name) for s in CONFIG["symbols"]}
    lo, hi = utc_ms(start), utc_ms(end)
    timeline = sorted({r["t"] for rows in series.values() for r in rows if lo <= r["t"] < hi})
    idx = {s: {r["t"]: i for i, r in enumerate(rows)} for s, rows in series.items()}
    cash, positions, trades, curve = initial, {}, [], []
    day, day_start, halted, outage_active = None, initial, False, False
    p = CONFIG["strategies"][name]
    for t in timeline:
        blocked = outage and outage_at(t)
        if blocked:
            outage_active = True
            curve.append({"timestamp_utc": iso(t), "equity_brl_scale": round((cash + sum(pos["qty"]*pos["mark"] for pos in positions.values()))*FX, 6)})
            continue
        recovering = outage_active
        outage_active = False
        d = datetime.fromtimestamp(t/1000, timezone.utc).date()
        if d != day:
            day, day_start, halted = d, cash + sum(pos["qty"]*pos["mark"] for pos in positions.values()), False
        if recovering:
            # No protective orders are assumed to exist. Close at the first observed open after recovery.
            for s in list(positions):
                i = idx[s].get(t)
                if i is None: continue
                pos, row = positions[s], series[s][i]
                raw = row["o"]; exit_price = raw*(1-IMPACT); fee = pos["qty"]*exit_price*CONFIG["fees_per_side"]
                cash += pos["qty"]*exit_price-fee
                pnl = pos["qty"]*(exit_price-pos["entry"])-pos["entry_fee"]-fee
                notional = pos["qty"]*pos["entry"]
                trades.append({"strategy": name, "symbol": s, "entry_utc": iso(pos["entry_t"]), "exit_utc": iso(t),
                    "entry_price_usdt": round(pos["entry"],10), "exit_price_usdt": round(exit_price,10), "notional_brl_scale": round(notional*FX,4),
                    "pnl_brl_scale": round(pnl*FX,6), "net_return_on_notional": pnl/notional if notional else 0,
                    "bars_held": pos["held"], "exit_reason": "data_outage_recovery", "fees_included": True})
                del positions[s]
        # First process exits on the current candle. If stop and target logic can conflict,
        # the stop wins; stops fill at an adverse gap open or stop price with market friction.
        for s in list(positions):
            i = idx[s].get(t)
            if i is None: continue
            row, pos = series[s][i], positions[s]
            pos["held"] += 1
            reason, raw_exit = None, None
            if row["l"] <= pos["stop"]:
                reason, raw_exit = "stop", min(pos["stop"], row["o"])
            elif name == "mean_reversion" and row["mid"] is not None and row["h"] >= row["mid"]:
                reason, raw_exit = "mean_reversion_target", max(row["o"], row["mid"])
            elif name != "mean_reversion" and row["atr"] is not None:
                trail = pos.get("trail_stop")
                if trail is not None and row["l"] <= trail:
                    reason, raw_exit = "trailing_stop", min(trail, row["o"])
            if reason is None and pos["held"] >= p["max_hold_bars"]:
                reason, raw_exit = "time_exit", row["c"]
            if reason:
                exit_price = raw_exit*(1-IMPACT)
                fee = pos["qty"]*exit_price*CONFIG["fees_per_side"]
                cash += pos["qty"]*exit_price - fee
                pnl = pos["qty"]*(exit_price-pos["entry"]) - pos["entry_fee"] - fee
                notional = pos["qty"]*pos["entry"]
                trades.append({"strategy": name, "symbol": s, "entry_utc": iso(pos["entry_t"]), "exit_utc": iso(t),
                    "entry_price_usdt": round(pos["entry"], 10), "exit_price_usdt": round(exit_price, 10), "notional_brl_scale": round(notional*FX, 4),
                    "pnl_brl_scale": round(pnl*FX, 6), "net_return_on_notional": pnl/notional if notional else 0,
                    "bars_held": pos["held"], "exit_reason": reason, "fees_included": True})
                del positions[s]
        # Entries use a closed signal bar and current candle open (one full bar of delay).
        if not halted and not recovering:
            for s, pos in positions.items():
                i = idx[s].get(t)
                if i is not None:
                    row = series[s][i]
                    pos["mark"] = row["c"]
                    if name != "mean_reversion" and row["atr"] is not None:
                        pos["peak"] = max(pos["peak"], row["c"])
                        pos["trail_stop"] = pos["peak"] - p["trail_atr"]*row["atr"]
            marked = cash + sum(pos["qty"]*pos["mark"] for pos in positions.values())
            for s, rows in series.items():
                i = idx[s].get(t)
                if i is None or s in positions or i == 0: continue
                previous, row = rows[i-1], rows[i]
                if previous["t"] + 3_600_000 != t or not previous["signal"] or previous["atr"] is None: continue
                if row["t"] < utc_ms("2021-07-01"): continue
                if marked <= day_start*(1-CONFIG["daily_loss_limit"]):
                    halted = True; break
                entry = row["o"]*(1+IMPACT)
                stop = max(0.00000001, previous["c"] - p["stop_atr"]*previous["atr"])
                if entry <= stop: continue
                stop_dist = max(0.003, (entry-stop)/entry)
                max_notional = min(marked*CONFIG["max_position_fraction"], marked*CONFIG["risk_fraction_per_trade"]/stop_dist, cash/(1+CONFIG["fees_per_side"]))
                step = CONFIG["lot_step_by_symbol"][s]
                qty = math.floor((max_notional/entry)/step)*step
                max_notional = qty*entry
                if max_notional < CONFIG["min_notional_usdt"]: continue
                fee = max_notional*CONFIG["fees_per_side"]
                cash -= max_notional + fee
                pos = {"qty": qty, "entry": entry, "entry_t": t, "stop": stop,
                    "peak": row["c"], "trail_stop": None, "mark": row["c"], "held": 0, "entry_fee": fee}
                # A stop can be touched during the same candle as an opening fill.
                if row["l"] <= stop:
                    raw_exit = min(row["o"], stop); exit_price = raw_exit*(1-IMPACT)
                    exit_fee = qty*exit_price*CONFIG["fees_per_side"]
                    cash += qty*exit_price-exit_fee
                    pnl = qty*(exit_price-entry)-fee-exit_fee
                    trades.append({"strategy": name, "symbol": s, "entry_utc": iso(t), "exit_utc": iso(t),
                        "entry_price_usdt": round(entry,10), "exit_price_usdt": round(exit_price,10), "notional_brl_scale": round(max_notional*FX,4),
                        "pnl_brl_scale": round(pnl*FX,6), "net_return_on_notional": pnl/max_notional if max_notional else 0,
                        "bars_held": 0, "exit_reason": "same_bar_stop_conservative", "fees_included": True})
                    marked = cash + sum(x["qty"]*x["mark"] for x in positions.values())
                    if marked <= day_start*(1-CONFIG["daily_loss_limit"]): halted = True
                else:
                    positions[s] = pos
                marked = cash + sum(x["qty"]*(series[xs][idx[xs][t]]["c"] if t in idx[xs] else x["mark"])
                                    for xs, x in positions.items())
        # Mark positions at each closed bar, using no future data.
        marked = cash + sum(pos["qty"]*pos["mark"] for pos in positions.values())
        curve.append({"timestamp_utc": iso(t), "equity_brl_scale": round(marked*FX, 6)})
    # Liquidate residuals at final available close to produce a realizable end mark.
    for s, pos in list(positions.items()):
        last = max((r for r in series[s] if r["t"] < hi), key=lambda r: r["t"])
        row = last; raw = row["c"]; exit_price = raw*(1-IMPACT)
        fee = pos["qty"]*exit_price*CONFIG["fees_per_side"]
        cash += pos["qty"]*exit_price - fee
        pnl = pos["qty"]*(exit_price-pos["entry"]) - pos["entry_fee"] - fee
        notional = pos["qty"]*pos["entry"]
        trades.append({"strategy": name, "symbol": s, "entry_utc": iso(pos["entry_t"]), "exit_utc": iso(row["t"]),
            "entry_price_usdt": round(pos["entry"],10), "exit_price_usdt": round(exit_price,10), "notional_brl_scale": round(notional*FX,4),
            "pnl_brl_scale": round(pnl*FX,6), "net_return_on_notional": pnl/notional if notional else 0,
            "bars_held": pos["held"], "exit_reason": "end_of_data", "fees_included": True})
    if curve: curve[-1]["equity_brl_scale"] = round(cash*FX, 6)
    return trades, curve, series


def period_metrics(trades, curve, start, end, initial=500.0):
    lo, hi = utc_ms(start), utc_ms(end)
    ts = [x for x in trades if lo <= utc_ms(x["exit_utc"][:10]) < hi]
    cs = [x for x in curve if lo <= utc_ms(x["timestamp_utc"][:10]) < hi]
    if not cs:
        return {"trades": len(ts), "net_return_pct": None, "net_pnl_brl_scale": None, "profit_factor": None,
                "max_drawdown_pct": None, "expectancy_per_trade_pct": None, "expectancy_ci95_pct": None}
    # The period is chained from the actual prior curve level, with 500 as the first-ever base.
    pre = [x for x in curve if utc_ms(x["timestamp_utc"][:10]) < lo]
    base = pre[-1]["equity_brl_scale"] if pre else initial
    end_eq = cs[-1]["equity_brl_scale"]
    vals = [base] + [x["equity_brl_scale"] for x in cs]
    peak, maxdd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        if peak: maxdd = min(maxdd, v/peak-1)
    wins = sum(max(0, x["pnl_brl_scale"]) for x in ts)
    losses = sum(min(0, x["pnl_brl_scale"]) for x in ts)
    pf = wins/abs(losses) if losses else None
    rets = [x["net_return_on_notional"] for x in ts]
    exp = statistics.mean(rets)*100 if rets else None
    ci = bootstrap_mean_ci(rets)
    return {"trades": len(ts), "net_return_pct": (end_eq/base-1)*100 if base else None,
            "net_pnl_brl_scale": end_eq-base, "ending_equity_brl_scale": end_eq, "profit_factor": pf,
            "max_drawdown_pct": maxdd*100, "expectancy_per_trade_pct": exp, "expectancy_ci95_pct": ci,
            "wins": sum(x["pnl_brl_scale"] > 0 for x in ts), "losses": sum(x["pnl_brl_scale"] <= 0 for x in ts)}


def bootstrap_mean_ci(values, reps=3000, seed=9701):
    if len(values) < 2: return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values)/len(values)*100 for _ in range(reps))
    return [means[int(0.025*reps)], means[int(0.975*reps)]]


def max_drawdown(equity):
    peak, result = equity[0], 0.0
    for x in equity:
        peak = max(peak, x); result = min(result, x/peak-1 if peak else 0)
    return result


def buy_hold(data_dir, start, end, initial=500.0):
    lo, hi = utc_ms(start), utc_ms(end)
    names = CONFIG["symbols"]
    end_values, starts = [], []
    for s in names:
        bars = [b for b in read_bars(data_dir, s) if lo <= b["t"] < hi]
        if not bars: return None
        starts.append(bars[0]["o"]*(1+IMPACT)*(1+CONFIG["fees_per_side"]))
        end_values.append(bars[-1]["c"]*(1-IMPACT)*(1-CONFIG["fees_per_side"]))
    # Equal-weight, fully invested buy and hold, with one conservative round trip per asset.
    return {"net_return_pct": (sum((initial/len(names))/starts[i]*end_values[i] for i in range(len(names)))/initial-1)*100,
            "trades": len(names)*2, "profit_factor": None, "max_drawdown_pct": None,
            "expectancy_per_trade_pct": None, "expectancy_ci95_pct": None,
            "note": "Buy-and-hold equal-weight; only endpoint costs charged, intraperiod drawdown not estimated."}


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: path.write_text("", encoding="utf-8"); return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def run_backtest(args):
    data_dir, out = Path(args.data_dir), Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    periods = CONFIG["periods_utc"]
    metrics, alltrades = {}, []
    for name in STRATEGIES:
        prepared = {s: features(read_bars(data_dir, s), name) for s in CONFIG["symbols"]}
        trades, curve = [], []
        for period_name, (start, end) in periods.items():
            period_trades, period_curve, _ = backtest_strategy(name, data_dir, INITIAL_USDT, start, end, prepared, False)
            trades.extend(period_trades); curve.extend(period_curve)
            metrics.setdefault(name, {})[period_name] = period_metrics(period_trades, period_curve, start, end, INITIAL_BRL)
            stress_trades, stress_curve, _ = backtest_strategy(name, data_dir, INITIAL_USDT, start, end, prepared, True)
            metrics[name][period_name+"_availability_stress"] = period_metrics(stress_trades, stress_curve, start, end, INITIAL_BRL)
            write_csv(out / f"{name}_{period_name}_equity.csv", period_curve)
            write_csv(out / f"{name}_{period_name}_availability_stress_equity.csv", stress_curve)
            write_csv(out / f"{name}_{period_name}_availability_stress_trades.csv", stress_trades)
        metrics[name]["buy_and_hold_oos"] = buy_hold(data_dir, *periods["out_of_sample"], INITIAL_BRL)
        write_csv(out / f"{name}_trades.csv", trades)
        write_csv(out / f"{name}_equity.csv", curve)
        alltrades.extend(trades)
        print(f"{name}: OOS {metrics[name]['out_of_sample']}")
    write_csv(out / "all_trades.csv", alltrades)
    metadata = json.loads((data_dir/"source_metadata.json").read_text(encoding="utf-8")) if (data_dir/"source_metadata.json").exists() else {}
    metadata.setdefault("brl_usdt_reference", {"brl_per_usdt": FX, "reference_date": CONFIG["brl_per_usdt_reference_date"],
        "source": "Banco Central do Brasil PTAX USD venda; USDT aproximado como USD; não é cotação executável."})
    if (data_dir/"source_metadata.json").exists():
        (data_dir/"source_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(data_dir.glob("*_1h.csv"))}
    result = {"generated_utc": datetime.now(timezone.utc).isoformat(), "config": CONFIG, "data_metadata": metadata,
              "sha256": hashes, "cost_per_side_pct": FRICTION*100, "cost_round_trip_pct": FRICTION*200,
              "metrics": metrics, "null_strategy": {"name": "cash / no trades", "return_pct": 0.0, "risk": 0.0},
              "limitations": ["Intervalos por bootstrap de operações tratam operações como independentes; autocorrelação e seleção de estratégias não estão cobertas.",
                              "Exposição é somente comprada; sem alavancagem, short, funding, saque, imposto ou conversão BRL/USDT.",
                              "Spread, slippage e comissão são hipóteses fixas por lado, não execução histórica observada.",
                              "Ativos escolhidos hoje introduzem viés de sobrevivência; candles OHLC não reproduzem fila, profundidade ou gaps intrabar.",
                              "Sinais e parâmetros são fixos, sem otimização; o teste fora da amostra cobre 2025-01-01 até 2026-10-08 UTC."]}
    (out/"metrics.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"Resultados e hashes SHA-256 em {out.resolve()}")


def make_dashboard(args):
    d = Path(args.results_dir); result = json.loads((d/"metrics.json").read_text(encoding="utf-8"))
    rows = []
    series_data = {}
    for s, m in result["metrics"].items():
        o, bh = m["out_of_sample"], m["buy_and_hold_oos"]
        pf = "—" if o["profit_factor"] is None else f"{o['profit_factor']:.2f}"
        expectancy = "—" if o["expectancy_per_trade_pct"] is None else f"{o['expectancy_per_trade_pct']:.3f}%"
        ci = "—" if not o["expectancy_ci95_pct"] else f"[{o['expectancy_ci95_pct'][0]:.3f}%, {o['expectancy_ci95_pct'][1]:.3f}%]"
        stress = m["out_of_sample_availability_stress"]
        rows.append(f"<tr><th>{s}</th><td>{o['net_return_pct']:.2f}%</td><td>{o['net_pnl_brl_scale']:.2f}</td><td>{o['trades']}</td><td>{pf}</td><td>{o['max_drawdown_pct']:.2f}%</td><td>{expectancy}</td><td>{ci}</td><td>{stress['net_return_pct']:.2f}%</td><td>{bh['net_return_pct']:.2f}%</td></tr>")
        series_data[s] = {}
        for period in result["config"]["periods_utc"]:
            pth = d / f"{s}_{period}_equity.csv"
            vals = list(csv.DictReader(pth.open(encoding="utf-8")))
            stride = max(1, math.ceil(len(vals)/600))
            sample = vals[::stride]
            if vals and sample[-1] != vals[-1]: sample.append(vals[-1])
            series_data[s][period] = [{"t": x["timestamp_utc"], "e": float(x["equity_brl_scale"])} for x in sample]
    body = "\n".join(rows)
    payload = json.dumps(series_data, ensure_ascii=False).replace("<", "\\u003c")
    html = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Laboratório quantitativo cripto</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1180px;margin:32px auto;padding:0 18px;color:#17212b;background:#f5f7fa}}h1{{font-size:2rem}}.box{{background:white;padding:18px;border-radius:12px;margin:16px 0;box-shadow:0 2px 10px #10203012}}table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{text-align:right;padding:10px;border-bottom:1px solid #e3e8ef}}th:first-child,td:first-child{{text-align:left}}small,.muted{{color:#526170}}.warning{{border-left:5px solid #c47900}}code{{background:#eef2f6;padding:2px 5px;border-radius:4px}}select{{padding:8px;margin:4px 12px 12px 0;border:1px solid #b8c4d0;border-radius:6px;background:white}}svg{{width:100%;height:auto;min-height:220px}}.chartline{{fill:none;stroke:#1769aa;stroke-width:3}}.grid{{stroke:#dce3eb;stroke-width:1}}.axis{{fill:#526170;font-size:12px}}@media(max-width:740px){{.scroll{{overflow-x:auto}}table{{min-width:1080px}}}}</style>
<body><h1>Laboratório quantitativo de cripto</h1><p class="muted">Binance Spot · BTC, ETH e SOL · candles de 1h · saldo simulado de R$500 por janela</p>
<section class="box"><h2>Resultado fora da amostra</h2><p>Período: 1 jan. 2025 a 8 out. 2026 UTC. Valores em R$ são uma escala aplicada aos retornos cotados em USDT.</p><div class="scroll"><table><thead><tr><th>Estratégia</th><th>Retorno líquido</th><th>P&amp;L (R$ escala)</th><th>Operações</th><th>Profit factor</th><th>Drawdown máx.</th><th>Expectativa/operação</th><th>IC 95% expectativa</th><th>Com indisponibilidade</th><th>Buy-and-hold</th></tr></thead><tbody>{body}</tbody></table></div><p class="muted">Nula: manter caixa, retorno 0%. Buy-and-hold: pesos iguais em BTC/ETH/SOL, custos de ida e volta, sem estimativa de drawdown intraperíodo. O intervalo de expectativa é bootstrap por operação; supõe independência e não corrige seleção de estratégias.</p></section>
<section class="box"><h2>Curva de saldo</h2><label for="strat">Estratégia</label><select id="strat"></select><label for="period">Janela</label><select id="period"><option value="development">Desenvolvimento · 2021–2023</option><option value="validation">Validação · 2024</option><option value="out_of_sample" selected>Fora da amostra · 2025–2026</option></select><div id="summary" class="muted"></div><svg id="chart" viewBox="0 0 900 320" role="img" aria-label="Curva horária do saldo simulado"></svg></section>
<section class="box"><h2>Custos e disponibilidade</h2><p>Taxa Spot regular: 0,10% por lado. Hipóteses conservadoras adicionais: spread 0,05% e slippage 0,05% por lado; custo combinado 0,20% por lado (0,40% ida e volta). O sinal só entra na abertura do candle horário seguinte. Candles ausentes bloqueiam novas entradas até a sequência voltar a ficar contínua.</p><p>A coluna de estresse injeta uma indisponibilidade determinística de 6 horas a cada bloco de 30 dias; durante a falha nenhum sinal é processado e posições virtuais são liquidadas na primeira abertura observada após o retorno. É um cenário hipotético de falha do feed, não uma ocorrência histórica observada.</p></section>
<section class="box warning"><h2>Pesquisa, sem promessa de lucro</h2><p>Nenhuma candidata apresentou retorno líquido positivo no teste fora da amostra. O momentum ficou perto de zero e seu intervalo inclui zero; as outras duas tiveram expectativa negativa. Os dados e o modelo não demonstram lucro futuro.</p><p>Sem alavancagem, martingale ou grid ilimitado. O paper trading usa apenas dados públicos e nunca envia ordens; suas proteções são simuladas e não protegem uma conta real. A escala usa PTAX de referência para aproximar USDT em reais, mas exclui spread/custos de conversão, depósitos, saques e impostos.</p><p>Dados, operações e metodologia: <code>data/</code>, <code>results/</code> e <code>research.md</code>. Atualizado em {result['generated_utc']}.</p></section>
<script>const D={payload};const S=document.getElementById('strat'),P=document.getElementById('period'),G=document.getElementById('chart');Object.keys(D).forEach(x=>S.add(new Option(x,x)));function draw(){{const a=D[S.value][P.value]||[];if(!a.length){{G.innerHTML='';return}}const W=900,H=320,L=64,R=18,T=16,B=38,vals=a.map(x=>x.e),lo=Math.min(500,...vals),hi=Math.max(500,...vals),span=hi-lo||1;const X=i=>L+i*(W-L-R)/Math.max(1,a.length-1),Y=v=>T+(hi-v)*(H-T-B)/span;let h='';for(let k=0;k<5;k++){{const v=lo+(hi-lo)*k/4,y=Y(v);h+=`<line class="grid" x1="${{L}}" x2="${{W-R}}" y1="${{y}}" y2="${{y}}"/><text class="axis" x="4" y="${{y+4}}">R$ ${{v.toFixed(0)}}</text>`}}const y0=Y(500);h+=`<line class="grid" x1="${{L}}" x2="${{W-R}}" y1="${{y0}}" y2="${{y0}}" stroke-dasharray="5 4"/>`;const d=a.map((x,i)=>(i?'L':'M')+X(i).toFixed(1)+','+Y(x.e).toFixed(1)).join(' ');h+=`<path class="chartline" d="${{d}}"/><text class="axis" x="${{L}}" y="${{H-8}}">${{a[0].t.slice(0,10)}}</text><text class="axis" text-anchor="end" x="${{W-R}}" y="${{H-8}}">${{a[a.length-1].t.slice(0,10)}}</text>`;G.innerHTML=h;const ret=(a[a.length-1].e/500-1)*100;document.getElementById('summary').textContent=`Saldo simulado: R$500,00 → R$${{a[a.length-1].e.toFixed(2)}} (${{ret.toFixed(2)}}%). Os pontos são candles horários, reduzidos para exibição.`}}S.onchange=P.onchange=draw;draw();</script></body></html>'''
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Dashboard salvo em {Path(args.output).resolve()}")


def paper(args):
    symbol, strategy = args.symbol, args.strategy
    if symbol not in CONFIG["symbols"]: raise SystemExit("Par fora da lista do laboratório.")
    folder = Path(args.state_dir); folder.mkdir(parents=True, exist_ok=True)
    state_path, events_path = folder/"state.json", folder/"events.csv"
    if state_path.exists(): state = json.loads(state_path.read_text(encoding="utf-8"))
    else: state = {"strategy": strategy, "symbol": symbol, "cash": INITIAL_USDT, "position": None, "day": None, "day_start": INITIAL_USDT, "created_utc": datetime.now(timezone.utc).isoformat()}
    if state["strategy"] != strategy or state["symbol"] != symbol: raise SystemExit("Estado existente usa outro par/estratégia; escolha outro --state-dir.")
    fields = ["time_utc", "event", "strategy", "symbol", "price", "cash", "equity", "detail"]
    def log(event, price, detail):
        exists = events_path.exists()
        with events_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader() if not exists else None
            equity = state["cash"] + (state["position"]["qty"]*price if state["position"] else 0)
            w.writerow({"time_utc": datetime.now(timezone.utc).isoformat(), "event": event, "strategy": strategy, "symbol": symbol,
                        "price": price, "cash": state["cash"], "equity": equity, "detail": detail})
    print("Paper trading (somente simulação). Ctrl+C encerra; nenhum endpoint de ordem é usado.")
    while True:
        if (folder/"KILL").exists(): print("KILL switch detectado; encerrando."); break
        try:
            data, _ = get_json("/api/v3/klines", {"symbol": symbol, "interval": "1h", "limit": 260})
            now_ms = int(time.time()*1000)
            closed = [k for k in data if k[6] < now_ms]
            if len(closed) < 220: raise RuntimeError("Série pública insuficiente")
            bars = [{"t": int(k[0]), "o":float(k[1]), "h":float(k[2]), "l":float(k[3]), "c":float(k[4]), "v":float(k[5]), "ct":int(k[6])} for k in closed]
            rows = features(bars, strategy); signal = rows[-1]; prev = rows[-2]
            ts = datetime.fromtimestamp(signal["t"]/1000, timezone.utc); d = ts.date().isoformat()
            if (now_ms - signal["ct"]) > 3_600_000: raise RuntimeError("Último candle fechado está vencido")
            if state.get("last_candle_utc") == iso(signal["t"]):
                time.sleep(args.poll_seconds); continue
            if d != state["day"]: state["day"], state["day_start"] = d, state["cash"] + (state["position"]["qty"]*signal["c"] if state["position"] else 0)
            pos = state["position"]
            if pos:
                pos["held"] += 1
                reason, raw_exit = None, None
                if signal["l"] <= pos["stop"]:
                    reason, raw_exit = "stop", min(signal["o"], pos["stop"])
                elif strategy == "mean_reversion" and signal["mid"] is not None and signal["h"] >= signal["mid"]:
                    reason, raw_exit = "mean_reversion_target", max(signal["o"], signal["mid"])
                elif strategy != "mean_reversion" and pos.get("trail_stop") is not None and signal["l"] <= pos["trail_stop"]:
                    reason, raw_exit = "trailing_stop", min(signal["o"], pos["trail_stop"])
                elif pos["held"] >= CONFIG["strategies"][strategy]["max_hold_bars"]:
                    reason, raw_exit = "time_exit", signal["c"]
                if reason:
                    px = raw_exit*(1-FRICTION)
                    state["cash"] += pos["qty"]*px
                    log("paper_exit", px, reason); state["position"] = None
                elif strategy != "mean_reversion" and signal["atr"]:
                    pos["peak"] = max(pos["peak"], signal["c"])
                    pos["trail_stop"] = pos["peak"] - CONFIG["strategies"][strategy]["trail_atr"]*signal["atr"]
            equity = state["cash"] + (state["position"]["qty"]*signal["c"] if state["position"] else 0)
            daily_block = equity <= state["day_start"]*(1-CONFIG["daily_loss_limit"])
            if not state["position"] and not daily_block and prev["signal"] and prev["atr"]:
                entry = signal["c"]*(1+IMPACT); stop = max(1e-8, prev["c"]-CONFIG["strategies"][strategy]["stop_atr"]*prev["atr"])
                if entry <= stop:
                    state["last_candle_utc"] = iso(signal["t"])
                    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
                    continue
                risk_frac = min(CONFIG["max_position_fraction"], CONFIG["risk_fraction_per_trade"]*entry/max(entry-stop, 0.003*entry))
                notional = min(equity*risk_frac, state["cash"]/(1+CONFIG["fees_per_side"]))
                step = CONFIG["lot_step_by_symbol"][symbol]
                qty = math.floor((notional/entry)/step)*step
                notional = qty*entry
                if notional >= CONFIG["min_notional_usdt"]:
                    state["cash"]-=notional*(1+CONFIG["fees_per_side"])
                    state["position"]={"qty":qty,"entry":entry,"stop":stop,"opened_utc":iso(signal["t"]),"held":0,
                        "peak":signal["c"],"trail_stop":None}
                    log("paper_entry", entry, "sinal em candle fechado; execução simulada após latência")
            state["last_candle_utc"] = iso(signal["t"])
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            print(f"{d} {symbol} close={signal['c']:.6g} posição={'sim' if state['position'] else 'não'}; ciclo atualizado")
            remaining = args.poll_seconds
            while remaining > 0 and not (folder/"KILL").exists():
                step = min(5, remaining); time.sleep(step); remaining -= step
        except KeyboardInterrupt: break
        except (urllib.error.URLError, TimeoutError, RuntimeError) as e:
            print(f"Sem atualização/entrada por erro ou dado stale: {e}", file=sys.stderr)
            time.sleep(max(args.poll_seconds, 60))
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(required=True)
    d = sub.add_parser("download"); d.add_argument("--start", default="2021-01-01"); d.add_argument("--end", default="2026-10-08"); d.add_argument("--data-dir", default=str(ROOT/"data")); d.set_defaults(func=download)
    b = sub.add_parser("backtest"); b.add_argument("--data-dir", default=str(ROOT/"data")); b.add_argument("--out-dir", default=str(ROOT/"results")); b.set_defaults(func=run_backtest)
    h = sub.add_parser("dashboard"); h.add_argument("--results-dir", default=str(ROOT/"results")); h.add_argument("--output", default=str(ROOT/"dashboard.html")); h.set_defaults(func=make_dashboard)
    q = sub.add_parser("paper"); q.add_argument("--strategy", choices=STRATEGIES, required=True); q.add_argument("--symbol", choices=CONFIG["symbols"], default="BTCUSDT"); q.add_argument("--state-dir", default=str(ROOT/"paper")); q.add_argument("--poll-seconds", type=int, default=3600); q.set_defaults(func=paper)
    args = p.parse_args(); args.func(args)


if __name__ == "__main__": main()
