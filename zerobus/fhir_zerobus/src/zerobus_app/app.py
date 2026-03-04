# app.py
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

from config import (
    ZEROBUS_SERVER_ENDPOINT,
    WORKSPACE_URL,
    FHIR_BUNDLE_TABLE_NAME,
    CLIENT_ID,
    CLIENT_SECRET,
)

app = FastAPI(title="FHIR → Zerobus Ingest App")

zerobus_sdk = None
zerobus_stream = None


@app.on_event("startup")
def startup_event():
    global zerobus_sdk, zerobus_stream
    try:
        # Create SDK client
        zerobus_sdk = ZerobusSdk(ZEROBUS_SERVER_ENDPOINT, WORKSPACE_URL)

        table_props = TableProperties(FHIR_BUNDLE_TABLE_NAME)
        options = StreamConfigurationOptions(record_type=RecordType.JSON)

        # Open a long-lived JSON stream for this table
        zerobus_stream = zerobus_sdk.create_stream(
            CLIENT_ID,
            CLIENT_SECRET,
            table_props,
            options,
        )
    except Exception as e:
        # If startup fails, the app will respond 500 to all requests.
        print(f"Failed to initialize Zerobus stream: {e}")
        zerobus_sdk = None
        zerobus_stream = None


@app.on_event("shutdown")
def shutdown_event():
    global zerobus_stream
    if zerobus_stream is not None:
        try:
            zerobus_stream.close()
        except Exception as e:
            print(f"Error closing Zerobus stream: {e}")


@app.post("/api/v1/ingest/fhir-bundle")
async def ingest_fhir_bundle(request: Request):
    """
    Accepts arbitrary JSON (e.g., a FHIR Bundle) and writes it
    into the `fhir` VARIANT column of TABLE_NAME via Zerobus.
    """
    global zerobus_stream

    if zerobus_stream is None:
        raise HTTPException(
            status_code=500,
            detail="Zerobus stream not initialized.",
        )

    try:
        payload = await request.json()  # Already JSON-compatible.
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload.",
        )

    # Shape the record to match the table schema:
    #   - bundle_uuid: unique identifier (primary key)
    #   - fhir: FHIR bundle payload as VARIANT
    #   - source_system: app title
    #   - event_timestamp: when payload was posted
    #   - ingest_datetime: auto-populated by DEFAULT current_timestamp()
    record = {
        "bundle_uuid": str(uuid.uuid4()),
        "fhir": payload,
        "source_system": app.title,
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        ack = zerobus_stream.ingest_record(record)  # dict → JSON → VARIANT
        ack.wait_for_ack()  # Wait until persisted.
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to write to Zerobus: {e}",
        )

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "bundle_uuid": record["bundle_uuid"]},
    )
