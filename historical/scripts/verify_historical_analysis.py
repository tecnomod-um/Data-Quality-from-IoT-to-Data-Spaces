#!/usr/bin/env python3
"""Verify annotation integrity and agreement metrics using 50-digit decimal arithmetic."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, getcontext
from pathlib import Path
from annotate_historical_units import SOURCE_FIELDS, source_digest

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    args=ap.parse_args();root=args.root
    ann=json.loads((root/"docs/author_annotations.json").read_text())
    rows=list(csv.DictReader((root/"data/H2022_paired_observations.csv").open()))
    metrics=list(csv.DictReader((root/"data/paired_agreement_metrics.csv").open()))
    units={u["pollutant"]:u["effective_unit"] or "" for u in ann["units"]}
    failures=[]
    if source_digest(rows)!=ann["immutable_source_columns_sha256"]:failures.append("source fingerprint")
    if len(rows)!=12610:failures.append("row count")
    if any(r["reported_unit"] or r["device_identity"] or r["reference_identity"] for r in rows):failures.append("source null fields changed")
    if any(r["effective_unit"]!=units[r["pollutant"]] for r in rows):failures.append("effective unit mapping")
    if sum(r["pair_status"]=="complete" for r in rows)!=12168:failures.append("complete pair count")
    if sum(bool(r["effective_unit"]) and r["pair_status"]=="complete" for r in rows)!=7370:failures.append("confirmed-unit pair count")
    getcontext().prec=50
    comparisons=[]
    for metric in metrics:
        pol=metric["pollutant"]
        full=[r for r in rows if r["pollutant"]==pol]
        split=list(csv.DictReader((root/"data"/("H2022_"+pol.replace(".","_")+".csv")).open()))
        if full!=split:failures.append(pol+": split/combined discrepancy")
        complete=[r for r in full if r["pair_status"]=="complete"]
        x=[Decimal(r["reference_value"]) for r in complete]
        y=[Decimal(r["sensor_value"]) for r in complete]
        n=Decimal(len(complete));e=[a-b for a,b in zip(y,x)]
        sx=sum(x);sy=sum(y);sxx=sum(v*v for v in x);syy=sum(v*v for v in y);sxy=sum(a*b for a,b in zip(x,y))
        covariance=n*sxy-sx*sy;vx=n*sxx-sx*sx;vy=n*syy-sy*sy
        slope=covariance/vx
        exact={"bias_sensor_minus_reference":sum(e)/n,"mae":sum(abs(v) for v in e)/n,
               "rmse":(sum(v*v for v in e)/n).sqrt(),"pearson_r":covariance/(vx*vy).sqrt(),
               "ols_slope_sensor_on_reference":slope,"ols_intercept_sensor_on_reference":sy/n-slope*sx/n}
        if int(metric["n"])!=len(complete):failures.append(pol+": n")
        for name,value in exact.items():
            actual=Decimal(metric[name]);delta=abs(actual-value)
            tol=Decimal("1e-10")*max(Decimal(1),abs(value))
            comparisons.append({"pollutant":pol,"metric":name,"absolute_difference":float(delta),"passed":delta<=tol})
            if delta>tol:failures.append(pol+": "+name)
    output={"source_columns_sha256":source_digest(rows),"protected_source_columns":SOURCE_FIELDS,
        "source_columns_unchanged":source_digest(rows)==ann["immutable_source_columns_sha256"],
        "rows":len(rows),"complete_pairs":sum(r["pair_status"]=="complete" for r in rows),
        "confirmed_unit_complete_pairs":sum(bool(r["effective_unit"]) and r["pair_status"]=="complete" for r in rows),
        "pair_status_counts":dict(Counter(r["pair_status"] for r in rows)),
        "independent_numeric_check":"Decimal precision50, raw-moment formulas versus centred binary-float analysis",
        "relative_or_absolute_tolerance":1e-10,"numeric_comparisons":len(comparisons),
        "maximum_absolute_numeric_difference":max(c["absolute_difference"] for c in comparisons),
        "comparisons":comparisons,"failures":failures,
        "metrics_csv_sha256":hashlib.sha256((root/"data/paired_agreement_metrics.csv").read_bytes()).hexdigest(),
        "scope":"Numerical and provenance integrity; no independent certification of the source measurements or author assertions."}
    (root/"data/analysis_verification.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({k:v for k,v in output.items() if k not in ["comparisons","protected_source_columns"]},indent=2))
    if failures:raise SystemExit("Historical analysis verification failed")

if __name__=="__main__":main()
