import os
import signal
import sys
import threading
import time
from typing import Dict, Optional, Any

from app.tool.base import BaseTool
from app.exceptions import ToolError


class TerminateTool(BaseTool):
    """Tool for terminating processes or the current execution."""
    
    def __init__(self):
        """Initialize the terminate tool."""
        super().__init__(
            name="terminate",
            description="Gracefully terminate processes or the current execution"
        )
    
    def _run(self, 
             message: str = "Task completed successfully",
             exit_code: int = 0,
             delay: int = 0,
             terminate_type: str = "soft") -> Dict[str, Any]:
        """
        Terminate the current process.
        
        Args:
            message (str, optional): Message to display before termination
            exit_code (int, optional): Exit code to return
            delay (int, optional): Delay in seconds before termination
            terminate_type (str, optional): Type of termination (soft, hard)
            
        Returns:
            Dict[str, Any]: Result of termination (only returned if terminate_type is "soft")
        """
        try:
            # Log termination request
            self.logger.info(f"Termination requested with message: {message}")
            
            # Return result if terminate_type is "soft"
            if terminate_type.lower() == "soft":
                return {
                    "status": "terminated",
                    "message": message,
                    "exit_code": exit_code,
                    "terminate_type": terminate_type
                }
            
            # Schedule hard termination after delay
            if delay > 0:
                def delayed_exit():
                    time.sleep(delay)
                    print(f"Terminating: {message}")
                    sys.exit(exit_code)
                
                # Start delayed exit thread
                thread = threading.Thread(target=delayed_exit)
                thread.daemon = True
                thread.start()
                
                return {
                    "status": "terminating",
                    "message": message,
                    "exit_code": exit_code,
                    "delay": delay,
                    "terminate_type": terminate_type
                }
            
            # Immediate termination
            print(f"Terminating: {message}")
            sys.exit(exit_code)
            
        except Exception as e:
            error_msg = f"Failed to terminate process: {str(e)}"
            self.logger.error(error_msg)
            raise ToolError(error_msg)
    
    def terminate_process(self, pid: int, signal_type: int = signal.SIGTERM) -> Dict[str, Any]:
        """
        Terminate a specific process by PID.
        
        Args:
            pid (int): Process ID to terminate
            signal_type (int, optional): Signal type to send
            
        Returns:
            Dict[str, Any]: Result of termination
        """
        try:
            # Check if process exists
            if not self._check_process_exists(pid):
                return {
                    "status": "error",
                    "message": f"Process with PID {pid} does not exist",
                    "success": False
                }
            
            # Send signal to process
            os.kill(pid, signal_type)
            
            # Check if process was terminated
            time.sleep(0.5)  # Short delay to allow process to terminate
            process_exists = self._check_process_exists(pid)
            
            return {
                "status": "terminated" if not process_exists else "signal_sent",
                "message": f"Process with PID {pid} {'terminated' if not process_exists else 'received signal'}",
                "pid": pid,
                "signal": signal_type,
                "success": True
            }
            
        except Exception as e:
            error_msg = f"Failed to terminate process {pid}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "pid": pid,
                "signal": signal_type,
                "success": False
            }
    
    def _check_process_exists(self, pid: int) -> bool:
        """
        Check if a process with the given PID exists.
        
        Args:
            pid (int): Process ID to check
            
        Returns:
            bool: True if process exists, False otherwise
        """
        try:
            # Sending signal 0 tests if the process exists without actually sending a signal
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def terminate_execution(message: str = "Task completed successfully", exit_code: int = 0,
                       delay: int = 0, terminate_type: str = "soft") -> Dict[str, Any]:
    """
    Terminate the current execution using the TerminateTool.
    
    Args:
        message (str, optional): Message to display before termination
        exit_code (int, optional): Exit code to return
        delay (int, optional): Delay in seconds before termination
        terminate_type (str, optional): Type of termination (soft, hard)
        
    Returns:
        Dict[str, Any]: Result of termination (only returned if terminate_type is "soft")
    """
    tool = TerminateTool()
    return tool.run(
        message=message,
        exit_code=exit_code,
        delay=delay,
        terminate_type=terminate_type
    )
