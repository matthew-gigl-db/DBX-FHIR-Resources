# ADT Generation Infrastructure

Infrastructure provisioning bundle for HL7 ADT message generation, managing Unity Catalog volumes and external storage locations for storing synthetic HL7 messages.

## Overview

This asset bundle deploys the foundational infrastructure required by the ADT generation workflow (`adt_generation`). It provisions Unity Catalog volumes for storing generated HL7 ADT messages and configures external storage locations if needed.

**Deployment Order**: Deploy this infrastructure bundle **before** deploying the `adt_generation` application bundle.

## Purpose

Separating infrastructure from the generation workflow provides:

* **Resource Lifecycle Management**: Volumes persist across job runs
* **Storage Flexibility**: Support for both managed and external volumes
* **Permission Control**: Centralized volume access management
* **Reusability**: Multiple generators can share the same volumes

## Bundle Resources

### 1. Unity Catalog Volumes
**Resource**: `volumes.yml`  
**Purpose**: Create volumes for HL7 message storage

**Volume Types**:
* **Managed Volumes**: Databricks-managed storage (default)
* **External Volumes**: Customer-managed cloud storage (S3, ADLS, GCS)

**Volume Structure**:
```
{catalog}.{schema}.{volume_name}/
├── adt/                 # ADT messages
│   ├── patient_001_event_001.hl7
│   ├── patient_001_event_002.hl7
│   └── ...
├── orm/                 # Order messages (future)
└── oru/                 # Result messages (future)
```

## Configuration Variables

### Unity Catalog
* **`catalog`**: Catalog name for volumes (default: "main")
* **`schema`**: Schema within catalog (default: "default")

### External Storage (Optional)
* **`external_location`**: Base cloud storage path (e.g., "s3://bucket/path")

## Deployment Targets

| Target | Workspace | Catalog | Schema | External Location |
|--------|-----------|---------|--------|-------------------|
| **dev** | fe-vm-mkgs-databricks-demos | dev_catalog | dev_schema | Local (managed) |
| **himss2026** | fe-sandbox-himss2026 | himss | redox | s3://himss2026-external-s3bucket/himss2026 |

## Getting Started

### Prerequisites

* Databricks workspace with Unity Catalog enabled
* Unity Catalog CREATE VOLUME permissions
* (Optional) Cloud storage bucket and IAM permissions for external volumes
* Databricks CLI authenticated

### 1. Choose Volume Type

#### Option A: Managed Volume (Recommended)
Uses Databricks-managed storage. No additional cloud configuration needed.

**Configuration**:
```yaml
# In volumes.yml
volumes:
  hl7_synthetic:
    catalog_name: ${var.catalog}
    schema_name: ${var.schema}
    name: hl7_synthetic
    volume_type: MANAGED
```

#### Option B: External Volume
Uses your own cloud storage (S3, ADLS, or GCS).

**Configuration**:
```yaml
# In volumes.yml
volumes:
  hl7_synthetic:
    catalog_name: ${var.catalog}
    schema_name: ${var.schema}
    name: hl7_synthetic
    volume_type: EXTERNAL
    storage_location: ${var.external_location}/hl7_synthetic
```

### 2. Configure Cloud Storage (External Volumes Only)

#### AWS S3

```bash
# Create S3 bucket
aws s3 mb s3://hl7-synthetic-messages

# Create IAM policy for Databricks access
cat > databricks-hl7-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::hl7-synthetic-messages",
        "arn:aws:s3:::hl7-synthetic-messages/*"
      ]
    }
  ]
}
EOF

aws iam create-policy --policy-name DatabricksHL7Access \
  --policy-document file://databricks-hl7-policy.json
```

#### Azure ADLS Gen2

```bash
# Create storage account
az storage account create \
  --name hl7syntheticmessages \
  --resource-group databricks-rg \
  --location eastus \
  --sku Standard_LRS

# Create container
az storage container create \
  --name hl7-messages \
  --account-name hl7syntheticmessages

# Grant Databricks access (via service principal or managed identity)
```

#### GCP Cloud Storage

```bash
# Create GCS bucket
gsutil mb -l us-east1 gs://hl7-synthetic-messages

# Grant Databricks service account access
gsutil iam ch \
  serviceAccount:databricks@project.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://hl7-synthetic-messages
```

### 3. Update Configuration

Edit `databricks.yml` variables:

```yaml
variables:
  catalog: "himss"
  schema: "redox"
  external_location: "s3://himss2026-external-s3bucket/himss2026"  # If using external
```

### 4. Deploy Infrastructure

```bash
# Validate bundle
databricks bundle validate -t himss2026

# Deploy
databricks bundle deploy -t himss2026
```

### 5. Verify Volumes

```bash
# List volumes in schema
databricks unity-catalog volumes list \
  --catalog himss \
  --schema redox

# Describe specific volume
databricks unity-catalog volumes get \
  --full-name himss.redox.hl7_synthetic
```

### 6. Grant Permissions

```bash
# Grant READ/WRITE to ADT generation job service principal
databricks grants update volume himss.redox.hl7_synthetic \
  --service-principal <service-principal-id> \
  --privilege READ_VOLUME,WRITE_VOLUME
```

### 7. Deploy ADT Generator

Now deploy the `adt_generation` bundle:
```bash
cd ../adt_generation
databricks bundle deploy -t himss2026
```

## Volume Access Patterns

### Write HL7 Messages (from ADT generator)

```python
# Write HL7 message to volume
hl7_message = """MSH|^~\&|DATABRICKS_SIM|..."""

dbutils.fs.put(
    f"/Volumes/himss/redox/hl7_synthetic/adt/patient_001.hl7",
    hl7_message,
    overwrite=True
)
```

### Read HL7 Messages (for processing)

```python
# List all ADT messages
files = dbutils.fs.ls("/Volumes/himss/redox/hl7_synthetic/adt/")
print(f"Found {len(files)} ADT messages")

# Read specific message
message = dbutils.fs.head("/Volumes/himss/redox/hl7_synthetic/adt/patient_001.hl7")
print(message)

# Read all messages into DataFrame
hl7_df = spark.read.text("/Volumes/himss/redox/hl7_synthetic/adt/*.hl7")
```

## Storage Management

### Monitor Volume Usage

```sql
-- Check volume size
DESCRIBE VOLUME EXTENDED himss.redox.hl7_synthetic;

-- List files (via SQL)
LIST '/Volumes/himss/redox/hl7_synthetic/adt/';
```

### Clean Up Old Messages

```python
# Delete messages older than 30 days
import datetime

cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)

for file in dbutils.fs.ls("/Volumes/himss/redox/hl7_synthetic/adt/"):
    if file.modificationTime < cutoff_date.timestamp() * 1000:
        dbutils.fs.rm(file.path)
        print(f"Deleted: {file.name}")
```

### Backup to Cloud Storage

```bash
# AWS S3
aws s3 sync \
  /dbfs/Volumes/himss/redox/hl7_synthetic/ \
  s3://backup-bucket/hl7-messages/ \
  --exclude "*" --include "*.hl7"

# Azure ADLS
az storage blob sync \
  --source /dbfs/Volumes/himss/redox/hl7_synthetic/ \
  --destination hl7-messages \
  --account-name backupstorage
```

## Permission Model

```
Unity Catalog: himss
└── Schema: redox
    └── Volume: hl7_synthetic
        ├── Owner: Infrastructure Admin
        ├── Permissions:
        │   ├── ADT Generator Job: READ_VOLUME, WRITE_VOLUME
        │   ├── Processing Pipeline: READ_VOLUME
        │   └── Analytics Users: READ_VOLUME
        └── Contents:
            ├── adt/ (ADT messages)
            ├── orm/ (Order messages)
            └── oru/ (Result messages)
```

## Cost Optimization

### Managed Volumes
* Charged per GB stored
* Automatic lifecycle management
* No egress charges within Databricks

### External Volumes
* Use your existing cloud storage pricing
* Control lifecycle policies directly
* May incur egress charges for cross-region access

**Recommendation**: Start with managed volumes for simplicity, migrate to external if needed for cost optimization at scale.

## Troubleshooting

### Volume Creation Fails
* Verify Unity Catalog permissions (CREATE VOLUME)
* Check catalog and schema exist
* Ensure external location credentials are valid (if applicable)

### Permission Denied on Write
* Verify service principal has WRITE_VOLUME grant
* Check schema-level permissions (USAGE, CREATE)
* Review volume ownership

### External Volume Connection Issues
* Verify IAM role/policy (AWS)
* Check service principal credentials (Azure)
* Confirm network connectivity (VPC, firewall)

### Volume Not Visible
```bash
# Refresh Unity Catalog metadata
databricks unity-catalog volumes get --full-name himss.redox.hl7_synthetic

# Check grants
databricks grants get volume himss.redox.hl7_synthetic
```

## Maintenance & Operations

### Regular Cleanup
Schedule periodic cleanup of old messages:
```python
# In a scheduled job
RETENTION_DAYS = 90
cleanup_path = "/Volumes/himss/redox/hl7_synthetic/adt/"

files_deleted = 0
for file in dbutils.fs.ls(cleanup_path):
    age_days = (time.time() - file.modificationTime/1000) / 86400
    if age_days > RETENTION_DAYS:
        dbutils.fs.rm(file.path)
        files_deleted += 1

print(f"Deleted {files_deleted} old HL7 messages")
```

### Monitoring
```sql
-- Volume usage over time (create monitoring table)
CREATE TABLE IF NOT EXISTS monitoring.volume_usage (
  volume_name STRING,
  file_count INT,
  total_size_gb DOUBLE,
  check_timestamp TIMESTAMP
);

-- Record daily stats
INSERT INTO monitoring.volume_usage
SELECT 
  'himss.redox.hl7_synthetic' as volume_name,
  COUNT(*) as file_count,
  SUM(size) / 1024 / 1024 / 1024 as total_size_gb,
  CURRENT_TIMESTAMP() as check_timestamp
FROM (
  LIST '/Volumes/himss/redox/hl7_synthetic/adt/'
);
```

## Documentation & Resources

* [Unity Catalog Volumes](https://docs.databricks.com/en/data-governance/unity-catalog/volumes.html)
* [External Locations](https://docs.databricks.com/en/data-governance/unity-catalog/external-locations.html)
* [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/)
* [Cloud Storage Best Practices](https://docs.databricks.com/en/data-governance/unity-catalog/best-practices.html)

## Support

* **Project**: Synthea-on-FHIR
* **Business Unit**: Healthcare and Life Sciences
* **Primary Developer**: matthew.giglia@databricks.com
* **Companion Bundle**: `adt_generation` (application)
* **Deployment Type**: Infrastructure (prerequisite)
