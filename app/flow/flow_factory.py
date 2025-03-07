from typing import Dict, Type, Any

from app.config import Config
from app.flow.base import BaseFlow
from app.flow.planning import PlanningFlow
from app.logger import get_logger

# Registry of available flows
FLOW_REGISTRY: Dict[str, Type[BaseFlow]] = {
    "planning": PlanningFlow,
    # Add more flows here as they are implemented
}

def create_flow(flow_name: str, config: Config) -> BaseFlow:
    """
    Create a flow instance by name.
    
    Args:
        flow_name (str): Name of the flow to create
        config (Config): Configuration object
        
    Returns:
        BaseFlow: Flow instance
        
    Raises:
        ValueError: If flow_name is not found in the registry
    """
    logger = get_logger("flow_factory")
    
    # Check if flow exists in registry
    flow_class = FLOW_REGISTRY.get(flow_name)
    if not flow_class:
        logger.error(f"Flow '{flow_name}' not found in registry")
        raise ValueError(f"Unknown flow: {flow_name}")
    
    # Create flow instance
    logger.debug(f"Creating flow '{flow_name}'")
    flow = flow_class()
    
    return flow
