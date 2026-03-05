# FHIR Zerobus Infrastructure

Infrastructure provisioning bundle for the FHIR Zerobus ingestion application, managing Unity Catalog resources, service principals, and external storage locations.

## Overview

This asset bundle deploys the foundational infrastructure required by the FHIR Zerobus application (`fhir_zerobus`). It handles Unity Catalog schema creation, volume provisioning, external locations, and service principal setup.

**Deployment Order**: Deploy this infrastructure bundle **before** deploying the `fhir_zerobus` application bundle.

## Purpose

Separating infrastructure from application deployment provides:

* **Clean Resource Management**: Infrastructure persists across app deployments
* **Permission Isolation**: Infrastructure managed by admins, apps by developers
* **Reusability**: Multiple apps can share the same infrastructure
* **Terraform/IaC Compatibility**: Infrastructure can be managed separately

## Bundle Resources

This bundle manages:

* Unity Catalog schemas for FHIR data storage
* Unity Catalog volumes for application data and artifacts
* External locations for S3/ADLS/GCS integration (if needed)
* Service principals with appropriate permissions
* IAM roles and policies (cloud-specific)

## Resource Types

### Unity Catalog Schemas
Tables for storing:
* Raw FHIR bundles ingested via Zerobus
* Processed FHIR resources (Patient, Observation, etc.)
* Application metadata and logs

### Unity Catalog Volumes
Storage for:
* Application configuration files
* DLT pipeline checkpoints
* Temporary processing data
* Archived FHIR bundles

### External Locations
External storage connectors (if using external volumes):
* S3 buckets (AWS)
* Azure Data Lake Storage (Azure)
* Google Cloud Storage (GCP)

### Service Principals
Identity and access:
* Zerobus ingestion service principal
* DLT pipeline execution identity
* Application deployment identity

## Deployment Targets

| Target | Workspace | Catalog | Purpose |
|--------|-----------|---------|---------|
| **dev** | fe-sandbox-himss2026 | himss | Development |
| **prod** | fe-sandbox-himss2026 | himss | Production |

## Getting Started

### Prerequisites

* Databricks workspace admin privileges
* Unity Catalog admin permissions
* Cloud IAM permissions (for external locations)
* Databricks CLI authenticated as admin

### 1. Review Configuration

Edit `databricks.yml` to verify/update:
* Workspace host
* Catalog and schema names
* Service principal UUIDs
* External storage paths (if applicable)

### 2. Deploy Infrastructure

```bash
# Validate infrastructure bundle
databricks bundle validate -t dev

# Deploy to development
databricks bundle deploy -t dev

# Deploy to production (when ready)
databricks bundle deploy -t prod
```

### 3. Verify Deployment

```bash
# Check schema exists
databricks unity-catalog schemas get <catalog>.<schema>

# Check volumes
databricks unity-catalog volumes list --catalog <catalog> --schema <schema>

# Check service principals
databricks service-principals list --filter "displayName eq '<name>'"
```

### 4. Deploy Application

After infrastructure is deployed, proceed with deploying the `fhir_zerobus` application bundle.

## Infrastructure Components

### Required Resources

1. **Unity Catalog Schema** (`himss.redox` or similar)
   - Owner: Infrastructure admin or service principal
   - Grants: SELECT, MODIFY to application service principal

2. **Volumes** (examples)
   - `app_config`: Application configuration files
   - `checkpoints`: DLT checkpoints
   - `archive`: Historical FHIR bundles

3. **Service Principal for Zerobus**
   - Purpose: Authenticate Zerobus SDK connections
   - Permissions: USAGE on catalog, MODIFY on schema, SELECT/INSERT on tables

4. **Service Principal for DLT Pipeline**
   - Purpose: Run DLT pipeline transformations
   - Permissions: USAGE on catalog, MODIFY on schema, READ/WRITE on volumes

## Permission Model

```
Unity Catalog: himss
└── Schema: redox
    ├── Permissions:
    │   ├── Admin Group: ALL PRIVILEGES
    │   ├── Zerobus SP: USAGE, SELECT, MODIFY
    │   └── DLT SP: USAGE, SELECT, MODIFY
    ├── Tables:
    │   └── fhir_bundle_zerobus (created by app)
    └── Volumes:
        ├── app_config (managed)
        └── checkpoints (managed)
```

## External Storage Setup (Optional)

### AWS S3

1. Create S3 bucket:
   ```bash
   aws s3 mb s3://fhir-zerobus-storage
   ```

2. Create IAM role with trust policy for Databricks

3. Update `databricks.yml` with external location path

4. Deploy bundle to create external location in Unity Catalog

### Azure ADLS Gen2

1. Create storage account and container

2. Create Azure service principal with Storage Blob Data Contributor role

3. Update `databricks.yml` with ADLS path

4. Deploy bundle

### GCP Cloud Storage

1. Create GCS bucket

2. Create service account with Storage Object Admin role

3. Update `databricks.yml` with GCS path

4. Deploy bundle

## Maintenance & Operations

### Adding New Schemas

1. Add schema definition to `resources/` directory
2. Update `databricks.yml` includes
3. Deploy with `databricks bundle deploy -t <target>`

### Modifying Permissions

1. Update permission grants in resource YAML files
2. Redeploy bundle
3. Verify with `databricks grants get <resource-type> <resource-name>`

### Managing Service Principals

```bash
# Create new service principal
databricks service-principals create --display-name "fhir-zerobus-sp"

# Generate OAuth secret
databricks service-principals create-token --service-principal-id <sp-id>

# Grant permissions (via bundle or CLI)
databricks grants update <resource-type> <resource-name> \
  --service-principal <sp-id> --privilege <privilege>
```

## Disaster Recovery

### Backup Strategy

* Unity Catalog schemas and tables: Delta table time travel (7-30 days)
* Volumes: Regular snapshots via cloud provider
* Infrastructure definitions: Version controlled in Git

### Recovery Procedure

1. Restore infrastructure bundle from Git
2. Deploy with `databricks bundle deploy -t <target>`
3. Restore data from Delta time travel or cloud snapshots
4. Redeploy application bundle

## Troubleshooting

### Permission Denied Errors
* Verify service principal has correct grants
* Check Unity Catalog hierarchy (catalog → schema → table/volume)
* Review IAM roles for external storage

### Resource Already Exists
* Check if resource was created manually
* Import existing resource into bundle state
* Or rename resource in bundle configuration

### External Location Issues
* Verify cloud storage credentials
* Check network connectivity (VPC, firewall rules)
* Confirm IAM role trust policies

## Documentation & Resources

* [Unity Catalog Administration](https://docs.databricks.com/data-governance/unity-catalog/)
* [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/)
* [Service Principals](https://docs.databricks.com/administration-guide/users-groups/service-principals.html)
* [External Locations](https://docs.databricks.com/data-governance/unity-catalog/external-locations.html)

## Support

* **Project**: Redox Zerobus Infrastructure
* **Business Unit**: Healthcare and Life Sciences
* **Primary Developer**: matthew.giglia@databricks.com
* **Deployment Type**: Infrastructure (prerequisite for fhir_zerobus app)
