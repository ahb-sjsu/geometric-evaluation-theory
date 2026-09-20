#!/usr/bin/env python3
"""Collect the G9b cell results off the cluster and grade them against the seal.

Same shape as the G9 harvester and for the same reason: a pod is garbage
collected after its job succeeds and takes its log with it, which cost one
cell's result in G9 before the harvester persisted records as it found them.
A saved record is the copy of record.
"""
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
NAMESPACE = "ssu-atlas-ai"
OUTDIR = os.path.join(HERE, "results")
BEGIN, END = "===RECORD-BEGIN===", "===RECORD-END==="
FLOOR = 50            # anti-vacuity, PREREG-G9B.md Section 4
CHAIN = {"y1_epa", "y2_first_down"}


def kubectl(*args):
    return subprocess.run(["kubectl", "-n", NAMESPACE, *args],
                          capture_output=True, text=True).stdout


def jobs():
    return sorted(kubectl("get", "jobs", "-l", "app=get-g9b", "-o",
                          "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}").split())


def pod_log(job):
    pods = kubectl("get", "pods", "-l", "job-name=%s" % job, "-o",
                   "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}").split()
    for p in pods:
        log = kubectl("logs", p, "--tail=-1")
        if BEGIN in log:
            return log
    return ""


def extract(log):
    if BEGIN not in log or END not in log:
        return None, None
    body = log.split(BEGIN, 1)[1].split(END, 1)[0]
    m = re.search(r"\{.*\}", body, re.S)
    if not m:
        return None, None
    return json.loads(m.group(0)), dict(re.findall(r"([0-9a-f]{64})\s+(\S+)", body))


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rows = []
    for name in jobs():
        saved = os.path.join(OUTDIR, "%s.json" % name)
        rec, shas = extract(pod_log(name))
        if rec is None and os.path.exists(saved):
            blob = json.load(open(saved))
            rec, shas = blob.get("record"), blob.get("sources_sha256")
        if rec is None:
            rows.append({"cell": name, "state": "no record"})
            continue
        with open(saved, "w") as f:
            json.dump({"record": rec, "sources_sha256": shas}, f, indent=1, sort_keys=True)
        coords = rec["coords"]
        rows.append({
            "cell": name, "coords": coords, "k": len(coords),
            "in_chain": CHAIN.issubset(set(coords)),
            "n_testable": rec["n_testable"], "n_violated": rec["n_violated"],
            "p_obs": rec["p_obs"], "p_null_mean": rec["p_null_mean"],
            "p_null_sd": rec["p_null_sd"], "p_value_perm": rec["p_value_perm"],
            "graded": rec["n_testable"] >= FLOOR,
            "state": "ok",
        })
    with open(os.path.join(HERE, "results_summary.json"), "w") as f:
        json.dump(rows, f, indent=1, sort_keys=True)

    ok = [r for r in rows if r.get("state") == "ok"]
    print("%-24s %2s %6s %8s %8s %8s %6s %s" %
          ("cell", "k", "test", "obs", "null", "p", "chain", "above null?"))
    print("-" * 82)
    for r in sorted(ok, key=lambda r: (r["k"], r["cell"])):
        print("%-24s %2d %6d %8.4f %8.4f %8.4f %6s %s" % (
            r["cell"], r["k"], r["n_testable"], r["p_obs"], r["p_null_mean"],
            r["p_value_perm"], "yes" if r["in_chain"] else "",
            "ABOVE" if r["p_obs"] > r["p_null_mean"] else "below"))
    missing = [r for r in rows if r.get("state") != "ok"]
    if missing:
        print()
        print("no record yet:", ", ".join(r["cell"] for r in missing))
    print()
    print("records held: %d of %d" % (len(ok), len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
