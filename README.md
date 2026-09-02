# IlluSync - Parcel/Civic Address QC Tool

An ArcGIS Pro Python toolbox that validates MPAC parcel data against civic address points, flagging mismatches in both directions. Built for NG911 data quality workflows.

## What it does

IlluSync spatially compares a parcel polygon layer against a civic address point layer and reports discrepancies as a single exception feature class. It checks for:

| Error Code | Description |
|---|---|
| `E01_MISS_PT` | Parcel has a specific address but no civic point inside it |
| `E02_ORPHAN` | Civic point falls outside any parcel |
| `E05_ARN_MIS` | Parcel and civic ARN (Assessment Roll Number) don't match |
| `E06_ADDR_MIS` | Parcel and civic addresses fully disagree |
| `E08_PARTIAL` | Parcel and civic addresses partially overlap (e.g. truncated text) |
| `E09_GHOST` | Civic point has an ARN but no address |
| `E10_PADDR` | Civic Address exists, Parcel have partial or no address |

Addresses are normalized (suffix expansion, punctuation, whitespace) before comparison, and rural/rangeline-style addressing (concession, sideroad, line, etc.) is distinguished from standard civic numbering to avoid false positives.

## Requirements

- ArcGIS Pro 3.x (ArcPy)
- No external Python libraries - runs in ArcGIS Pro's native Python environment

## Inputs

- **Parcel Layer** (polygon) + ARN field + Address field
- **Civic Point Layer** (point) + ARN field + Address field
- **Output Exception Feature Class** (polygon)

Field names are chosen at runtime - there's no fixed schema requirement, so it can run against any municipality's parcel and civic layers.

## Output

A single polygon feature class containing only the flagged records, with:

- Parcel ARN / Address
- Civic ARN / Address
- Spatial status (`INSIDE`, `OUTSIDE`, `MISSING`, `GHOST`)
- Match type (`FAIL`, `PARTIAL`)
- Error code and description
- Review flag (for QA sign-off tracking)

## Design principles

- **Validation-only** - no auto-correction, no silent overwrites. The tool flags; a human decides.
- **Schema-agnostic** - field mapping happens at runtime, not hardcoded.
- **No external dependencies** - pure ArcPy, runs anywhere ArcGIS Pro is installed.

## Known limitations

- Address normalization rules are tuned for English/Ontario-style addressing conventions.
- ARN fields with numeric types (Double/Long) may require additional normalization depending on source formatting.
- Long address strings beyond 150 characters will need field-length adjustment before running.

## Part of the NG911 QA tool series

- [RoadRanger](https://github.com/A-Charvin/RoadRanger-QA-911) - road segment address range continuity validation
- [FishboneQA](https://github.com/A-Charvin/Fishbone-QA-911) - civic address point-to-road centerline matching
- **IlluSync** - parcel/civic address cross-validation
