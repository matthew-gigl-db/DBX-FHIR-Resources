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
**Path**: `/Workspace/.experiments/epic_on_fhir_requests`  
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
* AI Gateway with inference table logging, usage tracking, and rate limiting
* OpenTelemetry telemetry (traces, logs, metrics to Unity Catalog tables)
* Resource tags for cost attribution

### 5. JWK URL Databricks App
**Resource**: `jwk_url.app.yml`  
**Purpose**: Host JSON Web Key (JWK) sets for OAuth2 authentication  
**Use Case**: Epic requires a public JWK URL for validating JWT signatures

### 6. MLflow Artifacts Volume
**Resource**: `mlflow_artifacts.volume.yml`  
**Purpose**: Storage for model artifacts, experiment files, and logs

### 7. Model Registration Job
**Resource**: `epic_on_fhir_model_registration.job.yml`  
**Purpose**: Registers a new model version, validates, promotes to champion, and updates the serving endpoint configuration  
**Compute**: Serverless (shared environment with mlflow and databricks-sdk)  
**Trigger**: On-demand via `deploy.sh` or `databricks bundle run`  
**Conditional execution** via `updateAIGatewayOnly` parameter:
* `false` (default): Full deployment — register model, then update endpoint config
* `true`: Config-only — skip model registration, only update AI Gateway/telemetry/tags

**Tasks**:

| Task | Condition | Purpose |
| --- | --- | --- |
| `check_update_mode` | Always runs | Evaluates `updateAIGatewayOnly` parameter |
| `register_and_promote_model` | Runs if `updateAIGatewayOnly=false` | Model registration, validation, promotion |
| `update_endpoint_config` | Runs after all tasks complete (`run_if: ALL_DONE`) | Updates AI Gateway, telemetry, tags via SDK |

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
* `kid`: Key ID for JWT header
* `public_key`: Public key (served by JWK app)

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
databricks secrets put-secret --scope epic_on_fhir_oauth_keys --key kid
databricks secrets put-secret --scope epic_on_fhir_oauth_keys --key public_key
```

### 2. Update Configuration

Edit `databricks.yml` to set:
* `catalog`: Unity Catalog name
* `schema`: Schema for FHIR data (default: `epic_on_fhir`)
* `run_as_user`: User or service principal
* `token_url`: Epic OAuth2 token endpoint

### 3. Deploy Bundle

Use the `deploy.sh` script for a complete deployment (recommended), or run individual `databricks bundle` commands manually.

#### Using deploy.sh (Recommended)

```bash
cd /Workspace/Users/<user>/epic-on-fhir/epic_on_fhir

# Validate first
databricks bundle validate -t <target>

# Deploy
./deploy.sh <target>
```

See the [Deploy Script](#deploy-script-deploysh) section below for full details.

#### Manual Deployment

```bash
# Validate bundle
databricks bundle validate -t dev

# Deploy infrastructure only
databricks bundle deploy -t dev

# Run model registration job (full deployment)
databricks bundle run -t dev epic_on_fhir_model_registration

# Or update endpoint config only (no model registration)
databricks bundle run -t dev epic_on_fhir_model_registration --params updateAIGatewayOnly=true
```

> **Note**: Manual deployment requires understanding the chicken-and-egg dependency
> between the serving endpoint and model registration. The deploy script handles this
> automatically. See the deploy script section for details.

### 4. Access Resources

After deployment:
* **MLflow Experiment**: Available in workspace under `/Workspace/.experiments/`
* **Model Serving**: Endpoint accessible via REST API
* **JWK App**: Databricks App URL for Epic registration
* **Unity Catalog**: Tables in configured catalog/schema

## Deploy Script (`deploy.sh`)

The deploy script provides single-command, idempotent deployment that handles resource ordering dependencies automatically.

### Usage

```bash
./deploy.sh [target]
```

**Arguments:**
* `target` — Bundle target (default: `dev`). One of: `dev`, `sandbox_prod`, `hls_fde_sandbox_prod`, `prod`

**Examples:**
```bash
./deploy.sh                      # Deploy to dev (default)
./deploy.sh sandbox_prod         # Deploy to sandbox production
./deploy.sh hls_fde_sandbox_prod # Deploy to HLS FDE sandbox
./deploy.sh prod                 # Deploy to production
```

### Four-Phase Deployment

The script runs four phases to handle the chicken-and-egg dependency between the model serving endpoint (which requires a model version to exist) and the model registration notebook (which requires the registered model resource to exist).

#### Phase 1: Deploy Bundle Infrastructure

```
databricks bundle deploy -t <target>
```

Creates all bundle resources: schema, experiment, registered model, volume, app, job, and serving endpoint. On **first deployment**, the serving endpoint may fail because no model version exists yet — this is expected.

#### Phase 2: Run Model Registration Job

```
databricks bundle run -t <target> epic_on_fhir_model_registration
```

Runs the job with default parameters (`updateAIGatewayOnly=false`). The `register_and_promote_model` task runs the `epic-on-fhir-requests-model` notebook on serverless compute:
1. Builds the `EpicFhirPyfuncModel` pyfunc
2. Logs and registers a new model version in Unity Catalog
3. Sets challenger alias on the new version
4. Validates with traced predictions against Epic's sandbox (GET and POST payloads)
5. Validates JSON serialization of responses
6. Promotes challenger → champion (rotates prior champion to "prior" alias)
7. Finds and updates the serving endpoint to serve the new champion version

The `update_endpoint_config` task then runs to apply AI Gateway, telemetry, and tag settings. On **first deployment**, this task exits gracefully if the endpoint doesn't exist yet (the notebook detects this and calls `dbutils.notebook.exit()`).

#### Phase 3: Conditional Re-deploy

```
databricks bundle deploy -t <target>   # only if Phase 1 had partial failure
```

If Phase 1 failed partially (e.g., serving endpoint couldn't be created), Phase 3 re-deploys the bundle. Now that a model version exists from Phase 2, the serving endpoint creation succeeds.

#### Phase 4: Conditional Endpoint Config Update

```
databricks bundle run -t <target> epic_on_fhir_model_registration --params updateAIGatewayOnly=true
```

Only runs if Phase 1 had partial failure. On first deployment, Phase 2's `update_endpoint_config` task skipped because the endpoint didn't exist. Now that Phase 3 created it, Phase 4 re-runs the job with `updateAIGatewayOnly=true` to apply AI Gateway, telemetry, and tags without re-registering the model.

**On subsequent runs**, Phase 1 fully succeeds (model version already exists), so Phases 3 and 4 are skipped — the script is idempotent.

### Flow Diagram

```
Phase 1: bundle deploy
    ├─ schema, experiment, registered model, volume, app, job  ✓
    └─ serving endpoint  ✓ (or ⚠ if no model version yet)
         │
Phase 2: bundle run epic_on_fhir_model_registration
    ├─ check_update_mode → false (full deployment)
    ├─ register_and_promote_model:
    │   ├─ Register model v(N) → set challenger alias
    │   ├─ Validate with traced predictions
    │   ├─ Promote challenger → champion (rotate prior)
    │   └─ Update serving endpoint to v(N)
    └─ update_endpoint_config:
        └─ ✓ (or ⚠ SKIPPED if endpoint doesn't exist yet)
         │
Phase 3: bundle deploy  (only if Phase 1 was partial)
    └─ serving endpoint  ✓ (model version now exists)
         │
Phase 4: bundle run --params updateAIGatewayOnly=true  (only if Phase 1 was partial)
    ├─ check_update_mode → true (config-only)
    ├─ register_and_promote_model → SKIPPED
    └─ update_endpoint_config:
        ├─ AI Gateway (inference tables, usage tracking, rate limits)
        ├─ Telemetry (OTel traces, logs, metrics tables)
        └─ Tags (component, environment, project, owner)
```

### Prerequisites

* Databricks CLI installed and authenticated for the target workspace
* Secret scope configured with Epic OAuth2 credentials (`client_id`, `private_key`, `kid`, `public_key`)
* Bundle validated: `databricks bundle validate -t <target>`

### Job Parameters

The model registration job accepts these parameters (all have bundle-resolved defaults):

| Parameter | Default Source | Description |
| --- | --- | --- |
| `catalog` | `resources.schemas...catalog_name` | Unity Catalog catalog name |
| `schema` | `resources.schemas...name` | Unity Catalog schema name |
| `registered_model_name` | `resources.schemas...catalog_name`.`schemas...name`.`registered_models...name` | Full 3-level UC model namespace |
| `endpoint_name` | `resources.model_serving_endpoints...name` | Serving endpoint name |
| `updateAIGatewayOnly` | `"false"` | Skip model registration, only update endpoint config |

The `register_and_promote_model` task passes `registered_model_name` to the notebook. The `update_endpoint_config` task passes `endpoint_name`, `catalog`, `schema`, and tag values.

### Package Dependencies

The serverless environment installs these packages (from Databricks' own package mirror — **not** the PyPI proxy):

* `mlflow>=2.10.0` — Model logging and registry
* `databricks-sdk>=0.20.0` — Serving endpoint management

> **Important**: Do not add `--index-url` or `--extra-index-url` to the serverless
> environment dependencies. Serverless compute, Databricks Apps, and model serving all
> run on Databricks-managed infrastructure with their own package mirror. The PyPI proxy
> (`pypi-proxy.dev.databricks.com`) is unreachable from these environments.

## Deployment Targets

| Target | Environment | Catalog | Schema | Workspace | Client ID Key |
| --- | --- | --- | --- | --- | --- |
| **dev** | Development | mkgs_dev | epic_on_fhir | fe-vm-mkgs-databricks-demos | client_id |
| **sandbox_prod** | Sandbox (prod-like) | mkgs | open_epic_smart_on_fhir | fe-vm-mkgs-databricks-demos | client_id |
| **hls_fde_sandbox_prod** | HLS FDE Sandbox | hls_fde | open_epic_smart_on_fhir | fevm-hls-fde | client_id |
| **prod** | Production | main | epic_on_fhir | dbc-de8ffabd-1dae | client_id_prod |

> **Note**: Production targets (`sandbox_prod`, `hls_fde_sandbox_prod`, `prod`) use
> `name_prefix` which is applied to all resource names (schema, model, endpoints).
> The `registered_model_name` job parameter resolves to the full prefixed 3-level
> namespace automatically.

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
      "http_method": "get",
      "resource": "Patient",
      "action": "<patient-fhir-id>"
    }
  ]
}
```

### Response

```json
{
  "predictions": [
    "{\"response_status_code\": 200, \"response_time_seconds\": 0.25, \"response_headers\": {...}, \"response_text\": \"...\", \"response_url\": \"...\"}"
  ]
}
```

Each prediction is a JSON-serialized string containing the Epic FHIR API response.

## Proxy Configuration

The bundle uses Databricks PyPI and npm proxies **for local development only**.

| Location | Purpose | File |
| --- | --- | --- |
| PyPI proxy | `uv sync` for local dev | `pyproject.toml` (`[[tool.uv.index]]`) |
| npm proxy | `npm install` for JWK app local dev | `.npmrc` |

Canonical proxy URLs are defined in `databricks.yml` variables (`var.pip_index_url`, `var.npm_registry_url`). The static files (`pyproject.toml`, `.npmrc`) have comments pointing to the canonical source — update manually if the proxy URL changes.

**Databricks-managed compute** (serverless, Apps, model serving) uses its own package mirror and **cannot reach** the proxy. Do not add proxy configuration to job dependencies, app YAML, app `requirements.txt`, or model serving conda environments.

## Development Workflow

1. **Test in Sandbox**: Use Epic's sandbox environment (`client_id`)
2. **Train Models**: Run experiments in dev workspace
3. **Register Model**: Promote to Unity Catalog model registry
4. **Deploy to Serving**: Create model serving endpoint
5. **Production Deployment**: Use production credentials (`client_id_prod`)

## Monitoring & Observability

* **Model Serving Metrics**: Request latency, throughput, error rates
* **MLflow Tracking**: Model performance, experiment comparisons
* **MLflow Tracing**: Traced predictions during validation for debugging
* **AI Gateway Inference Tables**: Request/response payload logging for audit
* **OpenTelemetry**: Traces, logs, and metrics persisted to Unity Catalog Delta tables
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

### Deploy Script Failures

* **Phase 1 partial failure**: Expected on first deploy (serving endpoint needs a model version). Phases 3 and 4 will handle it.
* **Phase 2 failure**: Check notebook cell output in the job run. Common causes: secret scope not configured, Epic sandbox unreachable, MLflow experiment permissions. The `update_endpoint_config` task exits gracefully if the endpoint doesn't exist yet — this is normal on first deploy.
* **Phase 4 failure**: The endpoint exists (Phase 3 created it) but the SDK calls failed. Check the `update-serving-endpoint-config` notebook output for API errors.
* **Package install timeout**: Do **not** add `--extra-index-url` to serverless dependencies. The proxy is unreachable from serverless compute.

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
