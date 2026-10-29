#!/usr/bin/env python3
"""Reproduce literal historical annex extraction; no calibration or validation claims.

Requires Poppler's pdftotext and PyMuPDF. The original PDF is supplied privately by the user.
Only source hash, neutral series identifiers, literal observations and page/row
provenance are emitted. No source PDF or personal metadata is redistributed.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile
import fitz
from collections import Counter
from datetime import datetime
from pathlib import Path

EXPECTED_SHA256 = "f0da594d8506e937ed9134840687c746ebb099a354440b7c5062b981b28b4234"
SECTIONS = [
    ("NO2", r"ANNEX I\. NO2 DATA", "HS1", "date_conflict;station_conflict"),
    ("NO", r"ANNEX II\. NO data", "HS2", ""),
    ("O3", r"ANNEX III\. O3 data", "HS3", ""),
    ("SO2", r"ANNEX IV\. SO data", "HS4", "date_conflict"),
    ("CO", r"ANNEX V\. CO data", "HS5", "date_conflict;clock_ambiguity"),
    ("PM10", r"ANNEX III\. PM10 data", "HS6", "timezone_unspecified"),
    ("PM2.5", r"ANNEX VII\. PM2\.5 data", "HS7", "timezone_unspecified"),
    ("PM1", r"ANNEX VIII\. PM1 data\.", "HS8", ""),
]
DATE_RE = re.compile(r"(?<!\d)(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2})(?!\d)")
TIME_RE = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2})?(?!\d)")
NUMBER_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
FIELDS = ["dataset_id", "series_id", "pollutant", "device_identity", "reference_identity",
          "source_row", "pdf_page", "pdf_page_end", "page_row", "timestamp_source",
          "timestamp_iso", "timezone_status", "sensor_value", "reference_value",
          "pair_status", "reported_unit", "unit_status", "quarantine_flags", "source_row_text"]

def write_rows(path, rows):
    temporary = path.with_suffix(path.suffix+".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
        f.flush();os.fsync(f.fileno())
    temporary.replace(path)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    a = ap.parse_args()
    sha = hashlib.sha256(a.pdf.read_bytes()).hexdigest()
    if sha != EXPECTED_SHA256:
        raise SystemExit(f"Source hash mismatch: expected {EXPECTED_SHA256}; received {sha}")
    a.output.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, check=True).stderr.splitlines()[0]
    with tempfile.TemporaryDirectory() as td:
        extracted = Path(td) / "layout.txt"
        subprocess.run(["pdftotext", "-layout", str(a.pdf), str(extracted)], check=True)
        text = extracted.read_text(encoding="utf-8")
    pdf = fitz.open(a.pdf)
    boundaries = []
    for pollutant, pattern, device, flags in SECTIONS:
        candidates = [m for m in re.finditer(pattern, text) if text.count("\f", 0, m.start()) >= 29]
        if len(candidates) != 1:
            raise ValueError(f"Expected exactly one actual annex heading for {pollutant}, found {len(candidates)}")
        boundaries.append((candidates[0].end(), pollutant, device, flags, candidates[0].start()))
    if boundaries != sorted(boundaries):
        raise ValueError("Annex ordering changed")
    rows, rejects, summaries = [], [], []
    for index, (start, pollutant, device, flags, heading_start) in enumerate(boundaries):
        end = boundaries[index+1][4] if index+1 < len(boundaries) else len(text)
        section = text[start:end]
        dates = list(DATE_RE.finditer(section))
        sr, page_counts = [], Counter()
        for n, match in enumerate(dates, 1):
            stop = dates[n].start() if n < len(dates) else len(section)
            fragment = section[match.start():stop]
            # Stop before trailing page separators; a row split across pages is retained.
            trimmed = fragment.rstrip()
            raw = " ".join(trimmed.split())
            page = text.count("\f", 0, start+match.start())+1
            end_page = page + trimmed.count("\f")
            page_counts[page] += 1
            times = list(TIME_RE.finditer(fragment))
            if len(times) != 1:
                rejects.append({"pollutant":pollutant,"source_row":n,"pdf_page":page,"reason":"not_exactly_one_time","raw":raw})
                continue
            time = times[0]
            residue = fragment[match.end()-match.start():]
            residue = TIME_RE.sub(" ", residue)
            numbers = NUMBER_RE.findall(residue)
            extras = NUMBER_RE.sub(" ", residue).strip()
            if len(numbers) <= 1 and not extras and pollutant == "PM1":
                # Source PM1 tables contain blank cells. Preserve their column identity
                # from the PDF geometry; never shift a single number into the wrong cell.
                # This source-hash-specific schema places sensor cells at x~252pt and
                # reference cells at x>=294pt. It was checked on pages626 and637.
                words = pdf[page-1].get_text("words")
                tw = [w for w in words if w[4] == time.group()]
                if len(tw) != 1:
                    raise ValueError(f"Ambiguous PDF time position at page{page}: {time.group()}")
                candidates = [w for w in words if NUMBER_RE.fullmatch(w[4])
                              and w[0]>210 and tw[0][1]-2<=w[1]<tw[0][1]+30]
                sensor = [w[4] for w in candidates if 245<=w[0]<=265]
                reference = [w[4] for w in candidates if 285<=w[0]<=400]
                if len(sensor)>1 or len(reference)>1 or len(candidates)!=len(numbers) or sorted(w[4] for w in candidates)!=sorted(numbers):
                    raise ValueError(f"Ambiguous missing-cell recovery at page{page}: {raw}")
                numbers = [sensor[0] if sensor else "", reference[0] if reference else ""]
            if len(numbers) != 2 or extras:
                rejects.append({"pollutant":pollutant,"source_row":n,"pdf_page":page,"reason":"not_exactly_two_numeric_cells_or_unparsed_text","raw":raw,"numbers":numbers,"extras":extras})
                continue
            source_time = match.group() + " " + time.group()
            if "/" in match.group():
                # The report prints two-digit year19. Preserve the original as well.
                dt = datetime.strptime(source_time, "%m/%d/%y %H:%M")
            else:
                dt = datetime.fromisoformat(source_time)
            row = dict(zip(FIELDS, ["H2022", device, pollutant, "", "",
                n, page, end_page, page_counts[page], source_time, dt.isoformat(),
                "explicit_UTC_offset" if dt.tzinfo else "not_stated", numbers[0], numbers[1],
                "complete" if all(numbers) else ("sensor_missing" if not numbers[0] and numbers[1] else "reference_missing" if numbers[0] and not numbers[1] else "both_missing"), "",
                "not_stated_in_annex", ";".join(filter(None,["unit_unresolved", "physical_device_identity_unresolved",flags])), raw]))
            rows.append(row); sr.append(row)
        numeric = [(float(r["sensor_value"]), float(r["reference_value"])) for r in sr if r["pair_status"]=="complete"]
        stamps = [datetime.fromisoformat(r["timestamp_iso"]) for r in sr]
        unique = sorted(set(stamps))
        intervals = Counter((b-a).total_seconds() for a,b in zip(unique, unique[1:]))
        expected_step = 60 if pollutant=="PM1" else 3600
        expected_points = int((unique[-1]-unique[0]).total_seconds()/expected_step)+1 if unique else 0
        summaries.append({"series_id":device, "pollutant":pollutant,
            "device_identity":None,"reference_identity":None,
            "rows":len(sr),"date_tokens":len(dates),"rejected_rows":len(dates)-len(sr),
            "first_timestamp_source":sr[0]["timestamp_source"] if sr else None,
            "last_timestamp_source":sr[-1]["timestamp_source"] if sr else None,
            "minimum_timestamp_iso":unique[0].isoformat() if unique else None,
            "maximum_timestamp_iso":unique[-1].isoformat() if unique else None,
            "pdf_pages":[min(r["pdf_page"] for r in sr),max(r["pdf_page_end"] for r in sr)] if sr else [],
            "complete_pairs":len(numeric),
            "missing_sensor_cells":sum(not r["sensor_value"] for r in sr),
            "missing_reference_cells":sum(not r["reference_value"] for r in sr),
            "missing_numeric_cells_in_extracted_rows":sum(not r[f] for r in sr for f in ["sensor_value","reference_value"]),
            "duplicate_timestamps":len(stamps)-len(unique),
            "non_increasing_source_steps":sum(b<=a for a,b in zip(stamps,stamps[1:])),
            "unique_timestamp_interval_seconds":dict(sorted(intervals.items())),
            "diagnostic_grid_step_seconds":expected_step,
            "diagnostic_grid_expected_points_in_annex_extent":expected_points,
            "diagnostic_grid_unlisted_points":expected_points-len(unique),
            "diagnostic_grid_is_completeness_claim":False,
            "negative_sensor_values":sum(float(r["sensor_value"])<0 for r in sr if r["sensor_value"]),
            "negative_reference_values":sum(float(r["reference_value"])<0 for r in sr if r["reference_value"]),
            "exact_equal_pairs":sum(x==y for x,y in numeric),
            "reported_unit":None,"unit_status":"not_stated_in_annex",
            "quarantine_flags":sr[0]["quarantine_flags"] if sr else flags})
        path = a.output / ("H2022_"+pollutant.replace(".","_")+".csv")
        write_rows(path,sr)
    write_rows(a.output/"H2022_paired_observations.csv",rows)
    (a.output/"extraction_rejects.json").write_text(json.dumps(rejects,indent=2)+"\n")
    report={"dataset_id":"H2022", "version":"1.0.0", "source_sha256":sha,"source_pdf_pages":text.count("\f"),
            "extraction_engine":version,"missing_cell_geometry_engine":"PyMuPDF "+fitz.VersionBind,
            "rows":len(rows),"complete_pairs":sum(r["pair_status"]=="complete" for r in rows),"rejected_rows":len(rejects),"series":summaries,
            "scope":"Literal recovery of historical report annexes; H2022 labels report date, not every measurement year.",
            "not_claimed":["raw instrument export", "clean validation dataset", "measurement accuracy", "physical device linkage", "verified digital signature", "public license", "anonymity", "relation to 2024-2026 paper campaigns"]}
    (a.output/"extraction_summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"rows":len(rows),"rejects":len(rejects),"series":[{k:s[k] for k in ["pollutant","rows","rejected_rows","first_timestamp_source","last_timestamp_source","duplicate_timestamps"]} for s in summaries]},indent=2))
    if rejects:
        raise SystemExit("Review rejected rows before using extraction")

if __name__ == "__main__":
    main()
