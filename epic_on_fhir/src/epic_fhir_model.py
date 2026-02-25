"""Epic on FHIR MLflow pyfunc model - Models from Code definition"""
import mlflow
from mlflow.models import set_model
from smart_on_fhir.epic_fhir_pyfunc import EpicFhirPyfuncModel

model = EpicFhirPyfuncModel(
	secret_scope_name="epic_on_fhir_oauth_keys",
	client_id_dbs_key="client_id",
	token_url="https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
	algo="RS384",
)

set_model(model)
