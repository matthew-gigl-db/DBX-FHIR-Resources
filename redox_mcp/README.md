# Redox MCP Server

Databricks Application hosting the Redox Model Context Protocol (MCP) server for integration with AI agent frameworks and healthcare data workflows.

## Overview

This asset bundle deploys a Databricks App that hosts the Redox MCP server, enabling AI agents (like Claude Desktop, GitHub Copilot, or custom LLM applications) to access Redox's FHIR data models and healthcare data definitions as contextual knowledge.

### What is MCP?

**Model Context Protocol (MCP)** is an open protocol that standardizes how applications provide context to Large Language Models (LLMs). The Redox MCP server exposes Redox's healthcare data models, FHIR resource definitions, and data transformation specifications in a way that AI agents can understand and use.

### What is Redox?

**Redox** is a healthcare data platform that connects health systems, EHRs, and digital health applications. The Redox MCP provides access to their standardized healthcare data models and transformation rules.

### Key Features

* **Redox Data Models**: Access to Redox's healthcare data specifications
* **FHIR Resource Definitions**: Structured FHIR R4 resource schemas
* **AI Agent Integration**: Compatible with MCP-enabled AI tools
* **OAuth2 Authentication**: Secure access to Redox APIs
* **Databricks Apps Hosting**: Built-in authentication and scaling
* **Healthcare Context**: Provides domain knowledge to LLMs

## Architecture

```
AI Agent (Claude, Copilot, etc.)
    ↓ MCP Protocol
Redox MCP Server (Databricks App)
    ↓ OAuth2
Redox API (data-models.prod.redoxengine.com)
    → FHIR Data Models
    → Transformation Specs
    → Healthcare Schemas
```

## Bundle Resources

### 1. Databricks App
**Resource**: `redox_mcp_serving.app.yml`  
**Name**: `redox_mcp_serving` (varies by target)  
**Purpose**: Host the Redox MCP server  
**Access**: Via Databricks Apps Gateway (authenticated)

### 2. Secret Scope
**Resource**: `redox_oauth.secret_scope.yml`  
**Name**: `redox_oauth_keys`  
**Purpose**: Store Redox API OAuth2 credentials  
**Required Secrets**:
* `client_id`: Redox application client ID
* `client_secret`: Redox application client secret
* `token_url`: Redox OAuth2 token endpoint

### 3. Unity Catalog Schema
**Resource**: `redox.schema.yml`  
**Name**: `redox` (within target catalog)  
**Purpose**: Schema for storing Redox-sourced FHIR data and metadata

### 4. Binary Volume
**Resource**: `bin.volume.yml`  
**Name**: `bin`  
**Purpose**: Store the Redox MCP server binary (`redox-mcp-linux-x64`)

## Prerequisites

### Access Requirements

⚠️ **Closed Beta Access Required**

This bundle requires access to the Redox MCP closed beta program. You must:

1. Be enrolled in the Redox MCP closed beta
2. Have permissions to download from:
   ```
   https://data-models.prod.redoxengine.com/downloads/redox-mcp/linux-x64/redox-mcp.bin
   ```
3. Have valid Redox API credentials (client ID and secret)

Contact Redox to request beta access.

### Databricks Requirements

* Databricks workspace with Databricks Apps enabled
* Unity Catalog with appropriate permissions
* Ability to create secret scopes
* Databricks CLI authenticated

## Getting Started

### 1. Download Redox MCP Binary

```bash
# Download the binary (requires beta access)
curl -o redox-mcp-linux-x64 \
  https://data-models.prod.redoxengine.com/downloads/redox-mcp/linux-x64/redox-mcp.bin

# Make executable
chmod +x redox-mcp-linux-x64
```

### 2. Upload Binary to Volume

```bash
# Create volume path (if needed)
databricks fs mkdirs dbfs:/Volumes/<catalog>/redox/bin/

# Upload binary
databricks fs cp ./redox-mcp-linux-x64 \
  dbfs:/Volumes/<catalog>/redox/bin/redox-mcp-linux-x64
```

### 3. Configure Secrets

```bash
# Create secret scope
databricks secrets create-scope redox_oauth_keys

# Add Redox credentials
databricks secrets put-secret --scope redox_oauth_keys --key client_id
# Paste your Redox client ID when prompted

databricks secrets put-secret --scope redox_oauth_keys --key client_secret
# Paste your Redox client secret when prompted
```

### 4. Update Configuration

Edit `databricks.yml` variables as needed:
* `catalog`: Unity Catalog name (e.g., `mkgs_dev`, `mkgs`)
* `schema`: Schema name (default: `redox`)
* `token_url`: Redox token endpoint (default set for R4 FHIR sandbox)
* `redox_binary_filename`: Binary filename (default: `redox-mcp-linux-x64`)
* `run_as_user`: User or service principal

### 5. Deploy Bundle

```bash
# Validate configuration
databricks bundle validate -t dev

# Deploy to development
databricks bundle deploy -t dev

# For production deployment
databricks bundle deploy -t prod
```

### 6. Access the MCP Server

After deployment, the Databricks App will be available at:
```
https://<workspace-url>/apps/<app-id>
```

The MCP server endpoint will be:
```
https://<workspace-url>/apps/<app-id>/mcp
```

## Deployment Targets

| Target | Workspace | Catalog | Schema | Purpose |
|--------|-----------|---------|--------|---------|
| **dev** | fe-vm-mkgs-databricks-demos | mkgs_dev | redox | Development |
| **prod** | fe-vm-mkgs-databricks-demos | mkgs | redox | Production |
| **free_edition** | dbc-e5684c0a-20fa | mkgs | redox | Free tier |
| **himss2026** | fe-sandbox-himss2026 | himss | redox | HIMSS demo |

## Using with AI Agents

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "redox": {
      "url": "https://<workspace-url>/apps/<app-id>/mcp",
      "headers": {
        "Authorization": "Bearer <databricks-token>"
      }
    }
  }
}
```

### Custom MCP Client

```python
from anthropic import Anthropic
from mcp import ClientSession

# Create MCP client
session = ClientSession(
    url="https://<workspace-url>/apps/<app-id>/mcp",
    headers={"Authorization": f"Bearer {databricks_token}"}
)

# Use with Anthropic Claude
client = Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": "What are the fields in a Redox FHIR Patient resource?"
    }],
    mcp_context=session
)
```

## MCP Capabilities

The Redox MCP server provides:

* **Data Model Schemas**: Structured definitions of Redox FHIR resources
* **Transformation Rules**: How data is mapped between formats
* **Validation Specs**: Required fields, data types, value constraints
* **Code Systems**: Healthcare terminologies (SNOMED, LOINC, CPT, etc.)
* **Example Payloads**: Sample FHIR resources for reference

## Monitoring & Maintenance

### Check App Status

```bash
databricks apps describe <app-name>
```

### View Logs

Access logs via the Databricks Apps UI or CLI:
```bash
databricks apps logs <app-name>
```

### Update Binary

When a new Redox MCP version is released:
1. Download new binary
2. Upload to volume (overwriting old version)
3. Restart the Databricks App

## Troubleshooting

### Binary Download Fails
* Verify you have Redox MCP beta access
* Check network connectivity
* Confirm download URL hasn't changed

### Authentication Errors
* Verify secret scope name matches `databricks.yml`
* Check client_id and client_secret are correct
* Ensure token_url is appropriate for your environment

### App Won't Start
* Check binary has execute permissions
* Verify volume path is accessible
* Review app logs for specific errors

## Documentation & Resources

* [Model Context Protocol Specification](https://modelcontextprotocol.io/)
* [Redox API Documentation](https://developer.redoxengine.com/)
* [Databricks Apps Documentation](https://docs.databricks.com/en/dev-tools/databricks-apps/)
* [Anthropic MCP Guide](https://www.anthropic.com/news/model-context-protocol)

## Support

* **Project**: Open Epic Smart on FHIR
* **Business Unit**: Healthcare and Life Sciences
* **Primary Developer**: matthew.giglia@databricks.com
* **Target Audience**: Healthcare Providers and Health Plans
