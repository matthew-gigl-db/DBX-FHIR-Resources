# 2026-06-13 Clinical Mart First Run — Build, Debug, Validate

## Goals
1. Implement `fhir_gold_clinical_mart` pipeline: 4 dimension tables + 6 fact tables reading from FHIR Gold
2. Debug and run first full pipeline refresh end-to-end
3. Validate integrity and data quality across all 10 tables
4. Diagnose the no-value observation cohort
5. Commit integrity check fixture notebook

---

## Problems Discovered

1. **CDC co-location error**: `DLTAnalysisException: No query found for dataset ncqai.dev_matthew_giglia_clinical_mart.dim_patient`
2. **Stream-stream LEFT OUTER join error on fact_encounter**: `Stream-stream LeftOuter join between two streaming DataFrame/Datasets is not supported without a watermark in the join keys`

---

## Root Causes & Fixes

| # | Problem | Root Cause | Fix |
|---|---------|-----------|-----|
| 1 | No query found for dim_patient | `dp.create_auto_cdc_flow()` was in `entity_resolution.py`; `dp.create_streaming_table()` was in `dimensions.py`. SDP requires both in the same file. | Moved all CDC flows from `entity_resolution.py` into `dimensions.py`, immediately after each streaming table declaration. Mirrors pattern in `fhir_gold.py`. |
| 2 | Stream-stream LEFT OUTER join on fact_encounter | `prac`, `org`, `loc` lookup CTEs all used `_gold()` (`STREAM()`). Structured Streaming rejects stream-stream LEFT OUTER joins without watermarks. | Added `_static(table)` helper (no STREAM wrapper). Changed all three dimension lookup CTEs to `_static()`. Only the primary `enc` CTE (encounter_gold) remains a streaming read. |

---

## Work Completed

### New Files

| File | Asset ID | Purpose |
|------|----------|---------|
| `src/fhir_gold_clinical_mart/transformations/entity_resolution.py` | 760357175635859 | 10 `@dp.temporary_view` functions — one per mart table. Reads gold via `_gold()` (STREAM) or `_static()` (snapshot). Computed columns: `full_name`, `age_years`, `age_band` (dim_patient); `length_of_stay_hours`, `is_emergency`, `is_inpatient` (fact_encounter); `is_chronic`, `is_active` (fact_condition); `is_abnormal_low`, `is_abnormal_high` (fact_observation); `duration_minutes` (fact_procedure). |
| `fixtures/clinical_mart_integrity_check` (notebook) | 760357175635964 | Post-load validation: row counts, null/dupe PKs, orphan FKs, gold alignment, dim_patient demographics, fact_encounter class/LOS, fact_condition flags, fact_observation value coverage, no-value diagnosis. |

### Modified Files

| File | Asset ID | Change |
|------|----------|--------|
| `src/fhir_gold_clinical_mart/transformations/dimensions.py` | 2240851736366203 | Added all 10 `dp.create_streaming_table()` declarations + all 10 `dp.create_auto_cdc_flow()` calls co-located immediately after each table declaration. SCD1. |
| `src/fhir_gold_clinical_mart/transformations/entity_resolution.py` | 760357175635859 | Added `_static(table)` helper alongside `_gold(table)`. Changed prac/org/loc dimension lookup CTEs in `fact_encounter_src` from `_gold()` to `_static()` to resolve stream-stream join error. |

---

## Key Architectural Decisions

- **CDC flows co-located with table declarations**: SDP's graph builder requires `dp.create_auto_cdc_flow()` to be in the same Python file as its `dp.create_streaming_table()`. Putting them in separate files silently drops the flows from graph registration, causing `No query found for dataset`. Reference: `fhir_gold.py` always co-locates table + flow.
- **Temp views can be in a separate file**: `@dp.temporary_view` decorated functions may live in any file matched by the pipeline's library glob.
- **Dimension lookups are static reads in fact views**: In `fact_encounter_src`, the practitioner/org/location lookup CTEs use `_static()` (no `STREAM`). Stream-stream LEFT OUTER joins require watermarks; only the primary source (encounter_gold) is `STREAM`.
- **Gold tables as clinical mart source**: Clinical Mart reads from FHIR Gold tables (already entity-resolved SCD1), not Silver directly. Natural keys are already resolved.
- **`_gold()` vs `_static()` pattern**:
  - `_gold(table)` → `STREAM({catalog}.{schema}.{table})` — primary streaming fact source
  - `_static(table)` → `{catalog}.{schema}.{table}` — dimension/lookup snapshot read

---

## Commits (mg-clinical-mart branch)

| SHA | Message |
|-----|---------|
| `8533198` | feat(clinical-mart): add entity_resolution.py with CDC flows for all 10 mart tables (initial — had co-location bug) |
| `75aaf3d` | fix(clinical-mart): co-locate CDC flows with streaming table declarations |
| `d8f4036` | fix(clinical-mart): use static reads for dimension lookups in fact_encounter_src |
| `94105e7` | feat(clinical-mart): add integrity check fixture notebook |

---

## Pipeline Run Summary

| Run ID | Result | Notes |
|--------|--------|-------|
| `f6e4984c-0b90-40a2-a0cd-96665676dc1d` | FAILED | CDC co-location bug — `No query found for dataset dim_patient` |
| `c165723a-2bb2-4610-99e4-b9b827fd92f0` | PARTIAL (9/10) | `fact_encounter` FAILED — stream-stream LEFT OUTER join error |
| `f160a6e6-f63f-4d9d-ace9-0c59b15149b0` | COMPLETED | All 10 flows, 0 errors — first clean full refresh |

Preceding pipeline runs (same day, same data set):
- Bronze: `b58fd799-95df-441e-a006-d8d5bb425844` (27 min)
- Silver: `570d3f3f-0db0-49ec-8236-25fccb3619c1` (~10 min)
- Gold: `b42e1031-299d-4f39-ada5-b97f18ccb332` (~10 min)

---

## Verification (run f160a6e6 — First Clean Full Refresh)

### Row Counts (10/10 exact match to gold source)

| Table | Rows | Gold Source Match |
|-------|------|-------------------|
| dim_patient | 124,565 | patient_gold |
| dim_practitioner | 1,240 | practitioner_gold |
| dim_organization | 1,126 | organization_gold |
| dim_location | 1,141 | location_gold |
| fact_encounter | 7,994,774 | encounter_gold |
| fact_condition | 4,939,762 | condition_gold |
| fact_observation | 70,599,707 | observation_gold |
| fact_procedure | 22,196,616 | procedure_gold |
| fact_medication_request | 6,522,549 | medication_request_gold |
| fact_immunization | 1,948,242 | immunization_gold |

### Integrity Checks (all pass)

- Null PKs: 0 across all 10 tables
- Duplicate PKs: 0 across all 7 keyed tables
- Orphan FKs (`patient_natural_key`): 0 across all 6 fact tables
- Gold-to-mart alignment: 100% for all 7 fact tables checked

### Data Quality

- `dim_patient` age bands: 0-17 18.1%, 18-34 21.2%, 35-49 17.4%, 50-64 20.5%, 65+ 22.8% (clinically plausible)
- `dim_patient`: avg age 44.4 yrs, range 0–110; 0 missing primary IDs; avg 4.61 identifiers/patient
- `fact_encounter`: `is_emergency` = 304,653 matches EMER class count exactly; `is_inpatient` = 150,522 matches IMP count exactly; avg IMP LOS 6.7 days; 8 null LOS rows on EMER/IMP (open encounters)
- `fact_condition`: 25.6% chronic, 124,561 distinct patients (near-complete coverage of 124,565 total)
- `fact_observation` value types: 77.5% quantity, 17.7% code, 4.7% no_value, 0.07% string

### No-Value Observation Diagnosis

- 3,332,827 rows (4.7%) have NULL `value_quantity`, `value_string`, and `value_code`
- Cell 8 root cause check: **100% are panel headers with `component[]` array**
  - `85354-9` Blood pressure panel: 1,948,378 rows (59% of no-value cohort)
  - `93025-5` PRAPARE social determinants panel: 1,351,621 rows (41%)
- Zero extraction gaps in the gold ETL — expected FHIR semantics
- Panel header child values are separate Observation resources with their own gold rows

---

## Tech Debt Documented in Code

| ID | Location | Description | Blocker |
|----|---------|-------------|--------|
| TD-1 | `dimensions.py` + `entity_resolution.py` | `fact_encounter` missing `practitioner_natural_key`, `organization_natural_key`, `location_natural_key` FK columns. JOIN logic already written in `entity_resolution.py` but columns commented out. | Add 3 columns to `fact_encounter` schema in `dimensions.py`, then uncomment SELECT lines in `fact_encounter_src`. |
| TD-2 | `dimensions.py` + `entity_resolution.py` | `fact_observation` missing `value_raw VARIANT`. Column exists on `observation_gold`. | Add `value_raw VARIANT` to `fact_observation` schema in `dimensions.py`, then uncomment `value_raw,` in `fact_observation_src`. |
| TD-3 | `dimensions.py` + `entity_resolution.py` | `fact_condition` missing `encounter_natural_key` FK. `_encounter_ref_url` + `_bundle_uuid` available on `condition_gold` for resolution. | Add `encounter_natural_key STRING` to `fact_condition` schema in `dimensions.py`, add encounter CTE and LEFT JOIN to `fact_condition_src`. |

---

## Known Remaining Issues

1. **TD-1**: `fact_encounter` missing practitioner/org/location FK columns (see Tech Debt above)
2. **TD-2**: `fact_observation` missing `value_raw VARIANT` (see Tech Debt above)
3. **TD-3**: `fact_condition` missing `encounter_natural_key` FK (see Tech Debt above)
4. **`fact_claim` not implemented**: `claim_gold` exists in FHIR schema with full column set; no mart table yet
5. **`register_metric_views` not yet run**: YAML fixtures in `fixtures/metric_views/` exist; notebook must be executed to register UC metric views
6. **SCD2 not considered for dims**: `dim_patient`/`dim_practitioner` implemented as SCD1; design doc mentions SCD2 tracking for `marital_status` and `address_state` changes

---

## Next Steps (Priority Order)

1. Open PR for `mg-clinical-mart` branch into main
2. **TD-1**: Add FK columns to `fact_encounter` schema in `dimensions.py`; uncomment 3 lines in `entity_resolution.py`
3. **TD-2**: Add `value_raw VARIANT` to `fact_observation` schema in `dimensions.py`; uncomment 1 line in `entity_resolution.py`
4. **TD-3**: Add `encounter_natural_key` to `fact_condition` schema in `dimensions.py`; add encounter CTE to `fact_condition_src`
5. **Add `fact_claim`**: `dp.create_streaming_table()` + `dp.create_auto_cdc_flow()` in `dimensions.py`; `fact_claim_src` temp view in `entity_resolution.py`
6. **Run `register_metric_views`** notebook (asset ID: 2240851736366200) to create UC metric views in `dev_matthew_giglia_clinical_mart`
7. **Consider SCD2** for `dim_patient` tracking `marital_status` and `address_state` changes
