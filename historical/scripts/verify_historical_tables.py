#!/usr/bin/env python3
"""Independent PDF-word cross-check of extracted rows using a second text engine.

Compares every date/time and numeric cell to PyMuPDF words. This verifies literal
transcription only; it does not validate scientific accuracy or source semantics.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import fitz

DATE = re.compile(r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2})")
TIME = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2})?")
NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
HASH = "f0da594d8506e937ed9134840687c746ebb099a354440b7c5062b981b28b4234"

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[1]/"data")
    args = ap.parse_args()
    assert hashlib.sha256(args.pdf.read_bytes()).hexdigest() == HASH
    doc = fitz.open(args.pdf)
    source, anomalies = {}, []
    for p in range(29,len(doc)):
        words = doc[p].get_text("words")
        indexes = [i for i,w in enumerate(words) if DATE.fullmatch(w[4])]
        for j,start in enumerate(indexes):
            stop = indexes[j+1] if j+1<len(indexes) else len(words)
            chunk = words[start:stop]
            ts = [w[4] for w in chunk if TIME.fullmatch(w[4])]
            vals = [w[4] for w in chunk if NUM.fullmatch(w[4])]
            if len(ts)!=1 or len(vals)>2:
                anomalies.append({"page":p+1,"date":chunk[0][4],"times":ts,"numbers":vals})
                continue
            key = (p+1,chunk[0][4]+" "+ts[0])
            if key in source:
                anomalies.append({"duplicate_source_key":key})
            source[key] = vals
    rows = list(csv.DictReader((args.data/"H2022_paired_observations.csv").open()))
    checks, fails, seen = Counter(), [], set()
    for r in rows:
        key = (int(r["pdf_page"]),r["timestamp_source"])
        expected = [r[c] for c in ["sensor_value","reference_value"] if r[c]]
        if source.get(key) != expected:
            fails.append({"row":r["source_row"],"series":r["series_id"],"key":key,"csv_values":expected,"pdf_values":source.get(key)})
        else:
            checks[r["pollutant"]] += 1
        seen.add(key)
    result = {"source_sha256":HASH,"verifier":"PyMuPDF "+fitz.VersionBind,
              "rows_checked":len(rows),"rows_matching":sum(checks.values()),
              "source_date_rows":len(source),"series_matching_rows":dict(checks),
              "unmatched_source_rows":len(set(source)-seen),"failures":fails,"source_parse_anomalies":anomalies,
              "scope":"Every annex timestamp and printed numeric value checked against a second PDF text engine; not scientific validation."}
    (args.data/"verification.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if fails or anomalies or set(source)-seen:
        raise SystemExit("PDF/CSV discrepancies require review")

if __name__ == "__main__":
    main()
