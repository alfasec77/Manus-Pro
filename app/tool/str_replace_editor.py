import os
import re
from typing import Dict, List, Optional, Any

from app.tool.base import BaseTool
from app.exceptions import FileOperationError
from app.config import config


class StrReplaceEditorTool(BaseTool):
    """Tool for editing text using string replacement operations."""
    
    def __init__(self):
        """Initialize the string replace editor tool."""
        super().__init__(
            name="str_replace_editor",
            description="Edit text or files using string replacement operations"
        )
    
    def _run(self, 
             text: Optional[str] = None,
             file_path: Optional[str] = None,
             replacements: List[Dict[str, str]] = None,
             regex: bool = False,
             save_changes: bool = True,
             backup: bool = True) -> Dict[str, Any]:
        """
        Edit text using string replacement operations.
        
        Args:
            text (str, optional): Text to edit (used if file_path not provided)
            file_path (str, optional): Path to file to edit
            replacements (List[Dict[str, str]]): List of replacement dictionaries
            regex (bool, optional): Use regex for replacements
            save_changes (bool, optional): Save changes to file
            backup (bool, optional): Create backup before editing file
            
        Returns:
            Dict[str, Any]: Editing results
        """
        try:
            # Initialize content from text or file
            content = text
            if file_path and not content:
                content = self._read_file(file_path)
            
            if not content:
                raise FileOperationError("Either 'text' or 'file_path' must be provided")
            
            if not replacements:
                replacements = []
            
            # Perform replacements
            original_content = content
            num_replacements = 0
            
            for replacement in replacements:
                old = replacement.get("old", "")
                new = replacement.get("new", "")
                
                if not old:
                    continue
                
                if regex:
                    # Use regex replacement
                    pattern = re.compile(old, re.MULTILINE)
                    result = pattern.subn(new, content)
                    content = result[0]
                    num_replacements += result[1]
                else:
                    # Use simple string replacement
                    if old in content:
                        count = content.count(old)
                        content = content.replace(old, new)
                        num_replacements += count
            
            # Save changes to file if requested
            if file_path and save_changes:
                # Create backup if requested
                if backup:
                    backup_path = f"{file_path}.bak"
                    with open(backup_path, "w", encoding="utf-8") as f:
                        f.write(original_content)
                
                # Write updated content
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                self.logger.info(f"Successfully edited file {file_path} with {num_replacements} replacements")
            
            # Return results
            return {
                "original_content": original_content,
                "updated_content": content,
                "num_replacements": num_replacements,
                "file_path": file_path if file_path else None,
                "success": True
            }
            
        except Exception as e:
            error_msg = f"Failed to perform text replacements: {str(e)}"
            self.logger.error(error_msg)
            raise FileOperationError(error_msg)
    
    def _read_file(self, file_path: str) -> str:
        """
        Read content from a file.
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: File content
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            error_msg = f"Failed to read file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise FileOperationError(error_msg)
    
    def edit_lines(self, 
                  file_path: str, 
                  line_edits: List[Dict[str, Any]],
                  save_changes: bool = True,
                  backup: bool = True) -> Dict[str, Any]:
        """
        Edit specific lines in a file.
        
        Args:
            file_path (str): Path to the file
            line_edits (List[Dict[str, Any]]): List of line edit operations
            save_changes (bool, optional): Save changes to file
            backup (bool, optional): Create backup before editing file
            
        Returns:
            Dict[str, Any]: Editing results
        """
        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            original_lines = lines.copy()
            num_edits = 0
            
            # Perform line edits
            for edit in line_edits:
                line_num = edit.get("line")
                action = edit.get("action", "replace")
                content = edit.get("content", "")
                
                if line_num is None:
                    continue
                
                # Adjust for 0-indexed list
                idx = line_num - 1 if line_num > 0 else line_num
                
                if action == "replace" and 0 <= idx < len(lines):
                    lines[idx] = content + ("\n" if not content.endswith("\n") else "")
                    num_edits += 1
                elif action == "insert" and 0 <= idx <= len(lines):
                    lines.insert(idx, content + ("\n" if not content.endswith("\n") else ""))
                    num_edits += 1
                elif action == "delete" and 0 <= idx < len(lines):
                    lines.pop(idx)
                    num_edits += 1
                elif action == "append":
                    lines.append(content + ("\n" if not content.endswith("\n") else ""))
                    num_edits += 1
            
            # Save changes to file if requested
            if save_changes:
                # Create backup if requested
                if backup:
                    backup_path = f"{file_path}.bak"
                    with open(backup_path, "w", encoding="utf-8") as f:
                        f.writelines(original_lines)
                
                # Write updated content
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                
                self.logger.info(f"Successfully edited file {file_path} with {num_edits} line edits")
            
            # Return results
            return {
                "original_lines": original_lines,
                "updated_lines": lines,
                "num_edits": num_edits,
                "file_path": file_path,
                "success": True
            }
            
        except Exception as e:
            error_msg = f"Failed to perform line edits: {str(e)}"
            self.logger.error(error_msg)
            raise FileOperationError(error_msg)


def edit_text(text: Optional[str] = None, file_path: Optional[str] = None,
             replacements: List[Dict[str, str]] = None, regex: bool = False,
             save_changes: bool = True, backup: bool = True) -> Dict[str, Any]:
    """
    Edit text using the StrReplaceEditorTool.
    
    Args:
        text (str, optional): Text to edit (used if file_path not provided)
        file_path (str, optional): Path to file to edit
        replacements (List[Dict[str, str]]): List of replacement dictionaries
        regex (bool, optional): Use regex for replacements
        save_changes (bool, optional): Save changes to file
        backup (bool, optional): Create backup before editing file
        
    Returns:
        Dict[str, Any]: Editing results
    """
    tool = StrReplaceEditorTool()
    return tool.run(
        text=text,
        file_path=file_path,
        replacements=replacements,
        regex=regex,
        save_changes=save_changes,
        backup=backup
    )
