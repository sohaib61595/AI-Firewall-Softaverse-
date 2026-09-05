"""
evaluate_test_data.py
=====================
Evaluates the AI Firewall ML model and Tier-1 regex engine against data/test_data.jsonl.
Generates comprehensive accuracy, recall, false-positive/negative breakdown, and per-attack-type statistics.
"""

import os
import sys
import json
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import io

if isinstance(sys.stdout, io.TextIOWrapper) and (sys.stdout.encoding or '').lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

from backend.core.model import firewall_model

TEST_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "test_data.jsonl")


def evaluate():
    if not os.path.exists(TEST_DATA_PATH):
        print(f"[ERROR] Test data file not found at: {TEST_DATA_PATH}")
        return

    print("=" * 65)
    print("      AI FIREWALL EVALUATION ON data/test_data.jsonl")
    print("=" * 65)

    firewall_model.load()

    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    total = len(records)
    print(f"\n[INFO] Loaded {total} evaluation prompts from test_data.jsonl\n")

    tp = 0  # Malicious correctly BLOCKED
    tn = 0  # Benign correctly SAFE
    fp = 0  # Benign incorrectly BLOCKED
    fn = 0  # Malicious incorrectly SAFE (missed)

    by_attack = defaultdict(lambda: {"total": 0, "blocked": 0, "safe": 0})
    fn_samples = []
    fp_samples = []

    for item in records:
        prompt_id = item.get("id", "")
        prompt = item.get("prompt", "")
        label = item.get("label", "").lower()
        attack_type = item.get("attack_type", "none")

        result = firewall_model.predict(prompt)
        is_blocked = (result.verdict == "BLOCKED")
        is_malicious = (label == "malicious")

        by_attack[attack_type]["total"] += 1
        if is_blocked:
            by_attack[attack_type]["blocked"] += 1
        else:
            by_attack[attack_type]["safe"] += 1

        if is_malicious and is_blocked:
            tp += 1
        elif not is_malicious and not is_blocked:
            tn += 1
        elif not is_malicious and is_blocked:
            fp += 1
            fp_samples.append({
                "id": prompt_id,
                "prompt": prompt,
                "category": result.category,
                "confidence": result.confidence,
                "risk_score": result.risk_score
            })
        elif is_malicious and not is_blocked:
            fn += 1
            fn_samples.append({
                "id": prompt_id,
                "attack_type": attack_type,
                "prompt": prompt,
                "confidence": result.confidence,
                "risk_score": result.risk_score
            })

    accuracy = (tp + tn) / total * 100
    precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    fp_rate = (fp / (fp + tn) * 100) if (fp + tn) > 0 else 0.0

    print("-" * 65)
    print("OVERALL PERFORMANCE METRICS")
    print("-" * 65)
    print(f"Total Evaluated Prompts   : {total}")
    print(f"Overall Accuracy          : {accuracy:.2f}% ({(tp + tn)}/{total})")
    print(f"Malicious Catch Rate (Rec): {recall:.2f}% ({tp}/{tp + fn})")
    print(f"Benign Retention (Spec)   : {(tn / (tn + fp) * 100):.2f}% ({tn}/{tn + fp})")
    print(f"False Positive Rate       : {fp_rate:.2f}% ({fp}/{fp + tn})")
    print(f"Precision                 : {precision:.2f}%")
    print(f"F1 Score                  : {f1:.2f}%")

    print("\n" + "-" * 65)
    print("DETECTION BREAKDOWN BY ATTACK TYPE")
    print("-" * 65)
    print(f"{'Attack Type':<20} {'Total':>7} {'Blocked':>9} {'Safe':>7} {'Catch Rate':>12}")
    print("-" * 65)
    for atype, stats in sorted(by_attack.items(), key=lambda x: -x[1]["total"]):
        t = stats["total"]
        b = stats["blocked"]
        s = stats["safe"]
        if atype == "none":
            rate_str = f"{(s / t * 100):.1f}% (Safe)"
        else:
            rate_str = f"{(b / t * 100):.1f}%"
        print(f"{atype:<20} {t:>7} {b:>9} {s:>7} {rate_str:>12}")

    print("\n" + "-" * 65)
    print(f"FALSE POSITIVES (Legitimate Prompts Blocked: {len(fp_samples)})")
    print("-" * 65)
    if not fp_samples:
        print("None! Zero false positives detected.")
    else:
        for ex in fp_samples[:10]:
            print(f"  [{ex['id']}] Flagged as {ex['category']} ({ex['confidence']}% conf):")
            print(f"    Prompt: {repr(ex['prompt'][:90])}")

    print("\n" + "-" * 65)
    print(f"FALSE NEGATIVES (Malicious Attacks Missed: {len(fn_samples)})")
    print("-" * 65)
    if not fn_samples:
        print("None! All malicious prompts were intercepted.")
    else:
        for ex in fn_samples[:10]:
            print(f"  [{ex['id']}] Type: {ex['attack_type']} | Risk: {ex['risk_score']} | Allowed as SAFE ({ex['confidence']}%):")
            print(f"    Prompt: {repr(ex['prompt'][:90])}")

    print("=" * 65)


if __name__ == "__main__":
    evaluate()
