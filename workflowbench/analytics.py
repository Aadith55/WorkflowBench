"""Small statistical summaries for experiment history."""
import math
from statistics import mean, median
from typing import Any

def wilson_interval(successes: int, total: int, z: float = 1.96):
    if total <= 0:
        return None
    if not 0 <= successes <= total:
        raise ValueError("successes must be between zero and total")
    if z <= 0:
        raise ValueError("z must be positive")
    p = successes / total
    d = 1 + z*z/total
    centre = (p + z*z/(2*total))/d
    margin = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))/d
    return max(0.0, centre-margin), min(1.0, centre+margin)

def summarise_runs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "successes": 0, "success_rate": None, "wilson_95": None}
    successes = sum(int(row.get("task_success", 0)) for row in rows)
    latencies = [float(r["latency_ms"]) for r in rows if r.get("latency_ms") is not None]
    costs = [float(r["estimated_cost_usd"]) for r in rows if r.get("estimated_cost_usd") is not None]
    successful_costs = [float(r["estimated_cost_usd"]) for r in rows
                        if int(r.get("task_success", 0)) == 1 and r.get("estimated_cost_usd") is not None]
    return {"n": len(rows), "successes": successes, "success_rate": successes/len(rows),
            "wilson_95": wilson_interval(successes, len(rows)),
            "mean_latency_ms": mean(latencies) if latencies else None,
            "median_latency_ms": median(latencies) if latencies else None,
            "known_cost_runs": len(costs),
            "known_cost_successes": len(successful_costs),
            "cost_per_success_usd": (sum(successful_costs)/len(successful_costs)
                                     if successful_costs else None)}

def mcnemar_exact(baseline: list[dict[str, Any]], verified: list[dict[str, Any]]) -> dict[str, Any]:
    a = {r["case_id"]: int(r.get("task_success", 0)) for r in baseline}
    bmap = {r["case_id"]: int(r.get("task_success", 0)) for r in verified}
    common = sorted(a.keys() & bmap.keys())
    b = sum(a[k] == 0 and bmap[k] == 1 for k in common)
    c = sum(a[k] == 1 and bmap[k] == 0 for k in common)
    n = b+c
    p = 1.0 if n == 0 else min(1.0, 2*sum(math.comb(n,k) for k in range(min(b,c)+1))/(2**n))
    return {"matched_cases": len(common), "baseline_only_failures": b,
            "verified_only_failures": c, "discordant_pairs": n, "exact_two_sided_p": p}
