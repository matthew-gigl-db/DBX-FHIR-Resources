import logging
from databricks.bundles.core import (
    Bundle,
    Resources,
    load_resources_from_current_package_module,
)
from .dynamic_deployment import DynamicResources

logger = logging.getLogger(__name__)


def load_resources(bundle: Bundle) -> Resources:
    """
    'load_resources' function is referenced in databricks.yml and
    is responsible for loading bundle resources defined in Python code.
    This function is called by Databricks CLI during bundle deployment.
    After deployment, this function is not used.
    
    This implementation:
    1. Loads static resources from YAML files in the resources folder
    2. Attempts dynamic deployment if authentication is available
    3. Merges dynamic resources into the base resources
    """
    
    # First, load all static resources from YAML files in the resources folder
    logger.info("Loading base resources from YAML files...")
    base_resources = load_resources_from_current_package_module()
    
    # Attempt dynamic deployment with graceful fallback
    try:
        logger.info("Attempting dynamic deployment...")
        deployer = DynamicResources(bundle)
        
        # Deploy secret scope if missing
        deployer.deploy_secret_scope_if_missing()
        
        # Deploy app if all prerequisites are met
        # Uses the bundle variable redox_binary_filename for the binary filename
        deployer.deploy_app_if_ready()
        
        # Get the dynamically added resources
        dynamic_resources = deployer.get_resources()
        
        # Merge dynamic resources into base resources
        if hasattr(dynamic_resources, 'secret_scopes') and dynamic_resources.secret_scopes:
            if not hasattr(base_resources, 'secret_scopes'):
                base_resources.secret_scopes = {}
            base_resources.secret_scopes.update(dynamic_resources.secret_scopes)
            logger.info("Merged dynamic secret scopes into base resources")
        
        if hasattr(dynamic_resources, 'apps') and dynamic_resources.apps:
            if not hasattr(base_resources, 'apps'):
                base_resources.apps = {}
            base_resources.apps.update(dynamic_resources.apps)
            logger.info("Merged dynamic apps into base resources")
        
        logger.info("Dynamic deployment completed successfully")
        
    except ValueError as e:
        # Authentication failed - this is expected during bundle deployment
        logger.warning(
            "Dynamic deployment skipped due to authentication: %s. "
            "This is normal during 'databricks bundle deploy' from CLI. "
            "To enable dynamic deployment, ensure ~/.databrickscfg is configured "
            "or run a post-deployment setup job.",
            str(e)
        )
    except Exception as e:
        # Other errors - log but don't fail the deployment
        logger.warning(
            "Dynamic deployment failed: %s. Proceeding with static resources only.",
            str(e),
            exc_info=True
        )
    
    return base_resources
