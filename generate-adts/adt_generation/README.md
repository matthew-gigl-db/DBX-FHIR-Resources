# HL7 ADT Message Generation

Generate synthetic HL7 v2.5 ADT (Admission, Discharge, Transfer) messages for testing clinical event workflows, HL7 interfaces, and healthcare integration systems.

## Overview

This asset bundle provides automated generation of realistic HL7 ADT messages representing patient encounters in a hospital setting. The generated messages conform to HL7 v2.5 standards and can be used for testing, development, and demonstration of healthcare integration workflows.

### What are ADT Messages?

**ADT** (Admission, Discharge, Transfer) messages are HL7 v2.x messages that communicate patient movement and administrative events within healthcare facilities. They are fundamental to hospital information systems integration.

### Key Message Types

* **ADT\^A01**: Patient Admission
* **ADT\^A02**: Patient Transfer
* **ADT\^A03**: Patient Discharge
* **ADT\^A04**: Patient Registration
* **ADT\^A08**: Patient Update

### Key Features

* **Synthetic Patient Data**: Realistic demographics without PHI
* **Clinical Event Simulation**: Multi-step patient journeys (admit → transfer → discharge)
* **HL7 v2.5 Conformance**: Standard-compliant message structure
* **Configurable Scale**: Generate 10s to 1000s of patient events
* **Unity Catalog Storage**: Messages stored in volumes for downstream processing
* **Databricks Job Orchestration**: Scheduled or on-demand generation

## Architecture

```
ADT Generator (Python/Spark)
    ↓ Generate Synthetic Patients
    ↓ Simulate Clinical Events
    ↓ Format as HL7 v2.5 ADT Messages
Unity Catalog Volume (hl7_synthetic)
    → ADT messages as .hl7 files
    → Available for downstream ingestion
```

## Bundle Resources

### 1. ADT Generator Job
**Resource**: `adt_generator.job.yml`  
**Name**: `adt_generator` (varies by target)  
**Purpose**: Execute ADT message generation workflow  
**Schedule**: On-demand (configurable)  
**Cluster**: Serverless or job cluster

**Job Tasks**:
1. Generate synthetic patient demographics
2. Create encounter sequences (admission → events → discharge)
3. Format each event as HL7 ADT message
4. Write HL7 messages to Unity Catalog volume

## Configuration Variables

### Patient Generation
* **`num_patients`**: Number of synthetic patients (default: 27)
* **`events_per_patient_max`**: Maximum ADT events per patient (default: 8)

### HL7 Configuration
* **`hl7_version`**: HL7 standard version (default: "2.5")
* **`sending_app`**: MSH-3 Sending Application (default: "DATABRICKS_SIM")
* **`sending_facility`**: MSH-4 Sending Facility (default: "DBX_FAC")
* **`receiving_app`**: MSH-5 Receiving Application (default: "DOWNSTREAM_SYS")
* **`receiving_facility`**: MSH-6 Receiving Facility (default: "DST_FAC")

### Storage Configuration
* **`catalog_use`**: Unity Catalog name (default: "main")
* **`schema_use`**: Schema within catalog (default: "healthcare")
* **`volume_name`**: Volume for HL7 file storage (default: "hl7_synthetic")
* **`relative_path`**: Subdirectory within volume (default: "adt")

## Sample HL7 ADT Message

### ADT^A01 - Patient Admission

```hl7
MSH|^~\&|DATABRICKS_SIM|DBX_FAC|DOWNSTREAM_SYS|DST_FAC|20250305123045||ADT^A01|MSG00001|P|2.5
EVN|A01|20250305123045
PID|1||123456^^^MRN||DOE^JOHN^A||19800115|M|||123 MAIN ST^^BOSTON^MA^02115||617-555-0100|||M|NON|987654321
PV1|1|I|4E^401^01^DBX_FAC^^^^ROOM|A||||||MED^MEDICINE^^^^^||||R||||||V123456|||||||||||||||||||||DBX_FAC|||||20250305110000
```

### Message Segments Explained

* **MSH** (Message Header): Message metadata, sender/receiver info
* **EVN** (Event Type): Event details and timestamp
* **PID** (Patient Identification): Demographics, identifiers, contact info
* **PV1** (Patient Visit): Encounter details, location, attending physician

## Getting Started

### Prerequisites

* Databricks workspace with Unity Catalog enabled
* Unity Catalog volume for HL7 file storage (see `adt_generation_infra`)
* Python 3.8+ with HL7 libraries (e.g., `hl7apy` or `python-hl7`)
* Databricks CLI authenticated

### 1. Deploy Infrastructure First

Deploy the `adt_generation_infra` bundle to create required volumes:

```bash
cd ../adt_generation_infra
databricks bundle deploy -t himss2026
```

### 2. Configure Generation Parameters

Edit `databricks.yml` variables section or override at deployment:

```yaml
variables:
  num_patients: "100"               # Generate 100 patients
  events_per_patient_max: "5"      # Up to 5 events each
  catalog_use: "himss"             # Target catalog
  schema_use: "redox"              # Target schema
  volume_name: "extract"           # Volume name
```

### 3. Deploy ADT Generator

```bash
# Validate bundle
databricks bundle validate -t himss2026

# Deploy
databricks bundle deploy -t himss2026
```

### 4. Run the Job

**Option A: Via UI**
1. Click the deployment rocket 🚀 in the left sidebar
2. Find the `adt_generator` job
3. Click **Run**

**Option B: Via CLI**
```bash
databricks bundle run adt_generator -t himss2026
```

**Option C: With Parameter Overrides**
```bash
databricks jobs run-now \
  --job-name "adt_generator" \
  --notebook-params '{"num_patients": "50", "events_per_patient_max": "10"}'
```

### 5. Access Generated Messages

```python
# List generated HL7 files
dbutils.fs.ls("/Volumes/himss/redox/extract/adt/")

# Read a sample message
message_content = dbutils.fs.head("/Volumes/himss/redox/extract/adt/patient_001_event_001.hl7")
print(message_content)
```

## Deployment Targets

| Target | Workspace | Catalog | Schema | Volume |
|--------|-----------|---------|--------|--------|
| **dev** | fe-vm-mkgs-databricks-demos | main | healthcare | hl7_synthetic |
| **himss2026** | fe-sandbox-himss2026 | himss | redox | extract |

## Generated Event Sequences

The generator creates realistic patient journey sequences:

### Example Patient Journey

1. **ADT\^A01** (Admission): Patient admitted to Emergency Department
2. **ADT\^A02** (Transfer): Moved to ICU
3. **ADT\^A02** (Transfer): Transferred to medical floor
4. **ADT\^A08** (Update): Demographics updated
5. **ADT\^A03** (Discharge): Patient discharged home

### Encounter Types
* Emergency admissions
* Scheduled surgeries
* Observation stays
* Inpatient admissions
* Outpatient visits

### Clinical Departments
* Emergency Department (ED)
* Intensive Care Unit (ICU)
* Medical/Surgical floors
* Operating Rooms (OR)
* Observation units

## File Naming Convention

Generated files follow this pattern:
```
{volume_path}/adt/patient_{patient_id}_event_{sequence}.hl7
```

Examples:
* `patient_001_event_001.hl7` - First admission for patient 001
* `patient_001_event_002.hl7` - Transfer event for patient 001
* `patient_027_event_008.hl7` - Eighth event for patient 027

## Use Cases

### 1. Testing HL7 Interfaces
Generate test data for HL7 integration engines:
```python
# Read ADT messages for testing
adt_messages = spark.read.text("/Volumes/himss/redox/extract/adt/*.hl7")
adt_messages.show(truncate=False)
```

### 2. Developing ADT Parsers
Test your HL7 parsing logic:
```python
from hl7apy import parser

# Parse an ADT message
message = parser.parse_file("/Volumes/himss/redox/extract/adt/patient_001_event_001.hl7")
print(f"Patient: {message.PID.PID_5}")
print(f"Event: {message.EVN.EVN_1}")
print(f"Visit: {message.PV1.PV1_3}")
```

### 3. Simulating Real-time Feeds
Stream messages to an HL7 listener:
```python
import time
import socket

# Send messages to HL7 listener (MLLP protocol)
def send_hl7_message(host, port, message):
    MLLP_START = b'\x0b'
    MLLP_END = b'\x1c\r'
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(MLLP_START + message.encode() + MLLP_END)

# Stream messages with delays
for file in dbutils.fs.ls("/Volumes/himss/redox/extract/adt/"):
    message = dbutils.fs.head(file.path)
    send_hl7_message("hl7-listener.example.com", 2575, message)
    time.sleep(1)  # 1 message per second
```

### 4. Building Analytics Pipelines
Parse ADT messages into structured tables:
```python
# Parse HL7 into structured data
from pyspark.sql.functions import udf
from pyspark.sql.types import StructType, StructField, StringType

def parse_adt(hl7_text):
    # Parse HL7 and extract fields
    # Returns dictionary with patient_id, event_type, timestamp, etc.
    pass

parse_udf = udf(parse_adt, return_schema)

parsed_adts = (
    spark.read.text("/Volumes/himss/redox/extract/adt/*.hl7")
    .withColumn("parsed", parse_udf("value"))
    .select("parsed.*")
)

parsed_adts.write.mode("overwrite").saveAsTable("himss.redox.adt_events")
```

## Monitoring & Troubleshooting

### Check Job Status
```bash
databricks jobs get --job-name "adt_generator"
databricks jobs list-runs --job-name "adt_generator" --limit 10
```

### Verify File Generation
```python
# Count generated files
files = dbutils.fs.ls("/Volumes/himss/redox/extract/adt/")
print(f"Generated {len(files)} HL7 ADT messages")

# Check file sizes
total_size = sum(file.size for file in files)
print(f"Total size: {total_size / 1024:.2f} KB")
```

### Validate HL7 Format
```python
from hl7apy import parser
from hl7apy.exceptions import ParserError

# Validate all messages
for file in dbutils.fs.ls("/Volumes/himss/redox/extract/adt/"):
    try:
        message = parser.parse_file(file.path)
        print(f"✓ Valid: {file.name}")
    except ParserError as e:
        print(f"✗ Invalid: {file.name} - {e}")
```

## Advanced Configuration

### Custom Event Distributions
Modify the job notebook to adjust:
* Admission type probabilities (emergency vs. scheduled)
* Length of stay distributions
* Transfer patterns
* Discharge disposition (home, SNF, expired, etc.)

### Adding Custom Segments
Extend messages with additional segments:
* **OBX** (Observation Results): Lab values, vitals
* **DG1** (Diagnosis): ICD-10 codes
* **PR1** (Procedures): CPT codes
* **IN1/IN2** (Insurance): Payer information

## Documentation & Resources

* [HL7 v2.5 Specification](http://www.hl7.org/implement/standards/product_brief.cfm?product_id=144)
* [HL7apy Library](https://python-hl7.readthedocs.io/)
* [MLLP Protocol](https://www.hl7.org/documentcenter/public_temp_2C240ED7-1C23-BA17-0CA8E0CA5D3C6B90/wg/inm/mllp_transport_specification.PDF)
* [Unity Catalog Volumes](https://docs.databricks.com/en/data-governance/unity-catalog/volumes.html)

## Support

* **Project**: Synthea-on-FHIR
* **Business Unit**: Healthcare and Life Sciences
* **Primary Developer**: matthew.giglia@databricks.com
* **Companion Bundle**: `adt_generation_infra` (prerequisite)
