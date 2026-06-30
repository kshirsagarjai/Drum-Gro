import json
import numpy as np

TOLERANCE    = 0.200   # 200ms matching window
OFFSET_RANGE = 5.0     # search ±5 seconds
OFFSET_STEP  = 0.010   # 10ms steps


# ── Loaders ──────────────────────────────────────────────────────

def load_ground_truth(path):
    with open(path) as f:
        data = json.load(f)
    events = []
    for e in data.get("events", []):
        comp = e.get("component") or e.get("label") or e.get("type")
        t    = e.get("time") or e.get("time_sec") or e.get("onset")
        if comp in ("kick", "snare") and t is not None:
            events.append({"time_sec": float(t), "component": comp})
    events = sorted(events, key=lambda x: x["time_sec"])
    print(f"Ground truth loaded: {len(events)} kick/snare events\n")
    return events


def load_performance(path):
    with open(path) as f:
        data = json.load(f)
    return [e for e in data if e["component"] in ("kick", "snare")]


# ── Offset search (match-count optimised) ────────────────────────

def find_best_offset(gt_events, perf_events):
    gt_times   = np.array([e["time_sec"] for e in gt_events])
    perf_times = np.array([e["time_sec"] for e in perf_events])
    offsets    = np.arange(-OFFSET_RANGE, OFFSET_RANGE, OFFSET_STEP)
    best_offset, best_matches = 0.0, 0
    for offset in offsets:
        shifted = perf_times - offset
        matches = sum(1 for gt_t in gt_times if np.any(np.abs(shifted - gt_t) <= TOLERANCE))
        if matches > best_matches:
            best_matches = matches
            best_offset  = offset
    return best_offset


# ── Core metric calculator (shared) ─────────────────────────────

def _calc(gt_events, shifted_perf, label, offset_ms, note=""):
    matched_errors, correct, used = [], 0, set()

    for gt in gt_events:
        best_idx, best_diff = None, float("inf")
        for i, p in enumerate(shifted_perf):
            if i in used: continue
            d = abs(p["time_sec"] - gt["time_sec"])
            if d < best_diff:
                best_diff, best_idx = d, i
        if best_idx is not None and best_diff <= TOLERANCE:
            used.add(best_idx)
            error = shifted_perf[best_idx]["time_sec"] - gt["time_sec"]
            matched_errors.append(error)
            if shifted_perf[best_idx]["component"] == gt["component"]:
                correct += 1

    n_gt      = len(gt_events)
    n_matched = len(matched_errors)
    mae  = round(sum(abs(e) for e in matched_errors) / n_matched * 1000, 1) if n_matched else None
    bias = round(sum(matched_errors)                 / n_matched * 1000, 1) if n_matched else None
    cia  = round(correct / n_gt * 100, 1)                                    if n_gt     else None

    print(f"── {label} ──")
    if note:
        print(f"  [{note}]")
    print(f"  Offset applied      : {offset_ms} ms")
    print(f"  Ground truth events : {n_gt}")
    print(f"  Matched within 200ms: {n_matched}")
    print(f"  MAE                 : {mae} ms")
    print(f"  Timing bias         : {bias} ms  (+ = late, - = early)")
    print(f"  CIA                 : {cia}%  ({correct}/{n_gt} correct component)\n")

    return {"label": label, "offset_ms": offset_ms, "n_gt": n_gt,
            "matched": n_matched, "MAE_ms": mae, "bias_ms": bias, "CIA_pct": cia}


# ── Two metric entry points ──────────────────────────────────────

def compute_metrics(gt_events, perf_events, label):
    """Auto offset search (match-count optimised). Used for P3."""
    offset     = find_best_offset(gt_events, perf_events)
    offset_ms  = round(offset * 1000, 1)
    shifted    = [{"time_sec": e["time_sec"] - offset, "component": e["component"]}
                  for e in perf_events]
    return _calc(gt_events, shifted, label, offset_ms)


def compute_metrics_fixed_offset(gt_events, perf_events, offset_sec, label):
    """Fixed CIA-optimised offset. Used for P1 and P2."""
    offset_ms = round(offset_sec * 1000, 1)
    shifted   = [{"time_sec": e["time_sec"] - offset_sec, "component": e["component"]}
                 for e in perf_events]
    return _calc(gt_events, shifted, label, offset_ms, note="CIA-optimised offset")


# ── Ground truth ─────────────────────────────────────────────────

GT = load_ground_truth(
    r"storage\processed\1b32810d-705f-492a-80fe-a91b6a8e6375\timeline.json"
)

# ── Run all four recordings ──────────────────────────────────────

results = []

# P1 and P2: tool condition only, CIA-optimised offsets from previous run
results.append(compute_metrics_fixed_offset(
    GT, load_performance("P1_highway_tool.json"),
    offset_sec=-3.810, label="P1 Highway Tool"))

results.append(compute_metrics_fixed_offset(
    GT, load_performance("P2_highway_tool.json"),
    offset_sec=-3.330, label="P2 Highway Tool"))

# P3: both conditions, auto offset search (CIA was already sensible)
results.append(compute_metrics(GT, load_performance("P3_highway_control.json"), "P3 Highway Control"))
results.append(compute_metrics(GT, load_performance("P3_highway_tool.json"),    "P3 Highway Tool"))

# ── Final summary table ──────────────────────────────────────────

print("══ FINAL SUMMARY ═══════════════════════════════════════════════════")
print(f"{'Recording':<28} {'Offset(ms)':<12} {'MAE(ms)':<10} {'Bias(ms)':<12} {'CIA%'}")
print("-" * 70)
for r in results:
    print(f"{r['label']:<28} {str(r['offset_ms']):<12} {str(r['MAE_ms']):<10} {str(r['bias_ms']):<12} {r['CIA_pct']}")
