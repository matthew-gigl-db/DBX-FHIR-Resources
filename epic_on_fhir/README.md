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
* **MLflow 3 Deployment Jobs**: Evaluation, human-in-the-loop approval (with auto-repair), and automated promotion
* **SQL Endpoint Testing**: `ai_query`-based FHIR endpoint test flow from the SQL Editor

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
Registration Job → sets "challenger" alias
    ↓ Triggers deployment job
Deployment Job → evaluate → approve (auto-repair) → promote to "champion"
    → Model Serving Endpoint (Real-time FHIR Request API)
        → SQL ai_query() / REST API / Python SDK
```

## Project Structure

```
epic_on_fhir/
├── databricks.yml                 # Bundle configuration (targets, variables, resources)
├── deploy.sh                      # Single-command deployment script (4-phase)
├── README.md                      # This file
├── pyproject.toml                 # Python project config (uv, local dev)
├── uv.lock                        # Dependency lockfile
├── .npmrc                         # npm proxy config (local dev)
├── .gitignore
│
├── resources/                     # Databricks Asset Bundle resource definitions
│   ├── epic_on_fhir.schema.yml
│   ├── epic_on_fhir_requests.experiment.yml
│   ├── epic_on_fhir_requests.registered_model.yml
│   ├── epic_on_fhir_requests.serving.yml
│   ├── epic_on_fhir_model_registration.job.yml
│   ├── epic_on_fhir_model_deployment.job.yml
│   ├── mlflow_artifacts.volume.yml
│   └── jwk_url.app.yml
│
├── src/                           # Source notebooks and Python modules
│   ├── epic-on-fhir-requests-model  # Model registration notebook
│   ├── evaluation                   # Evaluation notebook (deployment job task 1)
│   ├── approval                     # Approval check notebook (deployment job task 2)
│   ├── deployment                   # Deployment notebook (deployment job task 3)
│   ├── epic-smart-on-fhir-class-examples  # Interactive examples notebook
│   ├── epic-sandbox-basic-auth      # Basic auth examples notebook
│   │
│   ├── smart_on_fhir/              # Python package (bundled into model artifact)
│   │   ├── __init__.py
│   │   ├── auth.py                 # EpicApiAuth: JWT-based OAuth2
│   │   ├── endpoint.py             # EpicApiRequest: FHIR API client
│   │   ├── epic_fhir_pyfunc.py     # EpicFhirPyfuncModel: MLflow pyfunc
│   │   └── epic_fhir_model.py      # Models-from-code entrypoint
│   │
│   ├── jwk_url_app/                # Databricks App for hosting JWK sets
│   │   ├── app.py
│   │   └── requirements.txt
│   │
│   ├── queries/                    # SQL queries
│   │   └── Epic FHIR Endpoint Test Flow.dbquery.ipynb
│   │
│   └── _archive/                   # Deprecated notebooks (kept as reference)
│       └── update-serving-endpoint-config  # Superseded by deployment notebook + YAML
│
├── tests/                          # Pytest test suite
│   ├── conftest.py                 # Shared fixtures, path setup, constants
│   ├── test_auth.py                # EpicApiAuth unit tests
│   ├── test_endpoint.py            # EpicApiRequest unit tests
│   ├── test_epic_fhir_pyfunc.py    # EpicFhirPyfuncModel unit tests
│   ├── test_payloads.py            # FHIR payload construction tests
│   ├── test_registration_notebook.py   # Registration workflow tests
│   ├── test_evaluation_notebook.py     # Evaluation workflow tests
│   ├── test_approval_notebook.py       # Approval workflow tests
│   └── test_deployment_notebook.py     # Deployment workflow tests
│
└── fixtures/                       # Test fixtures and session records
    ├── examples/                   # Example FHIR payloads
    ├── images/                     # Documentation images
    ├── sessions/                   # Per-session development summaries
    │   ├── INDEX.md
    │   └── YYYY-MM-DD_description.md
    └── danger/                     # Destructive operation scripts
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
* AI Gateway with inference table logging, usage tracking, and rate limiting (configured declaratively in YAML)
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
**Purpose**: Registers a new model version to Unity Catalog with the "challenger" alias  
**Compute**: Serverless (shared environment with mlflow and databricks-sdk)  
**Trigger**: On-demand via `deploy.sh` or `databricks bundle run`  
**Concurrency**: `max_concurrent_runs: 1`

**Tasks**:

| Task | Purpose |
| --- | --- |
| `register_model` | Runs `epic-on-fhir-requests-model.ipynb` — builds pyfunc, logs to MLflow, registers to UC, sets "challenger" alias, exits with model metadata JSON |

### 8. Model Deployment Job
**Resource**: `epic_on_fhir_model_deployment.job.yml`  
**Purpose**: MLflow 3 deployment job — evaluates, approves, and promotes a model version from "challenger" to "champion"  
**Compute**: Serverless (shared environment with mlflow, databricks-sdk)  
**Trigger**: Auto-triggered on new model version creation, or on-demand  
**Concurrency**: `max_concurrent_runs: 1`

**Tasks**:

| Task | Depends On | Purpose |
| --- | --- | --- |
| `evaluation` | — | Loads model by name/version, runs traced FHIR predictions (GET Patient, POST Observation, POST AllergyIntolerance), validates JSON serialization, logs metrics (status codes, response times, pass/fail) to UC model version page and MLflow experiment |
| `approval_check` | `evaluation` | Checks Unity Catalog tag `approval_check = 'approved'` on model version. **Instant check** — fails immediately if not approved (`max_retries: 0`). The UC UI "Approve" button sets the tag and triggers **auto-repair**, which re-runs this task automatically. No polling or timeout. |
| `deployment` | `approval_check` | Promotes challenger → champion (rotates old champion → prior), updates serving endpoint version (preserving `environment_vars` from the current config), verifies endpoint is serving the correct version. AI Gateway configuration is managed declaratively by the bundle YAML. |

> **SDK install convention**: The deployment notebook includes `%pip install --upgrade databricks-sdk mlflow` + `restartPython()` as its first code cell to ensure the latest SDK version. This is required for any notebook that imports `databricks.sdk`.

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

## Testing

The test suite uses **pytest** and is discoverable by the Databricks workspace **Testing sidebar**. All tests mock external dependencies (MLflow, Databricks SDK, Epic FHIR API) — no real API calls or secrets required.

### Test Files

| File | Tests | Coverage |
| --- | --- | --- |
| `test_auth.py` | EpicApiAuth | JWT generation, token exchange, key loading |
| `test_endpoint.py` | EpicApiRequest | FHIR API client, URL construction, error handling |
| `test_epic_fhir_pyfunc.py` | EpicFhirPyfuncModel | Model init, predict(), NaN handling, error paths |
| `test_payloads.py` | FHIR payloads | Payload construction, JSON validity |
| `test_registration_notebook.py` | Registration workflow | Payload schema, conda env completeness, model template syntax, challenger alias, exit payload |
| `test_evaluation_notebook.py` | Evaluation workflow | Payload generation, JSON serialization validation, metric computation, validation gate assertions |
| `test_approval_notebook.py` | Approval workflow | Tag key convention (`approval_check`), approved/rejected/missing paths, case insensitivity, error messages |
| `test_deployment_notebook.py` | Deployment workflow | Alias rotation, env_vars preservation, ServedEntityInput construction, custom tags parsing, verification logic, SDK keyword-arg call pattern |

### Running Tests

```bash
# From the bundle root directory
cd epic_on_fhir

# Run all tests
python -B -m pytest tests/ -v

# Run only notebook workflow tests
python -B -m pytest tests/test_*_notebook.py -v

# Run from Databricks workspace Testing sidebar
# (auto-discovers test_*.py files)
```

### Shared Fixtures (`conftest.py`)

* **Fake secrets**: RSA key pair, client ID, kid (generated at import time, not real credentials)
* **Model fixtures**: `pyfunc_model`, `epic_auth`, `epic_api`
* **Mock fixtures**: `mock_mlflow_client`, `mock_workspace_client`, `mock_model_info`
* **Spark fixture**: Optional `spark` session (skipped when Spark unavailable)
* **Constants**: `FAKE_MODEL_NAME`, `FAKE_ENDPOINT_NAME`, `FAKE_CATALOG`, `FAKE_SCHEMA`, etc.

## SQL Endpoint Test Flow

The bundle includes a SQL query (`src/queries/Epic FHIR Endpoint Test Flow`) that exercises the full FHIR endpoint lifecycle using `ai_query()` from the SQL Editor:

1. **Search Patient** by external identifier (`GET Patient?identifier=EXTERNAL|Z6129`)
2. **Patient Clinical Summary** (`GET Patient/{id}/$summary`)
3. **Search Encounters** for the patient (`GET Encounter?patient=Patient/{id}`)
4. **Create Observation** — Heart Rate vital sign (`POST Observation`)
5. **Verify Observation** — Read-back (`GET Observation/{id}`)
6. **Create AllergyIntolerance** — Penicillin allergy (`POST AllergyIntolerance`)
7. **Verify AllergyIntolerance** — Read-back (`GET AllergyIntolerance/{id}`)

The query uses SQL session variables to chain FHIR resource IDs between steps, and a final summary statement reports pass/fail for each step.

This is useful for validating the serving endpoint works end-to-end without running notebooks or Python code.

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

# Run model registration job (registers model, sets "challenger" alias)
databricks bundle run -t dev epic_on_fhir_model_registration

# Set approval tag on the new model version (required for deployment job)
# Replace <model_name> and <version> with actual values from the registration output
databricks api post /api/2.0/mlflow/unity-catalog/model-versions/set-tag \
  --json '{"name": "<model_name>", "version": "<version>", "key": "approval_check", "value": "approved"}'

# Run deployment job (evaluates, approves, promotes to champion, updates endpoint)
databricks bundle run -t dev epic_on_fhir_model_deployment \
  --params "model_name=<model_name>,model_version=<version>"
```

> **Note**: Manual deployment requires understanding the chicken-and-egg dependency
> between the serving endpoint and model registration, plus setting the approval tag
> before the deployment job can proceed. The deploy script handles all of this
> automatically. See the deploy script section for details.

### 4. Access Resources

After deployment:
* **MLflow Experiment**: Available in workspace under `/Workspace/.experiments/`
* **Model Serving**: Endpoint accessible via REST API or `ai_query()` from SQL
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

Creates all bundle resources: schema, experiment, registered model, volume, app, jobs, and serving endpoint. On **first deployment**, the serving endpoint may fail because no model version exists yet — this is expected.

#### Phase 2: Run Model Registration Job

```
databricks bundle run -t <target> epic_on_fhir_model_registration
```

Runs the registration job, which executes the `epic-on-fhir-requests-model` notebook on serverless compute:
1. Builds the `EpicFhirPyfuncModel` pyfunc
2. Logs and registers a new model version in Unity Catalog
3. Sets the "challenger" alias on the new version
4. Exits with model metadata JSON (`model_name`, `model_version`, `model_uri`, `model_id`)

The script captures the run output and extracts the model name and version for Phase 4.

#### Phase 3: Conditional Re-deploy

```
databricks bundle deploy -t <target>   # only if Phase 1 had partial failure
```

If Phase 1 failed partially (e.g., serving endpoint couldn't be created), Phase 3 re-deploys the bundle. Now that a model version exists from Phase 2, the serving endpoint creation succeeds.

#### Phase 4: Conditional Deployment Job

Only runs if Phase 1 had partial failure (first-time deployment). The script:
1. Auto-approves the model version by setting the `approval_check = approved` tag via the UC REST API
2. Runs the deployment job with `model_name` and `model_version` parameters

```
databricks api post /api/2.0/mlflow/unity-catalog/model-versions/set-tag ...
databricks bundle run -t <target> epic_on_fhir_model_deployment \
  --params "model_name=<name>,model_version=<version>"
```

The deployment job then:
1. **Evaluates** the model against the Epic FHIR sandbox (traced predictions, metrics)
2. **Checks approval** via the UC tag (passes because deploy.sh auto-approved)
3. **Deploys**: promotes challenger → champion, updates serving endpoint (preserving environment_vars), verifies endpoint version

**On subsequent runs**, Phase 1 fully succeeds (model version already exists), so Phases 3 and 4 are skipped. The deployment job auto-triggers on new model version creation.

### Flow Diagram

```
Phase 1: bundle deploy
    ├─ schema, experiment, registered model, volume, app, jobs  ✓
    └─ serving endpoint  ✓ (or ⚠ if no model version yet)
         │
Phase 2: bundle run epic_on_fhir_model_registration
    └─ register_model:
        ├─ Build pyfunc model
        ├─ Log and register to Unity Catalog
        ├─ Set "challenger" alias
        └─ Exit with model metadata (name, version)
         │
Phase 3: bundle deploy  (only if Phase 1 was partial)
    └─ serving endpoint  ✓ (model version now exists)
         │
Phase 4: set approval tag + bundle run epic_on_fhir_model_deployment  (only if Phase 1 was partial)
    ├─ evaluation:
    │   ├─ Load model by name/version
    │   ├─ Traced FHIR predictions (GET Patient, POST Observation, etc.)
    │   └─ Log metrics to UC model version page + experiment
    ├─ approval_check:
    │   └─ Instant check: approval_check = 'approved' (auto-repair on failure)
    └─ deployment:
        ├─ Promote challenger → champion (rotate prior)
        ├─ Update serving endpoint (preserve environment_vars)
        ├─ Verify endpoint serves correct version
        └─ AI Gateway config managed by bundle YAML
```

### Prerequisites

* Databricks CLI installed and authenticated for the target workspace
* Secret scope configured with Epic OAuth2 credentials (`client_id`, `private_key`, `kid`, `public_key`)
* Bundle validated: `databricks bundle validate -t <target>`

### Job Parameters

#### Registration Job (`epic_on_fhir_model_registration`)

| Parameter | Default Source | Description |
| --- | --- | --- |
| `secret_scope_name` | `var.secret_scope_name` | Secret scope for Epic OAuth2 credentials |
| `client_id_dbs_key` | `var.client_id_dbs_key` | Secret key name for Epic client ID |
| `algo` | `var.algo` | JWT encryption algorithm (RS384) |
| `token_url` | `var.token_url` | Epic OAuth2 token endpoint |
| `mlflow_experiment_name` | `resources.experiments...name` | MLflow experiment path |
| `pip_index_url` | `var.pip_index_url` | Package index URL (local dev only) |
| `registered_model_name` | `resources.schemas...catalog_name`.`schemas...name`.`registered_models...name` | Full 3-level UC model namespace |

#### Deployment Job (`epic_on_fhir_model_deployment`)

| Parameter | Default Source | Description |
| --- | --- | --- |
| `model_name` | *(required, no default)* | Full 3-level UC model name (e.g., `catalog.schema.model`) |
| `model_version` | *(required, no default)* | Model version number to deploy |
| `mlflow_experiment_name` | `resources.experiments...name` | MLflow experiment path |
| `catalog` | `resources.schemas...catalog_name` | Unity Catalog catalog name |
| `schema` | `resources.schemas...name` | Unity Catalog schema name |
| `endpoint_name` | `resources.model_serving_endpoints...name` | Serving endpoint name |
| `tags` | JSON from bundle variables | Deployment metadata tags |

### Package Dependencies

The serverless environment installs these packages (from Databricks' own package mirror — **not** the PyPI proxy):

* `mlflow>=3.0.0` — Model logging, registry, tracing, and deployment job integration
* `databricks-sdk>=0.20.0` — Serving endpoint management (update_config_and_wait)

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

### SQL Access via ai_query()

The endpoint can also be called from SQL using `ai_query()`:

```sql
SELECT ai_query(
  'epic_on_fhir_requests',
  request => named_struct(
    'http_method', 'get',
    'resource', 'Patient',
    'action', '<patient-fhir-id>',
    'data', CAST(NULL AS STRING)
  ),
  returnType => 'STRUCT<response_status_code:INT, response_time_seconds:DOUBLE, response_text:STRING>'
) AS resp
```

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
3. **Register Model**: Run registration job to register to Unity Catalog (sets "challenger" alias)
4. **Approve Model**: Click "Approve" on the UC model version page (sets `approval_check = approved` tag), or set the tag via CLI/API
5. **Deploy to Serving**: Deployment job auto-triggers — evaluates, auto-repair waits for approval, promotes to "champion", updates endpoint
6. **Validate via SQL**: Run the `Epic FHIR Endpoint Test Flow` query to verify end-to-end
7. **Production Deployment**: Use production credentials (`client_id_prod`)

## Monitoring & Observability

* **Model Serving Metrics**: Request latency, throughput, error rates
* **MLflow Tracking**: Model performance, experiment comparisons
* **MLflow Tracing**: Traced predictions during evaluation for debugging
* **UC Model Version Metrics**: Evaluation metrics logged directly to model version page
* **AI Gateway Inference Tables**: Request/response payload logging for audit (configured in serving YAML)
* **OpenTelemetry**: Traces, logs, and metrics persisted to Unity Catalog Delta tables
* **Unity Catalog Lineage**: Data flow from Epic to downstream tables
* **Databricks SQL**: Query FHIR data for analytics using `ai_query()`

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
* If environment_vars are missing after an endpoint update, check that the deployment notebook is preserving them from the current served entity config

### Deploy Script Failures

* **Phase 1 partial failure**: Expected on first deploy (serving endpoint needs a model version). Phases 3 and 4 will handle it.
* **Phase 2 failure**: Check notebook cell output in the job run. Common causes: secret scope not configured, Epic sandbox unreachable, MLflow experiment permissions.
* **Phase 4 failure (metadata extraction)**: If the script cannot extract model metadata from the registration run, it prints manual commands. Run them to complete initial setup.
* **Phase 4 failure (deployment job)**: Check the individual task outputs — `evaluation` (FHIR sandbox connectivity), `approval_check` (UC tag missing), `deployment` (endpoint update API errors).
* **Package install timeout**: Do **not** add `--extra-index-url` to serverless dependencies. The proxy is unreachable from serverless compute.

### Deployment Job Issues

* **Evaluation task fails**: Check FHIR sandbox connectivity and model predictions. Metrics are logged to the UC model version page for debugging.
* **Approval task fails (expected)**: This is the normal human-in-the-loop gate. Click "Approve" on the UC model version page — the system sets the `approval_check` tag and **auto-repairs** the job run, re-running the approval task automatically. No manual re-run needed.
* **Approval task fails (rejected)**: If the tag is explicitly set to `rejected`, the task raises `ValueError` with instructions. Update the tag to `approved` and re-run the deployment job.
* **Deployment task fails (endpoint update)**: Check that the endpoint exists and the model version is valid. The task uses `update_config_and_wait()` with keyword args and preserves `environment_vars` — check for SDK version issues (`%pip install --upgrade databricks-sdk`).
* **Deployment task fails (env_vars lost)**: The deployment notebook reads `environment_vars` from the current served entity and carries them forward. If secrets are missing, redeploy the bundle (the serving YAML defines the env vars).

### Test Failures

* **`test_epic_fhir_pyfunc.py` import error**: This file imports `mlflow` — ensure mlflow is installed in the test environment.
* **Notebook workflow tests**: These tests (`test_*_notebook.py`) are self-contained with mocks and should pass without any external dependencies beyond `pytest` and `cryptography`.

## Archived Notebooks

The `src/_archive/` directory contains deprecated notebooks kept as reference:

* **`update-serving-endpoint-config`**: Previously used to programmatically update the serving endpoint configuration (workload size, scale-to-zero, AI Gateway). Now fully superseded by the deployment notebook (`src/deployment`) for version updates and the bundle YAML (`resources/epic_on_fhir_requests.serving.yml`) for AI Gateway configuration.

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
