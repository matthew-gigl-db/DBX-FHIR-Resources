from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.table(
    name="fhir_bundle_change_feed",
    comment="Streaming view of FHIR bundle Zerobus table change feed capturing all INSERT, UPDATE, and DELETE operations"
)
def fhir_bundle_change_feed():
    """
    Initialize streaming read from the Zerobus table's change data feed.
    
    Captures all change events with CDC metadata:
    - _change_type: INSERT, UPDATE_PREIMAGE, UPDATE_POSTIMAGE, DELETE
    - _commit_version: Delta version when the change occurred
    - _commit_timestamp: Timestamp when the change was committed
    
    All original table columns are preserved:
    - bundle_uuid (primary key)
    - fhir (VARIANT)
    - source_system
    - event_timestamp
    - request_detail (VARIANT)
    """
    return (
        spark.readStream
        .format("delta")
        .option("readChangeFeed", "true")
        .option("startingVersion", "0")  # Read all changes from the beginning
        .table("himss.redox.fhir_bundle_zerobus")
        .withColumn("_processed_at", F.current_timestamp())
    )
