from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.logger import get_logger
from app.schema import TaskOutput


class BaseFlow(ABC):
    """Base class for all flows in the system."""
    
    def __init__(self, name: str):
        """
        Initialize a flow.
        
        Args:
            name (str): Flow name
        """
        self.name = name
        self.logger = get_logger(f"flow.{name}")
    
    @abstractmethod
    def _run(self, **kwargs) -> TaskOutput:
        """
        Execute the flow with the given arguments.
        
        Args:
            **kwargs: Flow-specific arguments
            
        Returns:
            TaskOutput: Result of the flow execution
        """
        pass
    
    def run(self, **kwargs) -> TaskOutput:
        """
        Run the flow with error handling.
        
        Args:
            **kwargs: Flow-specific arguments
            
        Returns:
            TaskOutput: Result of the flow execution
        """
        try:
            self.logger.info(f"Running flow '{self.name}'")
            result = self._run(**kwargs)
            self.logger.info(f"Flow '{self.name}' completed successfully")
            return result
        except Exception as e:
            error_msg = f"Error running flow '{self.name}': {str(e)}"
            self.logger.error(error_msg)
            
            # Create error output
            return TaskOutput(
                success=False,
                error=error_msg
            )
