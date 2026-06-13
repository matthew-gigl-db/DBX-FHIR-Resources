# 2026-06-13 Gold YAML Engine Completion & gold_overrides.py

## Goals
1. Complete gold layer coverage for all clinically-relevant silver resource tables
2. Factor edge-case tables (location, bridge) into `gold_overrides.py`
3. Remove stale hand-coded views/tables from `entity_resolution.py` and `fhir_gold.py`
4. Update PROJECT_MEMORY.md to reflect final architecture

## Problems Discovered
1. **10 event views never removed from entity_resolution.py** — previous session's `executeCode` file writes did not persist (session was summarized/interrupted before workspace sync completed)
2. **Previous session assumed `editAsset` had succeeded** — the conversation summary said views were removed, but the actual file still had 741 lines with all 13 `@dp.temporary_view` decorators
3. **File ID mismatch** — `3903517986806171` (from Key File IDs table) is actually `databricks.yml`, not `fhir_gold.py`; required switching to workspace path for edits

## Root Causes & Fixes
| # | Problem | Root Cause | Fix |
|---|---------|-----------|-----|
| 1 | Stale views in entity_resolution.py | `executeCode` file writes during a session that was later summarized did not persist to workspace | Used `executeCode` with `open()` to replace lines 239–731 with YAML comment markers |
| 2 | Incorrect migration state | Conversation summary asserted removals that hadn't actually committed | Verified true file state via `open()` + `readAssetById`, then re-did the removal |
| 3 | Wrong file ID for fhir_gold.py | SESSION_MEMORY key file table had stale mapping | Used full workspace path (`/Workspace/Users/.../fhir_gold.py`) for all `editAsset` calls |

## Work Completed

### New YAML Fixtures (7 files created in `fixtures/gold_etl/`)
| File | Table | join_type | patient_ref_field | Notes |
|------|-------|-----------|-------------------|-------|
| `careteam_gold.gold.yml` | careteam_gold | event | subject | Reason codes, encounter ref, managing org |
| `documentreference_gold.gold.yml` | documentreference_gold | event | subject | LOINC doc types, content MIME type, custodian |
| `device_gold.gold.yml` | device_gold | event | patient | UDI, serial/lot numbers, manufacture/expiry dates |
| `imagingstudy_gold.gold.yml` | imagingstudy_gold | event | subject | Procedure codes, body site, modality, series/instance counts |
| `supplydelivery_gold.gold.yml` | supplydelivery_gold | event | patient | Supply type, item code, quantity, occurrence |
| `medication_gold.gold.yml` | medication_gold | entity | null | RxNorm code, standalone reference dimension |
| `practitionerrole_gold.gold.yml` | practitionerrole_gold | entity | null | NPI, org ID, NUCC specialty/role, telecom |

### New Source File
| File | Purpose |
|------|---------|--|
| `src/fhir_gold_etl/transformations/gold_overrides.py` | 241 lines. Hand-coded edge cases: location_gold (correlated subquery) + patient_identity_bridge (LATERAL VIEW EXPLODE). Contains own view + table + CDC flow for each. |

### Files Modified
| File | Change |
|------|--------|
| `entity_resolution.py` | 741 → 279 lines. Removed 10 event views (condition through explanationofbenefit) + location_resolved + patient_identity_bridge_resolved. Replaced with YAML/override comment markers. |
| `fhir_gold.py` | Removed location_gold table+CDC (replaced with override comment). Removed patient_identity_bridge table+CDC (replaced with override comment). Now 275 lines, 3 tables only. |
| `PROJECT_MEMORY.md` | Rewrote Section 4 (fhir_gold_etl) for 25-table 4-file architecture. Rewrote Gold YAML Engine section with final 20-fixture table, coverage summary. Updated Source File Reference. |

## Final Architecture (25 Gold Tables)

| Source File | Tables | Pattern |
|---|---|---|
| `fhir_gold.py` | patient_gold, practitioner_gold, organization_gold (3) | identifier_cascade entity |
| `gold_overrides.py` | location_gold, patient_identity_bridge (2) | correlated subquery, LATERAL VIEW |
| `gold_engine.py` | 20 YAML-driven tables | event (18), entity (2) |

### Silver Coverage
- 25/27 resource types covered (93%)
- Deferred: provenance (audit trail), account (10 rows), messageheader (10 rows)

## Decisions
- **medication and practitionerrole as YAML, not overrides** — both fit `join_type: entity` cleanly (no patient join, simple composite_sha2 keys). No need for hand-coded Python.
- **YAML `patient_ref_field: null`** for entity tables — engine skips patient JOIN generation entirely
- **Pipeline glob auto-discovers gold_overrides.py** — `../src/fhir_gold_etl/transformations/**` pattern means no pipeline YAML change needed
- **`_ORGANIZATION_NATURAL_KEY_SQL` duplicated in gold_overrides.py** — acceptable trade-off vs. importing from entity_resolution.py (avoids circular dependency risk in SDP execution)
- **`_PATIENT_NATURAL_KEY_SQL` duplicated in gold_overrides.py** — same rationale; the bridge view needs it standalone
- **Deferred provenance/account/messageheader** — no clinical/financial analytics value; can add later if needed

## Verification
- `bundle validate --target dev`: Validation OK (before and after all changes)
- `ast.parse()` on all 3 modified files: syntax OK
- No duplicate `@dp.temporary_view` or `dp.create_streaming_table` definitions across files
- Pipeline run `047e9c3b-86d4-4c5a-a299-a82920a4eab8` (13-table full refresh): COMPLETED
- 20 YAML fixtures in `fixtures/gold_etl/` directory confirmed

## Full Refresh Validation (run bc462613-c435-44aa-b92f-5c8d860dc69b — COMPLETED)

All 25 tables materialized successfully. 175,464,067 total gold rows.

### Row Counts
| Table | Gold | Silver | Dedup % |
|---|---|---|---|
| patient_gold | 124,256 | 134,899 | 7.9% |
| practitioner_gold | 1,240 | 4,230 | 70.7% |
| organization_gold | 1,126 | 4,226 | 73.4% |
| location_gold | 1,141 | 4,273 | 73.3% |
| patient_identity_bridge | 611,678 | — | — |
| encounter_gold | 7,972,040 | 7,973,057 | 0.0% |
| condition_gold | 4,925,267 | 4,925,267 | 0.0% |
| observation_gold | 70,386,595 | 70,671,532 | 0.4% |
| procedure_gold | 22,132,354 | 22,132,435 | 0.0% |
| medication_request_gold | 6,503,519 | 6,889,647 | 5.6% |
| immunization_gold | 1,942,924 | 1,942,924 | 0.0% |
| allergyintolerance_gold | 125,792 | 125,792 | 0.0% |
| careplan_gold | 445,608 | 448,311 | 0.6% |
| diagnosticreport_gold | 15,881,195 | 15,921,203 | 0.3% |
| medicationadministration_gold | 2,416,927 | 2,417,120 | 0.0% |
| claim_gold | 13,799,381 | 14,862,694 | 7.2% |
| explanationofbenefit_gold | 14,862,694 | 14,862,694 | 0.0% |
| coverage_gold | 3 | 6 | 50.0% |
| careteam_gold | 446,639 | 448,321 | 0.4% |
| documentreference_gold | 7,936,113 | 7,973,047 | 0.5% |
| device_gold | 777,663 | 777,663 | 0.0% |
| imagingstudy_gold | 636,751 | 636,751 | 0.0% |
| supplydelivery_gold | 3,531,819 | 3,550,135 | 0.5% |
| medication_gold | 104 | 2,417,120 | 100.0% |
| practitionerrole_gold | 1,238 | 4,210 | 70.6% |

### Referential Integrity
- Encounter → Patient FK: **0 orphans** / 7,972,040 (100% valid)
- Condition → Patient FK: **0 orphans** / 4,925,267 (100% valid)
- Location → Organization FK: **0 orphans** / 1,141 (100% valid)

### Identity Bridge
- 611,678 total identifier rows across 124,256 patients (4.9 avg IDs/patient)
- 6 identifier systems: SSN (20.3%), hospital (22.1%), synthea (22.1%), DL (18.3%), passport (17.2%), MRN (0.0%)

### Data Quality
- Natural keys: 0% null across ALL 25 tables
- Patient demographics: 100% populated (name, DOB, gender, state)
- Device UDI/type: 100% populated
- ImagingStudy procedure/body_site/modality: 100% populated
- Observation value_quantity: 77.5% (expected — 22.5% are coded or text observations)
- CareTeam reason_code: 52% (expected — not all care teams specify reason)

### Dedup Pattern Analysis
- **Reference entities** (70-100% dedup): Same real-world entity appears in many bundles.
  Medication is extreme: 2.4M silver → 104 gold (only 104 unique RxNorm codes in Synthea formulary).
- **Events (unique)** (0-0.6% dedup): Most clinical events are truly unique.
- **Events (cross-bundle)** (5-8% dedup): Patient/encounter/claim resources duplicated across overlapping bundles.

### gold_overrides.py Validated
- `location_gold`: 1,141 rows, correlated subquery resolved managing_organization_nk correctly (0 orphan FKs)
- `patient_identity_bridge`: 611,678 rows, LATERAL VIEW EXPLODE working correctly across 6 identifier systems

## Known Remaining Issues
1. **entity_resolution.py still has 10 YAML-driven view comments** — cosmetic only (no code, just breadcrumbs)
2. **File ID table in SESSION_MEMORY stale** — `3903517986806171` maps to `databricks.yml`, not `fhir_gold.py`
3. **DocumentReference is single-type** — all 7.9M rows are "History and physical note" (Synthea limitation)
4. **SupplyDelivery is single-type** — all 3.5M rows are type "device" (Synthea limitation)
5. **Clinical mart not yet implemented** — dimensions.py has schema DDL but no transformation SQL

## Next Steps
- Deploy to `hedis` target for production use
- Begin clinical mart dimensional model (dim_patient, fact_encounter, etc.)
- Consider HEDIS measure logic against gold tables
- Update PR with final validation results
