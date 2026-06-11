"""Dynamic silver table generation for FHIR resource types.

Architecture (three-step pattern per resource type):

    fhir_resources
        -> {resource_type}_raw   (PRIVATE streaming table: PIVOT, all columns VARIANT)
        -> {resource_type}_typed (Temporary view: CAST each column to its inferred type)
        -> {resource_type}       (Target streaming table: Auto CDC Type 1 upserts)

The private _raw table is append-only and pipeline-internal (not published to the
catalog). It isolates the PIVOT step and adds a _processing_time column for CDC
sequencing.

The _typed temporary view performs the VARIANT-to-typed CAST and serves as the
source for the Auto CDC flow.

The final silver table is a target streaming table that receives SCD Type 1
(upsert/overwrite) changes via create_auto_cdc_flow. This means:
  - New resources are inserted.
  - Updated resources overwrite existing rows (matched by {resource_type}_uuid).
  - Ordering is determined by _processing_time.

Schema evolution is handled automatically: when new columns or changed struct
types appear in fhir_resource_schemas, the table definitions change and DLT
triggers a full refresh (pipelines.reset.allowed = true).

Why SQL CAST instead of a UDF:
  Spark UDFs have fixed return types, so a single UDF cannot dynamically cast
  to different types per column. SQL CAST(variant_col AS complex_type) natively
  handles VARIANT-to-typed conversions including nested ARRAY<STRUCT<...>> types.

Two-pass behavior:
  - First run of ingestion pipeline: Bronze and resource tables are populated.
  - First run of this silver pipeline: Silver tables are dynamically generated
    for each discovered resource type (e.g., Patient, Encounter, Condition).
  - Schema changes: If fhir_resource_schemas has new columns or changed types,
    the table definitions change and DLT triggers a full refresh automatically.
"""

from pyspark import pipelines as dp
from pyspark.sql.functions import col


# ---------------------------------------------------------------------------
# Columns excluded from the PIVOT per resource type.
#
# Very large VARIANT values (e.g., ExplanationOfBenefit.item at ~6 KB/row ×
# 14.6M rows = ~90 GB total, ExplanationOfBenefit.contained at ~552 bytes/row
# × 14.6M rows = ~8 GB) cause the PIVOT shuffle to OOM on serverless compute
# and hang indefinitely.
#
# Excluded columns are omitted from the silver table. Raw values remain
# queryable via:
#   SELECT value FROM {catalog}.{schema}.fhir_resources
#   WHERE resourceType = '<Type>' AND key = '<column>'
# ---------------------------------------------------------------------------
_PIVOT_SKIP_COLUMNS: dict[str, set[str]] = {
    "ExplanationOfBenefit": {"item", "contained"},
}


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

    Returns True if new columns or changed types are detected. DLT handles the
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
                f"Full refresh will be triggered by DLT."
            )
            return True
    except Exception:
        pass  # Table does not exist yet (first run)
    return False


# ---------------------------------------------------------------------------
# SQL generation helpers
# ---------------------------------------------------------------------------
def _build_cast_sql(columns: list[dict], rt_lower: str) -> str:
    """Build SELECT expressions that CAST each VARIANT column to its inferred type."""
    exprs = [f"`{rt_lower}_uuid`", "`bundle_uuid`", f"`{rt_lower}_url`"]
    for col in columns:
        name = col["column_name"]
        dtype = col["schema_as_struct"]
        exprs.append(f"CAST(`{name}` AS {dtype}) AS `{name}`")
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
    for col in columns:
        name = col["column_name"]
        dtype = col["schema_as_struct"]
        parts.append(
            f"`{name}` {dtype} "
            f"COMMENT 'FHIR {resource_type}.{name} element.'"
        )
    return ",\n        ".join(parts)


# ---------------------------------------------------------------------------
# Dynamic table generation
# ---------------------------------------------------------------------------
def _create_resource_tables(resource_type: str, columns: list[dict]) -> None:
    """Create a private raw, typed view, and CDC target table for a FHIR resource type."""
    rt_lower = resource_type.lower()

    # Exclude known oversized columns from the PIVOT to prevent OOM shuffles.
    # Skipped columns are omitted from the silver table; raw values remain in fhir_resources.
    skip = _PIVOT_SKIP_COLUMNS.get(resource_type, set())
    if skip:
        skipped = [c["column_name"] for c in columns if c["column_name"] in skip]
        columns = [c for c in columns if c["column_name"] not in skip]
        print(
            f"[{resource_type}] Skipping oversized PIVOT columns (excluded from silver): "
            f"{skipped}"
        )

    keys = [c["column_name"] for c in columns]
    keys_sql = ", ".join([f"'{k}'" for k in keys])

    # Build a key predicate to exclude oversized columns from the shuffle input.
    # The PIVOT reads all rows matching resourceType regardless of whether a key
    # appears in keys_sql. For ExplanationOfBenefit, 'item' averages ~6 KB/row
    # across 14.6M rows (~90 GB) and 'contained' adds ~8 GB more. Without this
    # filter those rows enter the shuffle even though they produce no output column,
    # causing serverless OOM. Filtering them before the GROUP BY reduces the EOB
    # shuffle from ~200 GB to ~25 GB.
    skip_filter = ""
    if skip:
        skipped_keys_sql = ", ".join([f"'{k}'" for k in sorted(skip)])
        skip_filter = f"\n                AND key NOT IN ({skipped_keys_sql})"

    # Log schema evolution if applicable
    _detect_schema_evolution(resource_type, columns)

    # --- Private raw table: append-only PIVOT with VARIANT columns ----------
    @dp.table(
        name=f"{rt_lower}_raw",
        comment=(
            f"Private intermediate FHIR {resource_type} records. "
            f"PIVOT of fhir_resources with all columns as VARIANT."
        ),
        table_properties={
            "delta.enableChangeDataFeed":          "true",
            "delta.enableDeletionVectors":         "true",
            "delta.enableRowTracking":             "true",
            "delta.autoOptimize.optimizeWrite":    "true",
            "delta.autoOptimize.autoCompact":      "true",
            # autoCompact and Predictive Optimization both issue OPTIMIZE transactions
            # on this table (file rewrites). These are tolerated by _typed_view, which
            # reads this table via spark.readStream.option("skipChangeCommits", "true").
            # skipChangeCommits silently skips compaction commits without re-emitting
            # rows or causing duplicates -- unlike ignoreChanges which re-reads rewritten
            # files and requires downstream deduplication.
            # Note: SQL STREAM() syntax does not support streaming options, which is why
            # private=True is omitted here -- _typed_view must use the Python readStream
            # API (which requires a catalog-published table).
            "delta.enableVariantShredding":        "true",
            "pipelines.channel":                   "PREVIEW",
            "delta.feature.variantType-preview":   "supported",
            "pipelines.reset.allowed":             "true",
            "quality": "bronze",
        },
    )
    def _raw():
        return spark.sql(f"""
            SELECT *, current_timestamp() AS _processing_time FROM (
                SELECT
                    resource_uuid AS {rt_lower}_uuid,
                    bundle_uuid,
                    fullUrl AS {rt_lower}_url,
                    key,
                    value
                FROM STREAM({_catalog}.{_schema}.fhir_resources)
                WHERE resourceType = '{resource_type}'{skip_filter}
            ) PIVOT (
                first(value) FOR key IN ({keys_sql})
            )
        """)

    # --- Typed temporary view: CAST from VARIANT to inferred types ----------
    cast_sql = _build_cast_sql(columns, rt_lower)

    @dp.temporary_view(name=f"{rt_lower}_typed")
    def _typed_view():
        return spark.sql(f"""
            SELECT
                {cast_sql},
                _processing_time
            FROM STREAM({rt_lower}_raw)
        """)

    # --- Target silver table: Auto CDC Type 1 upserts ----------------------
    schema_ddl = _build_schema_ddl(columns, resource_type)

    dp.create_streaming_table(
        name=rt_lower,
        comment=(
            f"Typed FHIR {resource_type} records with columns cast "
            f"from VARIANT to their inferred schemas. "
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
        source=f"{rt_lower}_typed",
        keys=[f"{rt_lower}_uuid"],
        sequence_by=col("_processing_time"),
        except_column_list=["_processing_time"],
        stored_as_scd_type=1,
    )


# ---------------------------------------------------------------------------
# Generate tables for each discovered resource type
# ---------------------------------------------------------------------------
for _rt, _cols in _resource_map.items():
    _create_resource_tables(_rt, _cols)
