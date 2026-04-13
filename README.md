# Synthea-on-FHIR Healthcare Data Platform

A comprehensive healthcare data platform for demonstrating FHIR (Fast Healthcare Interoperability Resources) integration, synthetic data generation, real-time ingestion, and AI/ML model serving on Databricks.

## Overview

This repository contains multiple Databricks Asset Bundles that work together to provide a complete healthcare data platform. Each bundle is deployable independently or as part of a larger ecosystem, supporting development, staging, and production environments.

**Target Audience**: Healthcare Providers, Health Plans, Healthcare IT Teams  
**Primary Use Cases**: FHIR data integration, synthetic healthcare data generation, real-time clinical data ingestion, healthcare AI/ML deployment

## Project Structure

```
synthea-on-fhir/
├── redox_mcp/                  # Redox MCP Server for AI agents
├── epic_on_fhir/              # Epic FHIR integration & ML serving
├── synthea_on_dbx/            # Synthetic healthcare data generation
├── zerobus/
│   ├── fhir_zerobus/          # Real-time FHIR ingestion application
│   └── fhir_zerobus_infra/    # Infrastructure for Zerobus deployment
└── generate-adts/
    ├── adt_generation/         # HL7 ADT message generation
    └── adt_generation_infra/   # Infrastructure for ADT generation
```

## Asset Bundles

### 1. Redox MCP (`redox_mcp/`)

**Purpose**: Databricks Application hosting the Redox MCP (Model Context Protocol) server for use in AI agent frameworks.

**Key Resources**:
* **Databricks App**: Redox MCP Server (`redox_mcp_serving.app.yml`)
* **Secret Scope**: OAuth credentials for Redox API (`redox_oauth.secret_scope.yml`)
* **Unity Catalog Schema**: `redox` schema for FHIR data storage (`redox.schema.yml`)
* **Volume**: Binary storage for Redox MCP executable (`bin.volume.yml`)

**Prerequisites**: 
* Access to Redox MCP closed beta
* Ability to download from https://data-models.prod.redoxengine.com/downloads/redox-mcp/

**Documentation**: See [redox_mcp/README.md](redox_mcp/README.md)

---

### 2. Epic on FHIR (`epic_on_fhir/`)

**Purpose**: Integration with Epic EHR systems via FHIR APIs, including OAuth authentication, data extraction, and ML model serving for FHIR request handling.

**Key Resources**:
* **MLflow Experiment**: Model training and tracking (`epic_on_fhir_requests.experiment.yml`)
* **Registered Model**: FHIR request handling model (`epic_on_fhir_requests.registered_model.yml`)
* **Model Serving Endpoint**: Real-time FHIR API (`epic_on_fhir_requests.serving.yml`)
* **Databricks App**: JWK URL service for OAuth (`jwk_url.app.yml`)
* **Unity Catalog Schema**: `epic_on_fhir` schema (`epic_on_fhir.schema.yml`)
* **Volume**: MLflow artifacts storage (`mlflow_artifacts.volume.yml`)
* **Registration Job**: Model registration and UC alias management (`epic_on_fhir_model_registration.job.yml`)
* **Deployment Job**: MLflow 3 evaluation, approval, and promotion (`epic_on_fhir_model_deployment.job.yml`)

**Authentication**: RS384 JWT-based OAuth2 with Epic's FHIR endpoints

**Documentation**: See [epic_on_fhir/README.md](epic_on_fhir/README.md)

---

### 3. Synthea on Databricks (`synthea_on_dbx/`)

**Purpose**: Generate synthetic healthcare data using Synthea, process it through Delta Live Tables (DLT) pipelines, and store it in Unity Catalog for analytics and testing.

**Key Resources**:
* **DLT Pipeline**: Data processing and transformation (`pipeline_synthea_data_model.pipeline.yml`)
* **Job**: Orchestration for synthetic data generation (`synthea_on_dbx_job.job.yml`)
* **Unity Catalog Schema**: `synthea_data_gen` schema (`data_gen.schema.yml`)
* **Volumes**: 
  - `landing`: Incoming synthetic data files (`landing.volume.yml`)
  - `synthetic_files_raw`: Raw Synthea output (`synthetic_files_raw.volume.yml`)

**Use Cases**: Testing, demos, development data, FHIR format validation

**Documentation**: See [synthea_on_dbx/README.md](synthea_on_dbx/README.md)

---

### 4. FHIR Zerobus Ingestion (`zerobus/fhir_zerobus/`)

**Purpose**: Production-ready FastAPI application for real-time streaming ingestion of HL7 FHIR Bundles to Unity Catalog using Databricks Zerobus SDK.

**Key Features**:
* **Ultra-low Latency**: Microsecond-level acknowledgments via Zerobus
* **React Dashboard**: Interactive UI with health monitoring and API documentation
* **FastAPI REST Endpoint**: `/api/v1/ingest/fhir-bundle` for FHIR bundle ingestion
* **DLT Pipeline**: Downstream processing of ingested FHIR data
* **Direct Table Writes**: No Kafka or streaming clusters required

**Key Resources**:
* **Databricks App**: FastAPI ingestion service (`zerobus_app.app.yml`)
* **Secret Scope**: Zerobus credentials (`zerobus.secret_scope.yml`)
* **Job**: Unity Catalog table setup (`fhir_bundle_table_setup.job.yml`)
* **DLT Pipeline**: FHIR data processing (`fhir_zerobus_etl.pipeline.yml`)

**Table Schema**:
```sql
CREATE TABLE fhir_bundle_zerobus (
  bundle_uuid STRING,
  fhir VARIANT,           -- Native semi-structured JSON support
  source_system STRING,
  event_timestamp BIGINT,
  ingest_datetime TIMESTAMP
);
```

**Documentation**: 
* [zerobus/fhir_zerobus/README.md](zerobus/fhir_zerobus/README.md) - Complete application guide
* [zerobus/fhir_zerobus/DEPLOYMENT.md](zerobus/fhir_zerobus/DEPLOYMENT.md) - Deployment instructions
* [zerobus/fhir_zerobus/SECRET_SCOPE_SETUP.md](zerobus/fhir_zerobus/SECRET_SCOPE_SETUP.md) - Secret management

---

### 5. FHIR Zerobus Infrastructure (`zerobus/fhir_zerobus_infra/`)

**Purpose**: Infrastructure resources for Zerobus-based FHIR ingestion (Unity Catalog schemas, volumes, service principals).

**Resources**: Infrastructure definitions (schemas, volumes, external locations)

**Documentation**: See [zerobus/fhir_zerobus_infra/README.md](zerobus/fhir_zerobus_infra/README.md)

---

### 6. ADT Generation (`generate-adts/adt_generation/`)

**Purpose**: Generate synthetic HL7 ADT (Admission, Discharge, Transfer) messages for testing clinical event workflows.

**Key Resources**:
* **Job**: HL7 ADT message generator (`adt_generator.job.yml`)

**Configuration Variables**:
* `num_patients`: Number of synthetic patients (default: 27)
* `events_per_patient_max`: Max ADT events per patient (default: 8)
* `hl7_version`: HL7 message version (default: 2.5)
* `sending_app`, `sending_facility`: HL7 message headers
* `catalog_use`, `schema_use`, `volume_name`: Unity Catalog output locations

**Message Types Generated**: ADT\^A01 (Admit), ADT\^A03 (Discharge), ADT\^A02 (Transfer)

**Documentation**: 
* [generate-adts/adt_generation/README.md](generate-adts/adt_generation/README.md)
* [generate-adts/adt_generation/README_WORKFLOW.md](generate-adts/adt_generation/README_WORKFLOW.md)

---

### 7. ADT Generation Infrastructure (`generate-adts/adt_generation_infra/`)

**Purpose**: Infrastructure provisioning for ADT message generation (Unity Catalog volumes for HL7 file storage).

**Key Resources**:
* **Volumes**: External and managed volumes for HL7 storage (`volumes.yml`)

**Documentation**: See [generate-adts/adt_generation_infra/README.md](generate-adts/adt_generation_infra/README.md)

---

## Deployment

All asset bundles use Databricks Asset Bundles (DABs) for deployment. Each bundle supports multiple deployment targets:

### Common Deployment Targets

| Target | Workspace | Catalog | Purpose |
|--------|-----------|---------|---------|
| **dev** | fe-vm-mkgs-databricks-demos | mkgs_dev | Development and testing |
| **prod** | fe-vm-mkgs-databricks-demos | mkgs | Production |
| **himss2026** | fe-sandbox-himss2026 | himss | HIMSS conference demos |
| **free_edition** | dbc-e5684c0a-20fa | mkgs | Free tier testing |

### Quick Start

1. **Navigate to a bundle directory**:
   ```bash
   cd <bundle-directory>
   ```

2. **Validate the bundle**:
   ```bash
   databricks bundle validate -t <target>
   ```

3. **Deploy the bundle**:
   ```bash
   databricks bundle deploy -t <target>
   ```

4. **Run jobs or pipelines**:
   * Use the Databricks UI Deployments panel (rocket icon 🚀)
   * Or CLI: `databricks bundle run <resource-name> -t <target>`

### Workspace UI Deployment

All bundles can be deployed directly from the Databricks workspace:

1. Open the bundle folder in the Databricks workspace
2. Click the **deployment rocket** 🚀 in the left sidebar
3. Click **Deploy** in the Deployments panel
4. Monitor deployment progress
5. Run resources by hovering over them and clicking **Run**

## Technologies Used

* **Databricks Asset Bundles (DABs)**: Infrastructure as Code for Databricks
* **Unity Catalog**: Data governance, lineage, and access control
* **Delta Live Tables (DLT)**: Declarative ETL pipelines
* **Databricks Apps**: Hosted web applications with built-in auth
* **Databricks Zerobus**: Ultra-low latency streaming ingestion
* **Model Serving**: Real-time ML model endpoints
* **MLflow**: Experiment tracking and model registry
* **FastAPI**: High-performance REST APIs
* **React.js**: Modern web dashboards

## Healthcare Standards Supported

* **HL7 FHIR R4**: Fast Healthcare Interoperability Resources
* **HL7 v2.5**: ADT, ORM, ORU, and other clinical messaging
* **OAuth 2.0**: Secure healthcare API authentication
* **SMART on FHIR**: App authorization framework

## Project Metadata

* **Business Unit**: Healthcare and Life Sciences
* **Primary Developer**: matthew.giglia@databricks.com
* **Target Stakeholders**: Healthcare Providers and Health Plans
* **Project Tags**: FHIR, Healthcare, Synthetic Data, Real-time Ingestion, AI/ML

## Additional Resources

* [Databricks Asset Bundles Documentation](https://docs.databricks.com/en/dev-tools/bundles/)
* [Unity Catalog Documentation](https://docs.databricks.com/data-governance/unity-catalog/)
* [Databricks Zerobus Overview](https://docs.databricks.com/ingestion/zerobus-overview)
* [FHIR Specification](https://hl7.org/fhir/)
* [HL7 Standards](https://www.hl7.org/)

## License

See [LICENSE](LICENSE) file for details.
