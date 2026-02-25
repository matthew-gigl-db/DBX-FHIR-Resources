# Notebook kernel selection

If **Python (epic_on_fhir)** does not appear in the kernel list:

1. Click **Select Kernel** (top-right of notebook)
2. Choose **"Python Environments"**
3. Pick the env that shows `epic_on_fhir` or `.venv` in the path
4. Or choose **"Enter Interpreter Path..."** and paste:
   ```
   /Users/matthew.giglia/Documents/mkgs_databricks_demos/synthea-on-fhir/epic_on_fhir/.venv/bin/python
   ```

Alternate method:
- `Cmd+Shift+P` → **Python: Select Interpreter**
- Choose the `epic_on_fhir` / `.venv` interpreter
- Then open the notebook; it should use that kernel
