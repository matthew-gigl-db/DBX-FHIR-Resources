# Epic on FHIR Integration

Comprehensive integration with Epic EHR systems using HL7 FHIR R4 APIs, including OAuth2 authentication, data extraction, ML model training, and real-time model serving for FHIR request handling.

## Overview

This asset bundle provides production-ready integration with Epic's FHIR endpoints, enabling secure access to patient data, clinical observations, encounters, and other healthcare resources. The bundle includes ML capabilities for intelligent FHIR request optimization and serving.

### Key Features

* **Epic FHIR R4 Integration**: Native support for Epic's FHIR endpoints
* **OAuth2 Authentication**: RS384 JWT-based authentication (backend services)
* **SMART on FHIR**: Support for SMART authorization framework
* **ML Model Serving**: Real-time FHIR request handling and optimization
* **JWK Hosting**: Databricks App for serving JSON Web Keys (JWKs)
* **Unity Catalog Storage**: Secure storage of FHIR resources
* **MLflow Tracking**: Experiment tracking for model development

## Architecture

```
Epic EHR System
    ↓ FHIR R4 API (OAuth2)
Databricks - Data Ingestion
    ↓ Unity Catalog
FHIR Data Storage (epic_on_fhir schema)
    ↓ MLflow
Model Training & Experimentation
    ↓ Model Registry
Model Serving Endpoint
    → Real-time FHIR Request API
```

## Bundle Resources

### 1. Unity Catalog Schema
**Resource**: `epic_on_fhir.schema.yml`  
**Purpose**: Schema for storing FHIR resources and model artifacts  
**Tables**: Patient, Observation, Encounter, Condition, MedicationRequest, etc.

### 2. MLflow Experiment
**Resource**: `epic_on_fhir_requests.experiment.yml`  
**Path**: `/Workspace/experiments/epic_on_fhir_requests`  
**Purpose**: Track model training experiments for FHIR request optimization

### 3. Registered Model
**Resource**: `epic_on_fhir_requests.registered_model.yml`  
**Name**: `epic_on_fhir_requests`  
**Purpose**: Versioned ML models for FHIR request handling and optimization

### 4. Model Serving Endpoint
**Resource**: `epic_on_fhir_requests.serving.yml`  
**Endpoint**: `epic_on_fhir_requests`  
**Purpose**: Real-time API for FHIR request processing  
**Features**:
* Auto-scaling based on load
* Model versioning and A/B testing
* Query logging and monitoring

### 5. JWK URL Databricks App
**Resource**: `jwk_url.app.yml`  
**Purpose**: Host JSON Web Key (JWK) sets for OAuth2 authentication  
**Use Case**: Epic requires a public JWK URL for validating JWT signatures

### 6. MLflow Artifacts Volume
**Resource**: `mlflow_artifacts.volume.yml`  
**Purpose**: Storage for model artifacts, experiment files, and logs

### 7. Sample Job
**Resource**: `sample_job.job.yml`  
**Purpose**: Example job for FHIR data extraction and processing

## OAuth2 Authentication

### Backend Services (RS384)

This bundle uses Epic's Backend Services authentication (OAuth2 with JWT):

1. **Generate Key Pair**: Create RSA 4096-bit key pair
2. **Register with Epic**: Upload public key to Epic's portal
3. **Store in Secret Scope**: Save private key in `epic_on_fhir_oauth_keys`
4. **Generate JWT**: Sign JWT with private key (RS384 algorithm)
5. **Exchange for Token**: POST JWT to Epic's token endpoint
6. **Access FHIR API**: Use access token in Authorization header

### Secret Scope Configuration

Required secrets in `epic_on_fhir_oauth_keys`:
* `client_id`: Epic application client ID
* `client_id_prod`: Production client ID (for prod target)
* `private_key`: RSA private key (PEM format)
* `jwk_set`: JSON Web Key Set for public key hosting

## Getting Started

### Prerequisites

* Databricks workspace with Unity Catalog enabled
* Epic FHIR endpoint access (sandbox or production)
* Epic application registered with Backend Services enabled
* RSA key pair generated and registered with Epic
* Databricks CLI installed and authenticated

### 1. Configure Secrets

```bash
# Create secret scope (if not exists)
databricks secrets create-scope epic_on_fhir_oauth_keys

# Add Epic client credentials
databricks secrets put-secret --scope epic_on_fhir_oauth_keys --key client_id
databricks secrets put-secret --scope epic_on_fhir_oauth_keys --key private_key
databricks secrets put-secret --scope epic_on_fhir_oauth_keys --key jwk_set
```

### 2. Update Configuration

Edit `databricks.yml` to set:
* `catalog`: Unity Catalog name
* `schema`: Schema for FHIR data (default: `epic_on_fhir`)
* `run_as_user`: User or service principal
* `token_url`: Epic OAuth2 token endpoint
* `model_deployment_version`: Model version to deploy

### 3. Deploy Bundle

```bash
# Validate bundle
databricks bundle validate -t dev

# Deploy to development
databricks bundle deploy -t dev

# Deploy to production (when ready)
databricks bundle deploy -t prod
```

### 4. Access Resources

After deployment:
* **MLflow Experiment**: Available in workspace under `/Workspace/experiments/`
* **Model Serving**: Endpoint accessible via REST API
* **JWK App**: Databricks App URL for Epic registration
* **Unity Catalog**: Tables in configured catalog/schema

## Deployment Targets

| Target | Environment | Catalog | Schema | Client ID Key |
|--------|-------------|---------|--------|---------------|
| **dev** | Development | mkgs_dev | epic_on_fhir | client_id |
| **sandbox_prod** | Sandbox (prod-like) | mkgs | open_epic_smart_on_fhir | client_id |
| **prod** | Production | main | epic_on_fhir | client_id_prod |

## FHIR Resources Supported

* **Patient**: Demographics, identifiers
* **Observation**: Lab results, vitals, clinical observations
* **Encounter**: Visits, admissions, appointments
* **Condition**: Diagnoses, problems
* **MedicationRequest**: Prescriptions, med orders
* **Procedure**: Surgical procedures, interventions
* **AllergyIntolerance**: Allergies, intolerances
* **Immunization**: Vaccine records
* **DocumentReference**: Clinical documents, notes

## Model Serving API

### Endpoint Structure

```
POST https://<workspace-url>/serving-endpoints/epic_on_fhir_requests/invocations
Authorization: Bearer <databricks-token>
Content-Type: application/json

{
  "dataframe_records": [
    {
      "patient_id": "12345",
      "resource_type": "Observation",
      "query_params": {...}
    }
  ]
}
```

### Response

```json
{
  "predictions": [
    {
      "optimized_request": {...},
      "estimated_latency_ms": 250,
      "recommended_batch_size": 10
    }
  ]
}
```

## Development Workflow

1. **Test in Sandbox**: Use Epic's sandbox environment (`client_id`)
2. **Train Models**: Run experiments in dev workspace
3. **Register Model**: Promote to Unity Catalog model registry
4. **Deploy to Serving**: Create model serving endpoint
5. **Production Deployment**: Use production credentials (`client_id_prod`)

## Monitoring & Observability

* **Model Serving Metrics**: Request latency, throughput, error rates
* **MLflow Tracking**: Model performance, experiment comparisons
* **Unity Catalog Lineage**: Data flow from Epic to downstream tables
* **Databricks SQL**: Query FHIR data for analytics

## Troubleshooting

### Authentication Errors

* Verify private key format (PEM, RSA 4096-bit)
* Check client_id matches Epic registration
* Confirm token_url is correct for environment
* Validate JWT signature algorithm (RS384)

### Model Serving Issues

* Check model version is correctly deployed
* Verify endpoint has sufficient compute resources
* Review serving endpoint logs in Databricks UI

## Documentation & Resources

* [Epic FHIR Documentation](https://fhir.epic.com/)
* [SMART on FHIR](https://docs.smarthealthit.org/)
* [Databricks Model Serving](https://docs.databricks.com/machine-learning/model-serving/)
* [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/)
* [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/)

## Support

* **Primary Developer**: matthew.giglia@databricks.com
* **Business Unit**: Healthcare and Life Sciences
* **Project**: Open Epic Smart on FHIR
* **Target Audience**: Healthcare Providers and Health Plans
