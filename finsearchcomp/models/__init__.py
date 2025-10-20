import importlib
import os

from logger import get_logger

logger = get_logger(__name__)


def load_model(model_name, **kwargs):
    model_file = f"{model_name.replace('-', '_')}.py"
    model_path = os.path.join(os.path.dirname(__file__), model_file)
    
    if not os.path.exists(model_path):
        logger.error("Requested model does not exist: %s", model_name)
        raise ValueError(f"Model {model_name} not found")
    
    module = importlib.import_module(f"models.{model_name.replace('-', '_')}")
    logger.debug("Loaded model module for %s", model_name)
    return module.load_model(model_name, **kwargs)

def chat(model_name):
    model_file = f"{model_name.replace('-', '_')}.py"
    model_path = os.path.join(os.path.dirname(__file__), model_file)
    
    if not os.path.exists(model_path):
        raise ValueError(f"Model {model_name} not found")
    
    module = importlib.import_module(f"models.{model_name.replace('-', '_')}")
    return module.load_model(model_name) 
