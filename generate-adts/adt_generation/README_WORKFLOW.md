# ADT Generator Workflow Setup

This project uses [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/index.html) to deploy and manage the ADT message generator as a workflow job.

## 📁 Project Structure

```
adt_generation/
├── databricks.yml              # Bundle configuration with variables
├── resources/
│   └── adt_generator_job.yml  # Job definition
├── src/
│   └── adt-generators         # Main notebook
└── README_WORKFLOW.md          # This file
```

## 🔧 Configuration Variables

All configurable parameters are defined in `databricks.yml` under the `variables` section:

### Patient Generation
- **num_patients**: Number of synthetic patients (default: `327`)
- **events_per_patient_max**: Max ADT events per patient (default: `8`)

### HL7 Configuration
- **hl7_version**: HL7 version (default: `2.5`)
- **sending_app**: Sending application ID (default: `DATABRICKS_SIM`)
- **sending_facility**: Sending facility ID (default: `DBX_FAC`)
- **receiving_app**: Receiving application ID (default: `DOWNSTREAM_SYS`)
- **receiving_facility**: Receiving facility ID (default: `DST_FAC`)

### Storage Configuration
- **catalog_use**: Unity Catalog name (default: `main`)
- **schema_use**: Schema name (default: `healthcare`)
- **volume_name**: Volume name (default: `hl7_synthetic`)
- **relative_path**: Path within volume (default: `adt_fake`)

## 🚀 Deployment Commands

### Prerequisites
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/databricks-cli.html) installed and configured
- Appropriate permissions in the target workspace

### Deploy to Development
```bash
cd /Workspace/Users/matthew.giglia@databricks.com/synthea-on-fhir/generate-adts/adt_generation
databricks bundle deploy --target dev
```

### Deploy to Production
```bash
databricks bundle deploy --target prod
```

### Validate Configuration (without deploying)
```bash
databricks bundle validate
```

## ▶️ Running the Job

### Run with Default Parameters
```bash
databricks bundle run adt_generator_job --target dev
```

### Override Parameters at Runtime
```bash
databricks bundle run adt_generator_job --target dev \
  --param num_patients=500 \
  --param catalog_use=himss \
  --param volume_name=landing
```

### Run via Databricks UI
1. Go to **Workflows** in the Databricks UI
2. Find "ADT Message Generator - dev" (or prod)
3. Click **Run now**
4. Optionally override parameters in the run dialog

## 🔄 Updating Variables

### Method 1: Update databricks.yml (Persistent)
Edit the `variables` section in `databricks.yml` and redeploy:
```bash
databricks bundle deploy --target dev
```

### Method 2: Environment-Specific Overrides
Add variable overrides in the target configuration:
```yaml
targets:
  dev:
    variables:
      num_patients: "100"  # Dev uses fewer patients
      catalog_use: "dev_catalog"
```

### Method 3: Runtime Override (One-time)
Use `--param` flag when running (see above)

## 📊 Monitoring

- **Job Runs**: Navigate to Workflows → ADT Message Generator → Runs
- **Email Notifications**: Configured to send to matthew.giglia@databricks.com on success/failure
- **Logs**: Available in the run details page

## 🎯 Job Configuration Details

The job (`resources/adt_generator_job.yml`) includes:
- **Compute**: Serverless cluster with 2 workers (i3.xlarge)
- **Libraries**: Faker (auto-installed)
- **Timeout**: 2 hours (job), 1 hour (task)
- **Retries**: Up to 2 retries with 1-minute intervals
- **Concurrency**: Max 1 concurrent run

## 🔐 Permissions

The job runs as:
- **Dev**: Current user (development mode)
- **Prod**: matthew.giglia@databricks.com (specified in `run_as`)

## 📝 Scheduling (Optional)

To enable scheduled runs, uncomment the schedule section in `resources/adt_generator_job.yml`:
```yaml
schedule:
  quartz_cron_expression: "0 0 2 * * ?" # Daily at 2 AM
  timezone_id: "America/New_York"
  pause_status: "UNPAUSED"
```

Then redeploy:
```bash
databricks bundle deploy --target prod
```

## 🧪 Testing

### Test in Interactive Mode (Current Workflow)
1. Open the `adt-generators` notebook
2. Modify widget values in the UI
3. Run cells interactively

### Test as Job (Recommended before production)
```bash
# Deploy and run with test parameters
databricks bundle run adt_generator_job --target dev \
  --param num_patients=50 \
  --param relative_path=adt_test
```

## 📚 Additional Resources

- [Databricks Asset Bundles Documentation](https://docs.databricks.com/en/dev-tools/bundles/index.html)
- [Databricks CLI Reference](https://docs.databricks.com/en/dev-tools/cli/bundle-commands.html)
- [YAML Variables Guide](https://docs.databricks.com/en/dev-tools/bundles/settings.html#use-variables-in-a-bundle)

## 🐛 Troubleshooting

### Issue: Job fails with "Volume not found"
**Solution**: Ensure the Unity Catalog volume exists:
```sql
CREATE VOLUME IF NOT EXISTS ${catalog_use}.${schema_use}.${volume_name};
```

### Issue: Variables not being passed correctly
**Solution**: Check that variable syntax uses `${var.variable_name}` in the job YAML

### Issue: Bundle validation fails
**Solution**: Run `databricks bundle validate` for detailed error messages
