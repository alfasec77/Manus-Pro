import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Union

from app.tool.base import BaseTool
from app.exceptions import ToolError


class BashTool(BaseTool):
    """Tool for executing bash/shell commands."""
    
    def __init__(self):
        """Initialize the bash tool."""
        super().__init__(
            name="bash",
            description="Execute bash/shell commands in the system"
        )
    
    def _run(self, 
             command: str, 
             cwd: Optional[str] = None,
             env: Optional[Dict[str, str]] = None,
             timeout: Optional[int] = 60,
             capture_stderr: bool = True,
             text: bool = True) -> Dict[str, Union[str, int, List[str]]]:
        """
        Execute a bash/shell command.
        
        Args:
            command (str): Command to execute
            cwd (str, optional): Working directory
            env (Dict[str, str], optional): Environment variables
            timeout (int, optional): Timeout in seconds
            capture_stderr (bool, optional): Capture stderr output
            text (bool, optional): Return string output (vs bytes)
            
        Returns:
            Dict[str, Union[str, int, List[str]]]: Command execution results
        """
        try:
            self.logger.debug(f"Executing command: {command}")
            
            # Set up process arguments
            kwargs = {
                "shell": True,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE if capture_stderr else subprocess.DEVNULL,
                "text": text
            }
            
            if cwd:
                kwargs["cwd"] = cwd
            if env:
                # Merge with current environment
                full_env = os.environ.copy()
                full_env.update(env)
                kwargs["env"] = full_env
            
            # Execute command
            process = subprocess.run(command, timeout=timeout, **kwargs)
            
            # Prepare result
            result = {
                "returncode": process.returncode,
                "stdout": process.stdout,
                "command": command
            }
            
            if capture_stderr:
                result["stderr"] = process.stderr
            
            # Log success or failure
            if process.returncode == 0:
                self.logger.debug(f"Command executed successfully: {command}")
            else:
                self.logger.warning(f"Command returned non-zero exit code {process.returncode}: {command}")
                if capture_stderr:
                    self.logger.warning(f"stderr: {process.stderr}")
            
            return result
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds: {command}"
            self.logger.error(error_msg)
            return {
                "returncode": 124,  # Standard timeout exit code
                "stdout": "",
                "stderr": "Command timed out",
                "command": command,
                "error": "timeout"
            }
        except Exception as e:
            error_msg = f"Failed to execute command: {str(e)}"
            self.logger.error(error_msg)
            raise ToolError(error_msg)
    
    def execute_script(self, script_content: str, script_type: str = "bash", **kwargs) -> Dict[str, Union[str, int, List[str]]]:
        """
        Execute a script by saving it to a temporary file and running it.
        
        Args:
            script_content (str): Content of the script
            script_type (str, optional): Type of script (bash, python, etc.)
            **kwargs: Additional arguments for _run method
            
        Returns:
            Dict[str, Union[str, int, List[str]]]: Script execution results
        """
        # Create temporary script file
        script_extension_map = {
            "bash": ".sh",
            "python": ".py",
            "perl": ".pl",
            "ruby": ".rb",
            "node": ".js"
        }
        extension = script_extension_map.get(script_type, ".sh")
        
        with tempfile.NamedTemporaryFile(suffix=extension, mode='w', delete=False) as script_file:
            script_path = script_file.name
            script_file.write(script_content)
        
        try:
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Prepare command based on script type
            command_prefix_map = {
                "bash": "bash",
                "python": "python",
                "perl": "perl",
                "ruby": "ruby",
                "node": "node"
            }
            prefix = command_prefix_map.get(script_type, "bash")
            command = f"{prefix} {script_path}"
            
            # Execute the script
            result = self._run(command, **kwargs)
            
            return result
        finally:
            # Clean up temporary file
            try:
                os.unlink(script_path)
            except Exception as e:
                self.logger.warning(f"Failed to remove temporary script file: {str(e)}")


def execute_bash_command(command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, 
                         timeout: Optional[int] = 60, capture_stderr: bool = True) -> Dict[str, Union[str, int, List[str]]]:
    """
    Execute a bash command using the BashTool.
    
    Args:
        command (str): Command to execute
        cwd (str, optional): Working directory
        env (Dict[str, str], optional): Environment variables
        timeout (int, optional): Timeout in seconds
        capture_stderr (bool, optional): Capture stderr output
        
    Returns:
        Dict[str, Union[str, int, List[str]]]: Command execution results
    """
    tool = BashTool()
    return tool.run(
        command=command,
        cwd=cwd,
        env=env,
        timeout=timeout,
        capture_stderr=capture_stderr
    )
