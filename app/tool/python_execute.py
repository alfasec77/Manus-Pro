import os
import sys
import tempfile
import traceback
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, Optional, Union

from app.tool.base import BaseTool
from app.exceptions import ToolError
from app.tool.bash import BashTool


class PythonExecuteTool(BaseTool):
    """Tool for executing Python code."""
    
    def __init__(self):
        """Initialize the Python execution tool."""
        super().__init__(
            name="python_execute",
            description="Execute Python code and return the results"
        )
    
    def _run(self, 
             code: str, 
             use_subprocess: bool = False,
             capture_locals: bool = False,
             input_vars: Optional[Dict[str, Any]] = None,
             timeout: Optional[int] = 30) -> Dict[str, Any]:
        """
        Execute Python code and return the results.
        
        Args:
            code (str): Python code to execute
            use_subprocess (bool, optional): Run in a subprocess for isolation
            capture_locals (bool, optional): Capture local variables after execution
            input_vars (Dict[str, Any], optional): Variables to inject into the context
            timeout (int, optional): Timeout in seconds (only for subprocess)
            
        Returns:
            Dict[str, Any]: Execution results
        """
        if use_subprocess:
            return self._execute_in_subprocess(code, timeout)
        else:
            return self._execute_in_current_process(code, capture_locals, input_vars)
    
    def _execute_in_current_process(self, code: str, capture_locals: bool, input_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute Python code in the current process.
        
        Args:
            code (str): Python code to execute
            capture_locals (bool): Capture local variables after execution
            input_vars (Dict[str, Any], optional): Variables to inject into the context
            
        Returns:
            Dict[str, Any]: Execution results
        """
        # Create a dictionary for locals to capture variables
        local_vars = {}
        if input_vars:
            local_vars.update(input_vars)
        
        # Capture stdout and stderr
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()
        
        result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "locals": {},
            "exception": None
        }
        
        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exec(code, globals(), local_vars)
            
            result["success"] = True
            
            # Capture stdout and stderr
            result["stdout"] = stdout_buffer.getvalue()
            result["stderr"] = stderr_buffer.getvalue()
            
            # Capture local variables if requested
            if capture_locals:
                # Filter out internal variables (starting with underscore)
                result["locals"] = {k: v for k, v in local_vars.items() 
                                  if not k.startswith('_') and k != 'input_vars'}
            
            self.logger.debug("Python code executed successfully in current process")
            
        except Exception as e:
            result["success"] = False
            result["exception"] = {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            # Capture stdout and stderr (what was captured before the exception)
            result["stdout"] = stdout_buffer.getvalue()
            result["stderr"] = stderr_buffer.getvalue() + "\n" + traceback.format_exc()
            
            self.logger.warning(f"Error executing Python code: {type(e).__name__}: {str(e)}")
        
        return result
    
    def _execute_in_subprocess(self, code: str, timeout: Optional[int] = 30) -> Dict[str, Any]:
        """
        Execute Python code in a subprocess for isolation.
        
        Args:
            code (str): Python code to execute
            timeout (int, optional): Timeout in seconds
            
        Returns:
            Dict[str, Any]: Execution results
        """
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix=".py", mode='w', delete=False) as code_file:
            code_path = code_file.name
            code_file.write(code)
        
        try:
            # Use BashTool to execute the script
            bash_tool = BashTool()
            cmd_result = bash_tool.run(
                command=f"{sys.executable} {code_path}",
                timeout=timeout,
                capture_stderr=True
            )
            
            result = {
                "success": cmd_result["returncode"] == 0,
                "stdout": cmd_result["stdout"],
                "stderr": cmd_result["stderr"] if "stderr" in cmd_result else "",
                "returncode": cmd_result["returncode"]
            }
            
            if result["success"]:
                self.logger.debug("Python code executed successfully in subprocess")
            else:
                self.logger.warning(f"Python subprocess execution failed with code {cmd_result['returncode']}")
            
            return result
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(code_path)
            except Exception as e:
                self.logger.warning(f"Failed to remove temporary Python file: {str(e)}")


def execute_python_code(code: str, use_subprocess: bool = False, capture_locals: bool = False, 
                       input_vars: Optional[Dict[str, Any]] = None, timeout: Optional[int] = 30) -> Dict[str, Any]:
    """
    Execute Python code using the PythonExecuteTool.
    
    Args:
        code (str): Python code to execute
        use_subprocess (bool, optional): Run in a subprocess for isolation
        capture_locals (bool, optional): Capture local variables after execution
        input_vars (Dict[str, Any], optional): Variables to inject into the context
        timeout (int, optional): Timeout in seconds (only for subprocess)
        
    Returns:
        Dict[str, Any]: Execution results
    """
    tool = PythonExecuteTool()
    return tool.run(
        code=code,
        use_subprocess=use_subprocess,
        capture_locals=capture_locals,
        input_vars=input_vars,
        timeout=timeout
    )
