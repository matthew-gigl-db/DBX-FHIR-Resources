# FHIR Declarative Pipeline

A Declarative Automation Bundle (DABs) that ingests synthetic FHIR R4 bundles
through a three-stage Lakeflow Spark Declarative Pipeline stack: file movement,
bronze ingestion, and typed silver tables per resource type.

---

## Prerequisites

### 1. synthea_on_dbx (required for synthetic data generation)

The `Synthetic FHIR ETL Orchestration` job in this bundle calls
`synthea_on_dbx_job` as its first task. This job must be deployed to the same
workspace before this bundle can be deployed. The `synthea_job_id` variable
is resolved automatically by job name at `bundle validate` and `bundle deploy`
time — no manual ID lookup is needed. If the job is absent, validation will
fail with a lookup error.

To deploy `synthea_on_dbx`:

```bash
git clone https://github.com/mkgs-databricks-demos/synthea-on-fhir.git
cd synthea-on-fhir/synthea_on_dbx
databricks bundle deploy --target <target>
```

Repo: https://github.com/mkgs-databricks-demos/synthea-on-fhir/tree/main/synthea_on_dbx

The bundle deploys a job named exactly `synthea_on_dbx_job`. This name must
match the lookup in `databricks.yml`. If you deployed the synthea bundle in
`mode: development`, the job will be prefixed (e.g.
`[dev your_name] synthea_on_dbx_job`) and the lookup will fail. Deploy the
synthea bundle in production mode for `hedis` and `hls_fde` targets, or
override `synthea_job_id` manually in the `dev` target variables if needed.

---

## Deployment

```bash
# Validate first (resolves all variable lookups including synthea_job_id)
databricks bundle validate --target dev

# Deploy
databricks bundle deploy --target dev
```

Supported targets: `dev` (fevm-hedis, development mode), `hedis`
(fevm-hedis, production), `hls_fde` (fevm-hls-fde, production).

---

## Pipeline Architecture

Three Lakeflow Spark Declarative Pipelines run in sequence:

**1. Streaming FHIR Bundle Mover** (`fhir_bundle_mover_etl`)
Reads FHIR bundle files from a source volume using Auto Loader (binaryFile
format). A UDF distributes file copies across the cluster to the landing
volume. Results are tracked in the `file_tracker` streaming table. Already-
present destination files are skipped; re-running only processes new files.

**2. FHIR Bundle Resource Parsing ETL** (`fhir_bundle_ingestion_etl`)
Auto Loader text ingestion from the landing volume. Produces five tables:
`fhir_bronze`, `fhir_bronze_variant`, `bundle_meta`, `fhir_resources`
(exploded key-value pairs), and `fhir_resource_schemas` (one row per
resource type / column, with inferred VARIANT schema).

**3. FHIR Resource Silver ETL** (`fhir_resource_silver_etl`)
Dynamically generates typed silver tables for each FHIR resource type
discovered in `fhir_resource_schemas`. Per resource type:
- `{type}_raw` (private) — PIVOT of `fhir_resources` key-value rows into
  VARIANT columns, one column per field.
- `{type}` — Auto CDC Type 1 upserts; each VARIANT column cast to its
  inferred struct type from `fhir_resource_schemas`.

Schema evolution is handled automatically via `pipelines.reset.allowed = true`.
The silver pipeline must run after the ingestion ETL on first deployment
(two-pass: ingestion populates `fhir_resource_schemas`, silver reads it).

---

## Jobs

**FHIR Bundle Mover** (`fhir_bundle_mover_job`)
File-arrival triggered on the source volume. Accepts a `full_refresh`
parameter (default `"false"`). Uses a condition task to branch between
incremental and full refresh pipeline runs.

**FHIR ETL Orchestration** (`fhir_etl_orchestration_job`)
File-arrival triggered on the landing volume. Sequences ingestion ETL
followed by silver ETL. Accepts a `full_refresh` parameter. Use this job
to run or reprocess the ingestion and silver layers independently of file
movement.

**Synthetic FHIR ETL Orchestration** (`synthetic_fhir_etl_orchestration_job`)
End-to-end pipeline for synthetic data generation and ingestion. Linear
three-task sequence:
1. `run_synthea` — calls `synthea_on_dbx_job` with `catalog_use` set to
   the target catalog, `inject_bad_data=false`, `move_csv_to_landing=false`.
2. `run_fhir_bundle_mover` — moves generated bundles to the landing volume.
3. `run_fhir_etl_orchestration` — ingests and processes through bronze and
   silver layers.
Always runs incrementally. For full refresh, run the individual jobs directly.

---

## Variable Reference

| Variable | Description | Default |
|---|---|---|
| `catalog` | Target UC catalog | set per target |
| `schema` | Base schema name | set per target |
| `schema_resolved` | Resolved schema (includes target/user prefix in dev) | set per target |
| `source_catalog` | Catalog containing synthea source volume | set per target |
| `landing_volume` | Volume name for landed FHIR bundles | `landing` |
| `run_as_user` | User or service principal for job run_as | set per target |
| `synthea_job_id` | Resolved by lookup from job name `synthea_on_dbx_job` | lookup |
| `higher_level_service_principal` | SP application ID for hedis/hls_fde | `acf021b4-...` |

---

## Documentation

- [Declarative Automation Bundles in the workspace](https://docs.databricks.com/aws/en/dev-tools/bundles/workspace-bundles)
- [DABs configuration reference](https://docs.databricks.com/aws/en/dev-tools/bundles/reference)
- [DABs variable lookups](https://docs.databricks.com/aws/en/dev-tools/bundles/variables/)
- [synthea-on-fhir repo](https://github.com/mkgs-databricks-demos/synthea-on-fhir)
