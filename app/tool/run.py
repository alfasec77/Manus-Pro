"""
Run tool for executing various operations conveniently.
"""
from typing import Any, Dict, Optional, Union, List

from app.tool.base import BaseTool
from app.exceptions import ToolError
from app.tool.bash import BashTool
from app.tool.python_execute import PythonExecuteTool
from app.tool.file_saver import FileSaverTool


class RunTool(BaseTool):
    """General purpose tool for executing various operations."""
    
    def __init__(self):
        """Initialize the run tool."""
        super().__init__(
            name="run",
            description="Execute various operations such as commands, code, and file operations"
        )
        # Initialize sub-tools
        self.bash_tool = BashTool()
        self.python_tool = PythonExecuteTool()
        self.file_tool = FileSaverTool()
    
    def _run(self, 
             operation: str,
             **kwargs) -> Dict[str, Any]:
        """
        Run a specified operation.
        
        Args:
            operation (str): Type of operation to run
            **kwargs: Operation-specific arguments
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            # Delegate to appropriate tool based on operation
            if operation == "command" or operation == "bash":
                return self._run_command(**kwargs)
            elif operation == "python" or operation == "code":
                return self._run_python(**kwargs)
            elif operation == "file" or operation == "save":
                return self._run_file_operation(**kwargs)
            else:
                raise ToolError(f"Unknown operation: {operation}")
            
        except Exception as e:
            error_msg = f"Failed to run operation {operation}: {str(e)}"
            self.logger.error(error_msg)
            raise ToolError(error_msg)
    
    def _run_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Run a shell command.
        
        Args:
            command (str): Command to execute
            **kwargs: Additional arguments for BashTool
            
        Returns:
            Dict[str, Any]: Command execution results
        """
        return self.bash_tool.run(command=command, **kwargs)
    
    def _run_python(self, code: str, **kwargs) -> Dict[str, Any]:
        """
        Run Python code.
        
        Args:
            code (str): Python code to execute
            **kwargs: Additional arguments for PythonExecuteTool
            
        Returns:
            Dict[str, Any]: Python code execution results
        """
        return self.python_tool.run(code=code, **kwargs)
    
    def _run_file_operation(self, content: str, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Run a file operation (save content to file).
        
        Args:
            content (str): Content to save
            file_path (str): Path to save the file
            **kwargs: Additional arguments for FileSaverTool
            
        Returns:
            Dict[str, Any]: File operation results
        """
        return self.file_tool.run(content=content, file_path=file_path, **kwargs)


def run_operation(operation: str, **kwargs) -> Dict[str, Any]:
    """
    Run a specified operation using the RunTool.
    
    Args:
        operation (str): Type of operation to run (command, python, file)
        **kwargs: Operation-specific arguments
        
    Returns:
        Dict[str, Any]: Result of the operation
    """
    tool = RunTool()
    return tool.run(operation=operation, **kwargs)
