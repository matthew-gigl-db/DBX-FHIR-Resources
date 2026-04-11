#!/bin/bash
# deploy.sh — Single-command deployment for the Epic on FHIR asset bundle.
#
# Handles the chicken-and-egg dependency between the model serving endpoint
# (which requires a model version) and the model registration notebook
# (which requires the registered model resource to exist).
#
# Phases:
#   1. Deploy bundle infrastructure (schema, experiment, registered model, volume).
#      The serving endpoint may fail on first deploy if no model version exists.
#   2. Run the model registration job to create v1 and promote to champion.
#      The update_endpoint_config task exits gracefully if the endpoint doesn't exist.
#   3. Re-deploy the bundle so the serving endpoint picks up the model version.
#   4. Re-run the job (updateAIGatewayOnly=true) to apply AI Gateway/telemetry/tags
#      to the newly created endpoint.
#
# Subsequent runs are idempotent — if the serving endpoint already exists and
# has a valid model version, phases 3 and 4 are skipped.
#
# Usage:
#   ./deploy.sh [target]
#
# Arguments:
#   target   Bundle target (default: dev). One of: dev, sandbox_prod,
#            hls_fde_sandbox_prod, prod
#
# Prerequisites:
#   - Databricks CLI installed and authenticated
#   - Secret scope configured with Epic OAuth2 credentials
#   - Bundle validated: databricks bundle validate -t <target>
#
# Examples:
#   ./deploy.sh                     # Deploy to dev (default)
#   ./deploy.sh sandbox_prod        # Deploy to sandbox production
#   ./deploy.sh hls_fde_sandbox_prod # Deploy to HLS FDE sandbox

set -euo pipefail

TARGET="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOB_KEY="epic_on_fhir_model_registration"

echo "============================================="
echo "Epic on FHIR Bundle Deployment"
echo "Target: ${TARGET}"
echo "Time:   $(date -u +\"%Y-%m-%dT%H:%M:%SZ\")"
echo "============================================="
echo ""

# Change to the bundle root directory
cd "${SCRIPT_DIR}"

# --------------------------------------------------------------------------
# Phase 1: Deploy bundle infrastructure
# --------------------------------------------------------------------------
echo "[Phase 1/4] Deploying bundle infrastructure..."
echo "  This creates: schema, experiment, registered model, volume, app, job."
echo "  The serving endpoint may fail if no model version exists yet."
echo ""

if databricks bundle deploy -t "${TARGET}"; then
    echo ""
    echo "  ✓ Full deployment succeeded."
    PHASE1_FULL_SUCCESS=true
else
    echo ""
    echo "  ⚠ Partial deployment (serving endpoint may have failed — expected on first run)."
    PHASE1_FULL_SUCCESS=false
fi
echo ""

# --------------------------------------------------------------------------
# Phase 2: Run model registration job
# --------------------------------------------------------------------------
echo "[Phase 2/4] Running model registration job..."
echo "  Job: ${JOB_KEY}"
echo "  This registers a new model version, validates, and promotes to champion."
echo "  The endpoint config update task will be skipped if the endpoint doesn't exist yet."
echo ""

databricks bundle run -t "${TARGET}" "${JOB_KEY}"

echo ""
echo "  ✓ Model registration job completed."
echo ""

# --------------------------------------------------------------------------
# Phase 3: Re-deploy (only if Phase 1 had partial failure)
# --------------------------------------------------------------------------
if [ "${PHASE1_FULL_SUCCESS}" = true ]; then
    echo "[Phase 3/4] Skipping re-deploy (Phase 1 fully succeeded)."
else
    echo "[Phase 3/4] Re-deploying bundle..."
    echo "  The serving endpoint should succeed now that a model version exists."
    echo ""

    databricks bundle deploy -t "${TARGET}"

    echo ""
    echo "  ✓ Re-deployment succeeded."
fi
echo ""

# --------------------------------------------------------------------------
# Phase 4: Update endpoint config (only if Phase 1 had partial failure)
# --------------------------------------------------------------------------
# On first deploy, Phase 2's update_endpoint_config task skipped because the
# endpoint didn't exist. Now that Phase 3 created it, re-run the job with
# updateAIGatewayOnly=true to apply AI Gateway, telemetry, and tags.
if [ "${PHASE1_FULL_SUCCESS}" = true ]; then
    echo "[Phase 4/4] Skipping endpoint config update (Phase 2 already applied it)."
else
    echo "[Phase 4/4] Updating endpoint configuration..."
    echo "  Re-running job with updateAIGatewayOnly=true to apply AI Gateway, telemetry, and tags."
    echo ""

    databricks bundle run -t "${TARGET}" "${JOB_KEY}" --params updateAIGatewayOnly=true

    echo ""
    echo "  ✓ Endpoint configuration updated."
fi

echo ""
echo "============================================="
echo "Deployment complete for target: ${TARGET}"
echo "============================================="
