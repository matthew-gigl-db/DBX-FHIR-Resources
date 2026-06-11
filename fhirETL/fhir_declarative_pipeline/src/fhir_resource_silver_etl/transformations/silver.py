"""Dynamic silver table generation for FHIR resource types — Fully Streaming.

Architecture (two-step pattern per resource type):

    fhir_resources_variant
        -> {resource_type}_extract  (Temporary view: streaming filter by resourceType +
                                     VARIANT path extraction + CAST to typed columns)
        -> {resource_type}          (Target streaming table: Auto CDC Type 1 upserts)

This pipeline is FULLY STREAMING end-to-end:
- Source: fhir_resources_variant streaming table (one row per resource, full VARIANT)
- Filter: WHERE resourceType = '{type}' (streaming filter, no aggregation)
- Extract: resource:fieldName path expressions + CAST (local per-row, no shuffle)
- Target: Auto CDC Type 1 keyed on {resource_type}_uuid

NO materialized views. NO PIVOT. NO CDF bridging.

The previous architecture required a PIVOT aggregation (first()) which forced
Complete output mode, breaking downstream streaming reads. This approach eliminates
the PIVOT entirely by reading from a pre-assembled per-resource VARIANT table and
extracting columns via VARIANT path expressions.

Benefits over previous PIVOT-based approach:
- Fully streaming (no batch/MV intermediary)
- No OOM risk from PIVOT shuffles (extraction is per-row, no shuffle)
- All columns includable (even large ones like EOB.item, EOB.contained)
- Simpler architecture (2 objects per type instead of 3)
- Directly compatible with FHIR server loading (resource VARIANT -> NDJSON/JSONB)
- Eliminates DELTA_SOURCE_TABLE_IGNORE_CHANGES errors entirely
- No dependency on Enzyme incrementalization behavior

Why SQL CAST instead of a UDF:
  Spark UDFs have fixed return types, so a single UDF cannot dynamically cast
  to different types per column. SQL CAST(variant_col AS complex_type) natively
  handles VARIANT-to-typed conversions including nested ARRAY<STRUCT<...>> types.

Two-pass behavior:
  - First run of ingestion pipeline: Bronze, fhir_resources_variant, and schema
    tables are populated.
  - First run of this silver pipeline: Silver tables are dynamically generated
    for each discovered resource type (e.g., Patient, Encounter, Condition).
  - Schema changes: If fhir_resource_schemas has new columns or changed types,
    the table definitions change and SDP triggers a full refresh automatically.

FHIR server loading (Lakebase/HAPI):
  The source table fhir_resources_variant stores each resource as a complete
  VARIANT document. This is the ideal staging format for:
  - NDJSON export for HAPI $import or Aidbox /fhir/$import
  - Direct VARIANT->JSONB casting for Aidbox on Databricks Lakebase
  - No information loss (all fields preserved, including large nested arrays)
"""

from pyspark import pipelines as dp
from pyspark.sql.functions import col


# ---------------------------------------------------------------------------
# Columns excluded from extraction per resource type (optional).
#
# Unlike the previous PIVOT approach, VARIANT path extraction does NOT require
# a shuffle, so large columns (e.g., EOB.item at ~6 KB/row x 14.6M rows) do
# NOT cause OOM. This dict is retained only for intentional exclusions where
# columns should remain queryable only via the VARIANT source and not
# materialized in the typed silver table.
#
# To exclude columns, uncomment and populate:
#   "ExplanationOfBenefit": {"item", "contained"},
# ---------------------------------------------------------------------------
_EXTRACT_SKIP_COLUMNS: dict[str, set[str]] = {}


# ---------------------------------------------------------------------------
# Discover resource types and their schemas from the ingestion pipeline
# ---------------------------------------------------------------------------
try:
    _catalog = spark.conf.get("pipeline.catalog_use")
    _schema = spark.conf.get("pipeline.schema_use")
    _fq_schemas_table = f"{_catalog}.{_schema}.fhir_resource_schemas"

    _resource_meta = (
        spark.table(_fq_schemas_table)
        .select("resourceType", "column_name", "schema_of_variant", "schema_as_struct")
        .collect()
    )

    # Build {resource_type: [{column_name, schema_of_variant, schema_as_struct}, ...]}
    _resource_map: dict[str, list[dict]] = {}
    for row in _resource_meta:
        _resource_map.setdefault(row.resourceType, []).append(
            {
                "column_name": row.column_name,
                "schema_of_variant": row.schema_of_variant,
                "schema_as_struct": row.schema_as_struct,
            }
        )

    # Sort columns alphabetically for consistent ordering across runs
    for rt in _resource_map:
        _resource_map[rt].sort(key=lambda x: x["column_name"])

except Exception:
    _resource_map = {}


# ---------------------------------------------------------------------------
# Schema evolution detection (observability)
# ---------------------------------------------------------------------------
def _detect_schema_evolution(resource_type: str, columns: list[dict]) -> bool:
    """Check if the silver table schema has changed, requiring a full refresh.

    Returns True if new columns or changed types are detected. SDP handles the
    actual full refresh via pipelines.reset.allowed = true.
    """
    rt_lower = resource_type.lower()
    try:
        existing_cols = {
            row.column_name
            for row in spark.sql(
                f"SELECT column_name FROM {_catalog}.information_schema.columns "
                f"WHERE table_catalog = '{_catalog}' "
                f"AND table_schema = '{_schema}' "
                f"AND table_name = '{rt_lower}'"
            ).collect()
        }
        expected_cols = (
            {f"{rt_lower}_uuid", "bundle_uuid", f"{rt_lower}_url"}
            | {c["column_name"] for c in columns}
        )
        new_cols = expected_cols - existing_cols
        if new_cols:
            print(
                f"[Schema Evolution] {resource_type}: "
                f"new columns detected: {new_cols}. "
                f"Full refresh will be triggered by SDP."
            )
            return True
    except Exception:
        pass  # Table does not exist yet (first run)
    return False


# ---------------------------------------------------------------------------
# SQL generation helpers
# ---------------------------------------------------------------------------
def _build_extract_exprs(columns: list[dict], rt_lower: str) -> str:
    """Build SELECT expressions that extract and CAST VARIANT paths to typed columns.

    Each column is extracted from the resource VARIANT via path expression
    (resource:fieldName) and cast to its inferred struct type. This is a
    per-row operation with no shuffle — fundamentally different from PIVOT.
    """
    exprs = [
        f"resource_uuid AS `{rt_lower}_uuid`",
        "`bundle_uuid`",
        f"fullUrl AS `{rt_lower}_url`",
        "`ingest_time`",
    ]
    for c in columns:
        name = c["column_name"]
        dtype = c["schema_as_struct"]
        exprs.append(f"CAST(resource:{name} AS {dtype}) AS `{name}`")
    return ",\n                ".join(exprs)


def _build_schema_ddl(columns: list[dict], resource_type: str) -> str:
    """Build the schema DDL string for the typed silver table."""
    rt_lower = resource_type.lower()
    parts = [
        (
            f"`{rt_lower}_uuid` STRING NOT NULL PRIMARY KEY "
            f"COMMENT 'Unique identifier for the FHIR {resource_type} resource.'"
        ),
        (
            f"`bundle_uuid` STRING NOT NULL "
            f"COMMENT 'Unique identifier for the FHIR bundle.'"
        ),
        (
            f"`{rt_lower}_url` STRING "
            f"COMMENT 'Full URL of the {resource_type} resource in the entry array.'"
        ),
    ]
    for c in columns:
        name = c["column_name"]
        dtype = c["schema_as_struct"]
        parts.append(
            f"`{name}` {dtype} "
            f"COMMENT 'FHIR {resource_type}.{name} element.'"
        )
    return ",\n        ".join(parts)


# ---------------------------------------------------------------------------
# Dynamic table generation — fully streaming, no materialized views
# ---------------------------------------------------------------------------
def _create_resource_tables(resource_type: str, columns: list[dict]) -> None:
    """Create a streaming extract view and CDC target table for a FHIR resource type.

    Pattern per resource type (2 objects, fully streaming):
      1. {type}_extract  - Temporary view: STREAM(fhir_resources_variant) filtered
                           by resourceType, VARIANT path extraction + CAST.
      2. {type}          - Streaming table: Auto CDC Type 1 upserts from _extract.
    """
    rt_lower = resource_type.lower()

    # Apply optional column exclusions
    skip = _EXTRACT_SKIP_COLUMNS.get(resource_type, set())
    if skip:
        skipped = [c["column_name"] for c in columns if c["column_name"] in skip]
        columns = [c for c in columns if c["column_name"] not in skip]
        print(
            f"[{resource_type}] Skipping columns (excluded from silver): "
            f"{skipped}"
        )

    # Log schema evolution if applicable
    _detect_schema_evolution(resource_type, columns)

    # --- Streaming extract view: filter + VARIANT path extraction + CAST ------
    # Reads fhir_resources_variant as a stream, filters to the target
    # resourceType, and extracts typed columns from the resource VARIANT via
    # path expressions (resource:fieldName). No aggregation, no shuffle —
    # pure append-mode streaming.
    extract_sql = _build_extract_exprs(columns, rt_lower)

    @dp.temporary_view(name=f"{rt_lower}_extract")
    def _extract():
        return spark.sql(f"""
            SELECT
                {extract_sql}
            FROM STREAM({_catalog}.{_schema}.fhir_resources_variant)
            WHERE resourceType = '{resource_type}'
        """)

    # --- Target silver table: Auto CDC Type 1 upserts -------------------------
    schema_ddl = _build_schema_ddl(columns, resource_type)

    dp.create_streaming_table(
        name=rt_lower,
        comment=(
            f"Typed FHIR {resource_type} records with columns extracted "
            f"from VARIANT via path expressions and cast to inferred schemas. "
            f"Auto CDC Type 1 upserts keyed on {rt_lower}_uuid."
        ),
        schema=f"\n        {schema_ddl}\n        ",
        cluster_by_auto=True,
        table_properties={
            "delta.enableChangeDataFeed":          "true",
            "delta.enableDeletionVectors":         "true",
            "delta.enableRowTracking":             "true",
            "delta.autoOptimize.optimizeWrite":    "true",
            "delta.autoOptimize.autoCompact":      "true",
            "delta.enableVariantShredding":        "true",
            "pipelines.channel":                   "PREVIEW",
            "delta.feature.variantType-preview":   "supported",
            "pipelines.reset.allowed":             "true",
            "quality": "silver",
        },
    )

    dp.create_auto_cdc_flow(
        target=rt_lower,
        source=f"{rt_lower}_extract",
        keys=[f"{rt_lower}_uuid"],
        sequence_by=col("ingest_time"),
        except_column_list=["ingest_time"],
        stored_as_scd_type=1,
    )


# ---------------------------------------------------------------------------
# Generate tables for each discovered resource type
# ---------------------------------------------------------------------------
for _rt, _cols in _resource_map.items():
    _create_resource_tables(_rt, _cols)
