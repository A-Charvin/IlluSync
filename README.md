# IlluSync - Parcel/Civic Address QC Tool

An ArcGIS Pro Python toolbox that validates MPAC parcel data against civic address points, flagging mismatches in both directions. Built for NG911 data quality workflows.

## What it does

IlluSync spatially compares a parcel polygon layer against a civic address point layer and reports discrepancies as a single exception feature class. It checks for:

| Error Code | Description |
|---|---|
| `E00_MULTI` | Multiple error types found within the same parcel (details stored in ERR_LIST) |
| `E01_MISS_PT` | Parcel has a specific civic address but no civic point inside it |
| `E02_ORPHAN` | Civic point falls outside any parcel boundary |
| `E05_ARN_MIS` | Parcel and civic ARN (Assessment Roll Number) do not match |
| `E06_ADDR_MIS` | Parcel and civic addresses fully disagree |
| `E08_PARTIAL` | Parcel and civic addresses partially overlap (e.g. truncated text or unit numbers) |
| `E09_GHOST` | Civic point has a matching ARN but lacks an address |
| `E10_PADDR` | Civic point has a valid address, but the parcel address is missing or invalid |

Addresses are normalized (suffix expansion, punctuation, whitespace) before comparison, and rural/rangeline-style addressing (concession, sideroad, line, etc.) is distinguished from standard civic numbering to avoid false positives.

## Requirements

* ArcGIS Pro 3.x (ArcPy)
* No external Python libraries required

## Inputs

- **Parcel Layer** (polygon) + ARN field + Address field
- **Civic Point Layer** (point) + ARN field + Address field
- **Output Exception Feature Class** (polygon)

Field names are selected at runtime through dynamic dropdowns. There are no hardcoded schema requirements.

## Output

A single polygon feature class containing only the flagged records. When a parcel contains multiple civic points, the tool collapses them into one polygon row. The output schema includes:

* **Identifiers:** Parcel ARN, Parcel Address, Civic ARN, Civic Address (from the first evaluated point).
* **Status Fields:** Spatial status (`INSIDE`, `OUTSIDE`, `MISSING`, `GHOST`), Match type (`FAIL`, `PARTIAL`, `MIXED`), Error code, Error description.
* **Aggregation Fields:** 
  * `PT_COUNT`: Total number of civic points found inside the parcel.
  * `C_LIST`: A text list of all civic ARNs and addresses tied to the parcel.
  * `ERR_LIST`: A breakdown of specific errors tied to individual points on the parcel.
  * `NOTE`: Context tags like `MULTI POINT` or `ORPHAN`.
* **Review flag:** For QA sign-off tracking.

## Design principles

* **Validation-only:** No auto-correction and no silent overwrites. The tool flags records for human review.
* **Aggregated output:** One output polygon per parcel prevents map clutter and duplicate geometry errors.
* **Schema-agnostic:** Field mapping happens at runtime using explicit field maps to prevent ghost fields.
* **Safe memory management:** Uses the `memory` workspace and strictly deletes only its own temporary datasets to prevent conflicts in ModelBuilder.
* **No external dependencies:** Pure ArcPy, runs anywhere ArcGIS Pro is installed.

## Known limitations

* Address normalization rules are tuned for English/Ontario-style addressing conventions.
* ARN fields with numeric types (Double/Long) require explicit None-checks during processing to protect valid zero values.
* Long address strings beyond 250 characters are truncated with ellipses to respect geodatabase field limits.

## Part of the NG911 QA tool series

- [RoadRanger](https://github.com/A-Charvin/RoadRanger-QA-911) - road segment address range continuity validation
- [FishboneQA](https://github.com/A-Charvin/Fishbone-QA-911) - civic address point-to-road centerline matching
- **IlluSync** - parcel/civic address cross-validation
