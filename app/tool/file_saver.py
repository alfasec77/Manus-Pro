import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.tool.base import BaseTool
from app.exceptions import FileOperationError
from app.config import config


class FileSaverTool(BaseTool):
    """Tool for saving content to files."""
    
    def __init__(self):
        """Initialize the file saver tool."""
        super().__init__(
            name="file_saver",
            description="Save content to files on the filesystem"
        )
    
    def _run(self, 
             content: str, 
             file_path: str, 
             mode: str = "w", 
             encoding: str = "utf-8",
             create_dirs: bool = True) -> str:
        """
        Save content to a file.
        
        Args:
            content (str): Content to save
            file_path (str): Path to save the file
            mode (str, optional): File mode ('w' for write, 'a' for append)
            encoding (str, optional): File encoding
            create_dirs (bool, optional): Create directories if they don't exist
            
        Returns:
            str: Path to the saved file
        """
        try:
            # Make file_path absolute if it's not already
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            # Create directories if they don't exist
            if create_dirs:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write content to file
            with open(file_path, mode=mode, encoding=encoding) as f:
                f.write(content)
            
            self.logger.info(f"Content successfully saved to {file_path}")
            return file_path
            
        except Exception as e:
            error_msg = f"Failed to save content to file: {str(e)}"
            self.logger.error(error_msg)
            raise FileOperationError(error_msg)
    
    def save_binary(self, content: bytes, file_path: str, create_dirs: bool = True) -> str:
        """
        Save binary content to a file.
        
        Args:
            content (bytes): Binary content to save
            file_path (str): Path to save the file
            create_dirs (bool, optional): Create directories if they don't exist
            
        Returns:
            str: Path to the saved file
        """
        try:
            # Make file_path absolute if it's not already
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            # Create directories if they don't exist
            if create_dirs:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write binary content to file
            with open(file_path, mode="wb") as f:
                f.write(content)
            
            self.logger.info(f"Binary content successfully saved to {file_path}")
            return file_path
            
        except Exception as e:
            error_msg = f"Failed to save binary content to file: {str(e)}"
            self.logger.error(error_msg)
            raise FileOperationError(error_msg)


def save_file_content(content: str, file_path: str, mode: str = "w", encoding: str = "utf-8", create_dirs: bool = True) -> str:
    """
    Save content to a file using the FileSaverTool.
    
    Args:
        content (str): Content to save
        file_path (str): Path to save the file
        mode (str, optional): File mode ('w' for write, 'a' for append)
        encoding (str, optional): File encoding
        create_dirs (bool, optional): Create directories if they don't exist
        
    Returns:
        str: Path to the saved file
    """
    tool = FileSaverTool()
    return tool.run(
        content=content,
        file_path=file_path,
        mode=mode,
        encoding=encoding,
        create_dirs=create_dirs
    )
