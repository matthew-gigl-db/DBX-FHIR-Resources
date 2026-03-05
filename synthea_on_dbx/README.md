# Synthea on Databricks

Generate, process, and analyze synthetic healthcare data using Synthea™ with Databricks Delta Live Tables (DLT) for realistic FHIR R4 healthcare datasets.

## Overview

This asset bundle orchestrates the generation of synthetic patient data using Synthea (Synthetic Patient Population Simulator), processes it through Delta Live Tables pipelines, and stores it in Unity Catalog for analytics, testing, and development purposes. The data conforms to HL7 FHIR R4 standards.

### What is Synthea?

**Synthea** is an open-source synthetic patient and associated health records generator that models the medical history of synthetic patients. It creates realistic, de-identified patient data including demographics, encounters, conditions, medications, procedures, lab results, and more.

### Key Features

* **Synthetic FHIR R4 Data**: Generate realistic healthcare data without PHI concerns
* **Delta Live Tables Pipeline**: Automated data processing and quality checks
* **Unity Catalog Storage**: Governed data assets with lineage tracking
* **Job Orchestration**: Scheduled or on-demand data generation
* **Configurable Scale**: Generate from 10s to millions of synthetic patients
* **FHIR Resource Types**: Patient, Encounter, Observation, Condition, Medication, Procedure, and more

## Architecture

```
Synthea Generator
    ↓ FHIR R4 JSON/CSV
Volume: synthetic_files_raw
    ↓ Auto Loader
Volume: landing
    ↓ Delta Live Tables Pipeline
Unity Catalog Tables (synthea_data_gen schema)
    → Patient, Encounter, Observation, Condition, etc.
    → Analytics & ML Ready
```

## Bundle Resources

### 1. Unity Catalog Schema
**Resource**: `data_gen.schema.yml`  
**Name**: `synthea_data_gen`  
**Purpose**: Schema for storing processed FHIR resources  
**Tables Created**:
* `patient` - Patient demographics and identifiers
* `encounter` - Clinical encounters (visits, admissions)
* `observation` - Lab results, vital signs, clinical observations
* `condition` - Diagnoses and problems
* `medication_request` - Prescriptions and medication orders
* `procedure` - Surgical procedures and interventions
* `immunization` - Vaccination records
* `allergy_intolerance` - Allergies and intolerances
* `care_plan` - Treatment plans
* `claim` - Healthcare claims and billing

### 2. Landing Volume
**Resource**: `landing.volume.yml`  
**Name**: `landing`  
**Purpose**: Staging area for incoming Synthea-generated files  
**Usage**: DLT Auto Loader monitors this volume for new data

### 3. Raw Files Volume
**Resource**: `synthetic_files_raw.volume.yml`  
**Name**: `synthetic_files_raw`  
**Purpose**: Store raw Synthea output before processing  
**Formats**: FHIR JSON, CSV, or NDJSON

### 4. Delta Live Tables Pipeline
**Resource**: `pipeline_synthea_data_model.pipeline.yml`  
**Name**: `synthea_data_model` (varies by target)  
**Purpose**: Process raw Synthea data into curated FHIR tables  
**Features**:
* Auto Loader for incremental ingestion
* Data quality checks and validation
* FHIR resource parsing and normalization
* Schema evolution and enforcement
* Lineage tracking via Unity Catalog

**Source Code**: Located in `synthea_on_dbx_etl/` directory

### 5. Orchestration Job
**Resource**: `synthea_on_dbx_job.job.yml`  
**Name**: `synthea_on_dbx_job`  
**Purpose**: Coordinate Synthea generation and pipeline execution  
**Schedule**: Configurable (default: on-demand)

## Getting Started

### Prerequisites

* Databricks workspace with Unity Catalog enabled
* Cluster with Synthea installed or Docker for Synthea
* Python 3.8+ for orchestration scripts
* Databricks CLI authenticated

### 1. Install Synthea (Optional - if generating locally)

```bash
# Download Synthea
wget https://github.com/synthetichealth/synthea/releases/latest/download/synthea-with-dependencies.jar

# Generate sample data (Massachusetts, 100 patients)
java -jar synthea-with-dependencies.jar -p 100 Massachusetts
```

Or use Docker:
```bash
docker run --rm -v $PWD/output:/output synthetichealth/synthea:latest -p 100
```

### 2. Configure Bundle

Edit `databricks.yml` variables:
* `catalog`: Unity Catalog name (e.g., `mkgs_dev`, `mkgs`)
* `schema`: Schema name (default: `synthea_data_gen`)
* `volume`: Landing volume name (default: `landing`)
* `notifications`: Email addresses for job failure alerts
* `run_as_user`: User or service principal for job execution

### 3. Deploy Bundle

```bash
# Validate configuration
databricks bundle validate -t dev

# Deploy to development
databricks bundle deploy -t dev

# Deploy to HIMSS demo environment
databricks bundle deploy -t himss2026
```

### 4. Upload Synthea Data

```bash
# Upload to raw volume
databricks fs cp ./output/fhir/*.json \
  dbfs:/Volumes/<catalog>/<schema>/synthetic_files_raw/ --recursive

# Or upload to landing volume for immediate processing
databricks fs cp ./output/fhir/*.json \
  dbfs:/Volumes/<catalog>/<schema>/landing/ --recursive
```

### 5. Run the Pipeline

**Option A: Via UI**
1. Click the deployment rocket 🚀 in the left sidebar
2. Find `synthea_data_model` pipeline
3. Click **Run**

**Option B: Via CLI**
```bash
databricks bundle run synthea_on_dbx_job -t dev
```

**Option C: Via Jobs API**
```bash
databricks jobs run-now --job-name "<prefix> synthea_on_dbx_job"
```

## Data Schema

### Patient Table
```sql
CREATE TABLE patient (
  id STRING,
  identifier ARRAY<STRUCT<system: STRING, value: STRING>>,
  name ARRAY<STRUCT<family: STRING, given: ARRAY<STRING>>>,
  gender STRING,
  birthDate DATE,
  address ARRAY<STRUCT<city: STRING, state: STRING, postalCode: STRING>>,
  maritalStatus STRUCT<coding: ARRAY<STRUCT<code: STRING, display: STRING>>>,
  ...
)
```

### Observation Table
```sql
CREATE TABLE observation (
  id STRING,
  subject STRUCT<reference: STRING>,
  encounter STRUCT<reference: STRING>,
  code STRUCT<coding: ARRAY<STRUCT<system: STRING, code: STRING, display: STRING>>>,
  effectiveDateTime TIMESTAMP,
  valueQuantity STRUCT<value: DOUBLE, unit: STRING, system: STRING>,
  ...
)
```

## Deployment Targets

| Target | Workspace | Catalog | Schema | Mode |
|--------|-----------|---------|--------|------|
| **dev** | fe-vm-mkgs-databricks-demos | mkgs_dev | synthea_data_gen | Development |
| **prod** | fe-vm-mkgs-databricks-demos | mkgs | synthea_data_gen | Production |
| **himss2026** | fe-sandbox-himss2026 | himss | synthea_data_gen | HIMSS Demo |

## Configuration Variables

### Data Generation Parameters
* `num_patients`: Number of synthetic patients to generate (configurable in job)
* `state`: US state for patient generation (default: Massachusetts)
* `city`: Specific city (optional)
* `seed`: Random seed for reproducibility (optional)

### Infrastructure
* `catalog`: Unity Catalog for storage
* `schema`: Schema name within catalog
* `volume`: Landing volume for Auto Loader
* `serverless_environment_version`: Serverless DBR version (default: 4)

### Operational
* `notifications`: Email list for job failures
* `run_as_user`: Execution identity
* `tags_*`: Resource tagging for cost tracking and organization

## Use Cases

### 1. Testing & Development
Generate realistic test data for application development without using real PHI:
```python
# Query synthetic patients
spark.sql("""
  SELECT id, name, gender, birthDate, city
  FROM synthea_data_gen.patient
  WHERE city = 'Boston' AND birthDate > '2000-01-01'
""").display()
```

### 2. Demo Environments
Create compelling healthcare demos with realistic data:
```python
# Patient journey analysis
spark.sql("""
  SELECT 
    p.id as patient_id,
    p.name,
    COUNT(DISTINCT e.id) as encounter_count,
    COUNT(DISTINCT c.id) as condition_count,
    COUNT(DISTINCT m.id) as medication_count
  FROM synthea_data_gen.patient p
  LEFT JOIN synthea_data_gen.encounter e ON p.id = e.subject.reference
  LEFT JOIN synthea_data_gen.condition c ON p.id = c.subject.reference
  LEFT JOIN synthea_data_gen.medication_request m ON p.id = m.subject.reference
  GROUP BY p.id, p.name
""").display()
```

### 3. ML Model Training
Train healthcare AI/ML models on synthetic data:
```python
# Feature engineering for readmission prediction
from databricks.feature_engineering import FeatureEngineeringClient

fe = FeatureEngineeringClient()

# Create feature table from synthetic encounters
features = spark.sql("""
  SELECT 
    patient_id,
    age,
    gender,
    COUNT(encounter_id) as num_encounters_30d,
    AVG(length_of_stay) as avg_los,
    MAX(severity_score) as max_severity
  FROM synthea_data_gen.patient_features
  GROUP BY patient_id, age, gender
""")

fe.create_table(
  name="synthea_data_gen.patient_risk_features",
  primary_keys=["patient_id"],
  df=features
)
```

### 4. FHIR Validation
Test FHIR parsing and validation logic:
```python
# Validate FHIR resource structure
from fhir.resources.patient import Patient

df = spark.table("synthea_data_gen.patient")
for row in df.limit(10).collect():
    patient = Patient.parse_obj(row.asDict())
    print(f"Valid FHIR Patient: {patient.id}")
```

## Monitoring & Maintenance

### Pipeline Health
* Monitor DLT pipeline runs in the Databricks UI
* Check data quality metrics in the pipeline dashboard
* Review lineage in Unity Catalog

### Data Freshness
```sql
SELECT 
  MAX(ingest_datetime) as last_update,
  COUNT(*) as total_patients
FROM synthea_data_gen.patient;
```

### Storage Usage
```sql
DESCRIBE DETAIL synthea_data_gen.patient;
```

## Troubleshooting

### Pipeline Failures
* Check DLT pipeline logs for specific errors
* Verify volume permissions and file accessibility
* Ensure Synthea output format matches expected schema

### Schema Mismatches
* Review FHIR resource version (must be R4)
* Check for custom Synthea modules that add non-standard fields
* Use schema evolution settings in DLT configuration

### Performance Optimization
* Adjust Auto Loader max files per trigger
* Optimize cluster size for data volume
* Consider partitioning large tables by date

## Documentation & Resources

* [Synthea GitHub](https://github.com/synthetichealth/synthea)
* [Synthea Wiki](https://github.com/synthetichealth/synthea/wiki)
* [FHIR R4 Specification](https://hl7.org/fhir/R4/)
* [Delta Live Tables](https://docs.databricks.com/workflows/delta-live-tables/)
* [Databricks Auto Loader](https://docs.databricks.com/ingestion/auto-loader/)
* [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/)

## Support

* **Parent Project**: synthea-on-fhir
* **Business Unit**: Healthcare and Life Sciences
* **Primary Developer**: matthew.giglia@databricks.com
* **Target Stakeholders**: Databricks Healthcare Customers
