#!/usr/bin/env python3
"""Descriptive unweighted agreement of the unchanged printed sensor/reference pairs.

OLS y=a+b*x uses x=reference and y=sensor. Fits describe the tabulated values;
they are not applied as calibration, a correction, or a conformity decision.
PM1 is calculated only on its unconfirmed numerical scale, separately labelled.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from annotate_historical_units import source_digest

SOURCE_SLOPES={"NO2":1.11,"NO":0.98,"O3":0.98,"SO2":0.81,"CO":0.33,"PM10":0.86,"PM2.5":0.88,"PM1":1.22}
ORDER=["NO2","NO","O3","SO2","CO","PM10","PM2.5","PM1"]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    args=ap.parse_args(); root=args.root
    src=root/"data/H2022_paired_observations.csv"
    allrows=list(csv.DictReader(src.open()))
    annotation=json.loads((root/"docs/author_annotations.json").read_text())
    if source_digest(allrows)!=annotation["immutable_source_columns_sha256"]:
        raise ValueError("Source-column fingerprint mismatch")
    if any(r.get("author_annotation_id")!=annotation["annotation_id"] for r in allrows):
        raise ValueError("Run the author annotation step first")
    bypol=defaultdict(list)
    for r in allrows:bypol[r["pollutant"]].append(r)
    results, extremes, slope_diagnostics=[],[],[]
    for pol in ORDER:
        full=bypol[pol];rows=[r for r in full if r["pair_status"]=="complete"]
        x=[float(r["reference_value"]) for r in rows];y=[float(r["sensor_value"]) for r in rows]
        if any(not math.isfinite(v) for v in x+y):raise ValueError("Nonfinite numeric cell")
        n=len(rows);mx=statistics.fmean(x);my=statistics.fmean(y)
        errors=[s-r for s,r in zip(y,x)]
        xx=math.fsum((v-mx)**2 for v in x);yy=math.fsum((v-my)**2 for v in y)
        xy=math.fsum((rx-mx)*(sy-my) for rx,sy in zip(x,y))
        slope=xy/xx if xx>0 else None
        intercept=my-slope*mx if slope is not None else None
        pearson=xy/math.sqrt(xx*yy) if xx>0 and yy>0 else None
        reverse_slope=xy/yy if yy>0 else None
        unit=rows[0]["effective_unit"] or None
        result={"series_id":rows[0]["series_id"],"pollutant":pol,"rows_total":len(full),"n":n,
            "incomplete_rows":len(full)-n,"effective_unit":unit,
            "unit_basis":rows[0]["effective_unit_basis"],"author_annotation_id":annotation["annotation_id"],
            "analysis_scope":"physical_unit_descriptive_agreement" if unit else "unconfirmed_numerical_scale_only",
            "bias_sensor_minus_reference":statistics.fmean(errors),
            "mae":statistics.fmean(abs(v) for v in errors),
            "rmse":math.sqrt(statistics.fmean(v*v for v in errors)),
            "pearson_r":pearson,"ols_slope_sensor_on_reference":slope,
            "ols_intercept_sensor_on_reference":intercept,
            "reference_min":min(x),"reference_max":max(x),"sensor_min":min(y),"sensor_max":max(y),
            "distinct_reference_values":len(set(x)),"distinct_sensor_values":len(set(y)),
            "equal_pairs":sum(a==b for a,b in zip(x,y)),
            "median_absolute_error":statistics.median(abs(v) for v in errors),
            "maximum_absolute_error":max(abs(v) for v in errors),
            "quarantine_flags":rows[0]["quarantine_flags"]}
        results.append(result)
        slope_diagnostics.append({"series_id":result["series_id"],"pollutant":pol,
            "source_summary_page":29,"source_summary_slope":SOURCE_SLOPES[pol],
            "source_summary_orientation":"not established by summary heading",
            "ols_slope_sensor_on_reference":slope,
            "ols_intercept_sensor_on_reference":intercept,
            "ols_slope_reference_on_sensor":reverse_slope,
            "ols_intercept_reference_on_sensor":mx-reverse_slope*my if reverse_slope is not None else None,
            "interpretation":"Most reported summary slopes are nearer the reverse fit; numerical proximity is not proof of identical fitting population, rounding or method."})
        for rank,(r,error) in enumerate(sorted(zip(rows,errors),key=lambda v:(-abs(v[1]),int(v[0]["source_row"])))[:3],1):
            extremes.append({"series_id":r["series_id"],"pollutant":pol,"rank_by_absolute_error":rank,
                "timestamp_source":r["timestamp_source"],"sensor_value_source":r["sensor_value"],
                "reference_value_source":r["reference_value"],"signed_error":error,
                "absolute_error":abs(error),"effective_unit":unit,"source_row":int(r["source_row"]),
                "pdf_page":int(r["pdf_page"]),"page_row":int(r["page_row"]),
                "treatment":"retained; largest printed errors, not diagnosed as invalid observations"})
    def write_csv(name,records):
        with (root/"data"/name).open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    write_csv("paired_agreement_metrics.csv",results)
    write_csv("largest_absolute_errors.csv",extremes)
    write_csv("regression_direction_diagnostics.csv",slope_diagnostics)
    report={"dataset_id":"H2022","version":"1.1.0","source_pdf_sha256":annotation["source_sha256"],
        "annotated_csv_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
        "immutable_source_columns_sha256":source_digest(allrows),"author_annotation_id":annotation["annotation_id"],
        "method":{"pairing":"Pairs exactly as printed in a source row; no temporal rejoin or alignment correction.",
            "weighting":"Equal weight for each complete row; gaps do not create synthetic observations.",
            "bias":"mean(sensor-reference)","mae":"mean(abs(sensor-reference))",
            "rmse":"sqrt(mean((sensor-reference)^2))",
            "pearson_r":"centred cross-product divided by square root of centred sums of squares",
            "ols":"sensor = intercept + slope*reference; ordinary least squares with an intercept",
            "ols_justification":"Each series has at least two complete pairs and nonzero reference variance; descriptive projection only, no error-free-reference or causal assertion.",
            "missingness":"Exclude incomplete rows from pair statistics only; preserve them in recovered CSVs.",
            "numeric_conversion":False,"outlier_removal":False,"calibration_applied":False,
            "confidence_intervals_or_significance_tests":False},
        "complete_pairs":sum(r["n"] for r in results),
        "complete_pairs_with_author_confirmed_units":sum(r["n"] for r in results if r["effective_unit"]),
        "series":results,"largest_absolute_errors":extremes,"regression_direction_diagnostics":slope_diagnostics,
        "limitations":["Related-source confirmation is not an exact cohort or physical-device mapping to the171 metric records.",
            "Annex dates and unresolved body/annex conflicts are preserved; timestamp coincidence does not prove independently verified co-location or alignment.",
            "Autocorrelation, missingness and unequal temporal coverage preclude treating the row count as an independent sample count.",
            "Correlation measures association and must not be substituted for agreement or calibration.",
            "SO2 and CO have only three distinct reference values; their narrow numerical range limits regression interpretation.",
            "PM1 bias/MAE/RMSE/intercept are arithmetic on an unconfirmed source scale; no physical unit is assigned.",
            "No measurement-uncertainty budget, coverage factor, regulatory threshold or conformity classification is inferred."]}
    (root/"data/paired_agreement_metrics.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"complete_pairs":report["complete_pairs"],"author_unit_pairs":report["complete_pairs_with_author_confirmed_units"],"series":[{k:r[k] for k in ["pollutant","n","effective_unit","bias_sensor_minus_reference","mae","rmse","pearson_r"]} for r in results]},indent=2))

if __name__=="__main__":main()
