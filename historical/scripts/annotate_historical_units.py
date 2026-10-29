#!/usr/bin/env python3
"""Apply explicit author annotations without changing any recovered source column."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

SOURCE_FIELDS = ["dataset_id", "series_id", "pollutant", "device_identity", "reference_identity",
    "source_row", "pdf_page", "pdf_page_end", "page_row", "timestamp_source", "timestamp_iso",
    "timezone_status", "sensor_value", "reference_value", "pair_status", "reported_unit",
    "unit_status", "source_row_text"]
ADDED_FIELDS = ["effective_unit", "effective_unit_basis", "author_annotation_id", "analysis_status"]
SUMMARY_CONFLICTS = {"NO2", "NO", "SO2", "PM10"}

def source_digest(rows):
    data = json.dumps([[str(r.get(c,"")) for c in SOURCE_FIELDS] for r in rows],
                      ensure_ascii=False,separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    a=ap.parse_args(); root=a.root
    ann_path=root/"docs/author_annotations.json"
    ann=json.loads(ann_path.read_text())
    units={u["pollutant"]:u for u in ann["units"]}
    combined=root/"data/H2022_paired_observations.csv"
    with combined.open(newline="") as f:
        reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
    before=source_digest(rows)
    if before!=ann["immutable_source_columns_sha256"]:
        raise ValueError("Recovered source-column fingerprint changed before annotation")
    for key in ADDED_FIELDS:
        if key not in fields:fields.append(key)
    for r in rows:
        u=units[r["pollutant"]]
        r["effective_unit"]=u["effective_unit"] or ""
        r["effective_unit_basis"]=u["basis"]
        r["author_annotation_id"]=ann["annotation_id"]
        r["analysis_status"]="descriptive_agreement_only" if u["effective_unit"] else "numerical_summary_only_unit_unconfirmed"
        flags=[f for f in r["quarantine_flags"].split(";") if f]
        if u["effective_unit"]:flags=[f for f in flags if f!="unit_unresolved"]
        for flag in ["exact_cohort_mapping_unverified"]+(["source_summary_conflict"] if r["pollutant"] in SUMMARY_CONFLICTS else []):
            if flag not in flags:flags.append(flag)
        r["quarantine_flags"]=";".join(flags)
    after=source_digest(rows)
    if before!=after:raise ValueError("Annotation mutated source columns")
    def write(path,subset):
        temporary=path.with_suffix(path.suffix+".tmp")
        with temporary.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(subset)
            f.flush();os.fsync(f.fileno())
        # Readers must see either the old complete file or the new complete file.
        temporary.replace(path)
    write(combined,rows)
    for pol in units:
        write(root/"data"/("H2022_"+pol.replace(".","_")+".csv"),[r for r in rows if r["pollutant"]==pol])
    summary_path=root/"data/extraction_summary.json"
    summary=json.loads(summary_path.read_text())
    summary.update(version="1.1.0",author_annotation_id=ann["annotation_id"],
        author_annotation_file="docs/author_annotations.json",
        relation_to_paper_171_records=ann["report_relationship"],
        analysis_status="descriptive_comparison_author_units_with_unresolved_provenance",
        immutable_source_columns_sha256=after,
        rows_with_author_confirmed_effective_unit=sum(bool(r["effective_unit"]) for r in rows))
    summary["not_claimed"]=[v for v in summary.get("not_claimed",[]) if v!="relation to 2024-2026 paper campaigns"]
    if "exact cohort mapping to the171-record corpus" not in summary["not_claimed"]:
        summary["not_claimed"].append("exact cohort mapping to the171-record corpus")
    for s in summary["series"]:
        r=next(r for r in rows if r["pollutant"]==s["pollutant"])
        s.update({k:(r[k] or None) for k in ADDED_FIELDS})
        s["quarantine_flags"]=r["quarantine_flags"]
    summary_path.write_text(json.dumps(summary,indent=2)+"\n")
    manifest_path=root/"docs/source_manifest.json"
    manifest=json.loads(manifest_path.read_text())
    manifest.update(version="1.1.0",analysis_status=summary["analysis_status"],
        relation_to_paper_171_records=ann["report_relationship"],
        author_annotation_id=ann["annotation_id"],author_annotation_file="docs/author_annotations.json",
        effective_units={pol:u["effective_unit"] for pol,u in units.items()},
        effective_unit_basis="author confirmation for seven pollutants; PM1 not confirmed",
        immutable_source_columns_sha256=after)
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
    verification={"annotation_id":ann["annotation_id"],"annotation_file_sha256":hashlib.sha256(ann_path.read_bytes()).hexdigest(),
        "rows":len(rows),"source_fields":SOURCE_FIELDS,"source_columns_sha256_before":before,
        "source_columns_sha256_after":after,"source_columns_unchanged":before==after,
        "author_confirmed_unit_rows":sum(bool(r["effective_unit"]) for r in rows),
        "unconfirmed_unit_rows":sum(not r["effective_unit"] for r in rows),
        "all_reported_unit_fields_remain_null":all(not r["reported_unit"] for r in rows),
        "all_physical_device_fields_remain_null":all(not r["device_identity"] and not r["reference_identity"] for r in rows),
        "numeric_conversion_applied":False,"date_correction_applied":False}
    (root/"data/annotation_verification.json").write_text(json.dumps(verification,indent=2)+"\n")
    print(json.dumps(verification,indent=2))

if __name__=="__main__":main()
