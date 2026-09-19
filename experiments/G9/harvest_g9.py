#!/usr/bin/env python3
"""Collect the G9 cell results off the cluster and grade them against the seal.

Runs on Atlas. Reads each cell's pod log, pulls the record the job printed
between its markers, and writes one result file per cell plus a graded summary.

Two things this does deliberately.

It watches job status as a first-class signal, not only logs. A Job can fail
and take its pods and their logs with it, and a harvester that only greps logs
goes quiet at exactly that moment and looks like a harvester finding nothing.

It grades against the bars as sealed, and it refuses to grade a plane the
registration declared vacuous. Those planes are reported with their counts and
no verdict, which is what the registration says before any number was seen.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAMESPACE = "ssu-atlas-ai"
SUBMITTED = os.path.join(HERE, "submitted.json")
OUTDIR = os.path.join(HERE, "results")

BEGIN = "===RECORD-BEGIN==="
END = "===RECORD-END==="

# Sealed bars, PREREG-G9.md Section 6.
PASS_MARGIN = 0.10
FAIL_MARGIN = 0.02
P_MAX = 0.01


def kubectl(*args):
    return subprocess.run(["kubectl", "-n", NAMESPACE, *args],
                          capture_output=True, text=True).stdout


def job_status(name):
    out = kubectl("get", "job", name, "-o", "json")
    if not out.strip():
        return {"exists": False}
    j = json.loads(out)
    st = j.get("status", {})
    return {"exists": True,
            "succeeded": int(st.get("succeeded", 0) or 0),
            "failed": int(st.get("failed", 0) or 0),
            "active": int(st.get("active", 0) or 0),
            "created": j.get("metadata", {}).get("creationTimestamp")}


def pod_log(job):
    pods = kubectl("get", "pods", "-l", "job-name=%s" % job,
                   "-o", "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}").split()
    for p in pods:
        log = kubectl("logs", p, "--tail=-1")
        if BEGIN in log:
            return log
    return pods and kubectl("logs", pods[0], "--tail=-1") or ""


def extract(log):
    if BEGIN not in log or END not in log:
        return None, None
    body = log.split(BEGIN, 1)[1].split(END, 1)[0]
    m = re.search(r"\{.*\}", body, re.S)
    if not m:
        return None, None
    rec = json.loads(m.group(0))
    shas = dict(re.findall(r"([0-9a-f]{64})\s+(\S+)", body))
    return rec, shas


def grade(rec, carries_bar):
    if not carries_bar:
        return "NO VERDICT, plane declared vacuous before the seal"
    obs, null, p = rec["p_obs"], rec["p_null_mean"], rec["p_value_perm"]
    if obs <= null - PASS_MARGIN and p < P_MAX:
        return "PASS"
    if obs >= null - FAIL_MARGIN:
        return "FAIL"
    return "INDETERMINATE"


def main():
    if not os.path.exists(SUBMITTED):
        raise SystemExit("no submitted.json")
    cells = json.load(open(SUBMITTED))
    os.makedirs(OUTDIR, exist_ok=True)
    summary = []
    for c in cells:
        name = c["k8s_job"] or c["cell"]
        st = job_status(name)
        rec, shas = (None, None)
        if st.get("exists"):
            rec, shas = extract(pod_log(name))
        row = {"cell": c["cell"], "plane": c["plane"], "floor": c["floor"],
               "carries_bar": c["bar"], "job": name, "status": st}
        if rec is None:
            row["state"] = "no record"
            row["verdict"] = None
        else:
            row.update({"p_obs": rec["p_obs"], "p_null_mean": rec["p_null_mean"],
                        "p_null_sd": rec["p_null_sd"], "p_value_perm": rec["p_value_perm"],
                        "n_testable": rec["n_testable"], "n_violated": rec["n_violated"],
                        "n_units": rec["n_respondents"]})
            row["verdict"] = grade(rec, c["bar"])
            row["state"] = "ok"
            with open(os.path.join(OUTDIR, "%s.json" % c["cell"]), "w") as f:
                json.dump({"record": rec, "sources_sha256": shas}, f, indent=1, sort_keys=True)
        summary.append(row)

    with open(os.path.join(HERE, "results_summary.json"), "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)

    hdr = "%-26s %-5s %8s %8s %8s %7s %7s  %s" % (
        "cell", "floor", "p_obs", "null", "p_perm", "test", "viol", "verdict")
    print(hdr)
    print("-" * len(hdr))
    for r in summary:
        if r["state"] != "ok":
            print("%-26s %-5s %s" % (r["cell"], r["floor"], r["state"]))
            continue
        print("%-26s %-5d %8.4f %8.4f %8.4f %7d %7d  %s" % (
            r["cell"], r["floor"], r["p_obs"], r["p_null_mean"], r["p_value_perm"],
            r["n_testable"], r["n_violated"], r["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
