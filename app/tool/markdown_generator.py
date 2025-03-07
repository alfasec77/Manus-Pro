import os
import uuid
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.tool.base import BaseTool
from app.schema import DocumentFormat, GenerateDocumentInput
from app.exceptions import DocumentGenerationError
from app.config import config
from app.tool.file_saver import FileSaverTool


# Define a Pydantic model for the tool parameters
class MarkdownGeneratorParams(BaseModel):
    content: str = Field(..., description="Content for the Markdown document")
    output_path: Optional[str] = Field(None, description="Path to save the Markdown file (optional)")
    title: Optional[str] = Field(None, description="Document title (optional)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the document (optional)")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options for document generation (optional)")


class MarkdownGeneratorTool(BaseTool):
    """Tool for generating Markdown documents."""
    
    def __init__(self):
        """Initialize the Markdown generator tool."""
        parameters = {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content for the Markdown document"
                },
                "output_path": {
                    "type": "string",
                    "description": "Path to save the Markdown file (optional)"
                },
                "title": {
                    "type": "string",
                    "description": "Document title (optional)"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata for the document (optional)"
                },
                "options": {
                    "type": "object",
                    "description": "Additional options for document generation (optional)"
                }
            },
            "required": ["content"]
        }
        
        super().__init__(
            name="markdown_generator",
            description="Generate Markdown documents from text content",
            parameters=parameters
        )
        
        # Create artifacts directory if it doesn't exist
        self.artifacts_dir = config.get_nested_value(["artifacts", "base_dir"], "./artifacts")
        self.markdown_artifacts_dir = os.path.join(self.artifacts_dir, "markdown")
        os.makedirs(self.markdown_artifacts_dir, exist_ok=True)
        
        # Initialize the file saver tool
        self.file_saver = FileSaverTool()
    
    def _save_artifact(self, markdown_path: str, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Save Markdown as an artifact.
        
        Args:
            markdown_path (str): Path to the Markdown file
            title (Optional[str]): Title of the document
            metadata (Optional[Dict[str, Any]]): Additional metadata
            
        Returns:
            str: Path to the saved artifact
        """
        # Generate a unique ID for this artifact
        artifact_id = str(uuid.uuid4())
        
        # Create filename if title is provided
        if title:
            safe_title = "".join(c if c.isalnum() else "_" for c in title[:30]).lower()
            filename = f"{safe_title}_{artifact_id[:8]}.md"
        else:
            filename = f"markdown_{artifact_id[:8]}.md"
        
        # Create artifact path
        artifact_path = os.path.join(self.markdown_artifacts_dir, filename)
        
        # Copy the file to artifacts directory
        with open(markdown_path, "r", encoding="utf-8") as src_file:
            content = src_file.read()
        
        with open(artifact_path, "w", encoding="utf-8") as dst_file:
            dst_file.write(content)
        
        # Create metadata file
        metadata_path = os.path.join(self.markdown_artifacts_dir, f"{filename}.meta.json")
        
        # Prepare metadata
        meta = {
            "id": artifact_id,
            "title": title,
            "original_path": markdown_path,
            "timestamp": config.get_timestamp(),
            "type": "markdown"
        }
        
        if metadata:
            meta.update(metadata)
        
        # Save metadata
        with open(metadata_path, "w", encoding="utf-8") as f:
            import json
            json.dump(meta, f, indent=2)
        
        self.logger.info(f"Markdown artifact saved to {artifact_path}")
        return artifact_path
    
    def _open_markdown(self, markdown_path: str) -> None:
        """
        Open the Markdown file using the appropriate system command.
        
        Args:
            markdown_path (str): Path to the Markdown file
        """
        try:
            # Check if markdown_path exists
            if not os.path.exists(markdown_path):
                self.logger.warning(f"Cannot open Markdown - file does not exist: {markdown_path}")
                return
                
            if os.name == 'nt':  # Windows
                os.startfile(markdown_path)
            elif os.name == 'posix':  # macOS or Linux
                platform = os.uname().sysname
                if platform == 'Darwin':  # macOS
                    # Try to use a markdown editor if available, otherwise just open with default app
                    try:
                        # Check if VS Code is available
                        subprocess.run(['which', 'code'], check=True, capture_output=True)
                        subprocess.Popen(['code', markdown_path])
                    except subprocess.CalledProcessError:
                        # Fall back to default app
                        subprocess.Popen(['open', markdown_path])
                else:  # Linux
                    # Try different editors in order of preference
                    editors = ['xdg-open', 'gedit', 'kate', 'nano', 'vim']
                    for editor in editors:
                        try:
                            subprocess.run(['which', editor], check=True, capture_output=True)
                            subprocess.Popen([editor, markdown_path])
                            break
                        except subprocess.CalledProcessError:
                            continue
            else:
                self.logger.warning(f"Unsupported operating system for auto-opening Markdown: {os.name}")
        except Exception as e:
            self.logger.warning(f"Error opening Markdown file: {str(e)}")
    
    def _run(self, 
             content: str, 
             output_path: Optional[str] = None, 
             title: Optional[str] = None, 
             metadata: Optional[Dict[str, Any]] = None,
             options: Optional[Dict[str, Any]] = None,
             action: Optional[str] = None,
             file_name: Optional[str] = None,
             file_path: Optional[str] = None,
             format: Optional[str] = None,
             text: Optional[str] = None,
             file: Optional[str] = None,
             **kwargs) -> Dict[str, Any]:
        """
        Generate a Markdown document.
        
        Args:
            content (str): Content for the Markdown file
            output_path (str, optional): Path to save the Markdown file
            title (str, optional): Document title
            metadata (Dict[str, Any], optional): Document metadata
            options (Dict[str, Any], optional): Additional options for document generation
            action (str, optional): Action parameter (ignored, for compatibility)
            file_name (str, optional): Alternative name for the output file (ignored, use output_path instead)
            file_path (str, optional): Alternative path for the output file (ignored, use output_path instead)
            format (str, optional): Format for the output (defaults to markdown, ignored as this tool always generates markdown)
            text (str, optional): Alternative parameter for content (will be used if content is empty)
            file (str, optional): Alternative parameter for output file (ignored, use output_path instead)
            **kwargs: Any other parameters (ignored for compatibility)
            
        Returns:
            Dict[str, Any]: Dictionary containing path to the generated Markdown file and additional information
        """
        # Use text parameter as content if content is empty
        if not content and text:
            content = text
            self.logger.info(f"Using 'text' parameter as content")
            
        # Handle file parameter as an alternative to output_path if output_path is not provided
        if not output_path and file:
            output_path = file
            self.logger.info(f"Using 'file' parameter as output_path: {output_path}")
        
        # Handle file_path parameter as an alternative to output_path if output_path is still not provided
        if not output_path and file_path:
            output_path = file_path
            self.logger.info(f"Using file_path parameter as output_path: {output_path}")
        
        # Handle file_name parameter to append to output directory if output_path is still not provided
        if not output_path and file_name:
            # Use default output directory
            output_dir = config.get_nested_value(["document", "markdown_output_dir"], "./output/markdown")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, file_name)
            self.logger.info(f"Using file_name parameter to construct output_path: {output_path}")
        
        if not output_path:
            # Use default output directory from config
            output_dir = config.get_nested_value(["document", "markdown_output_dir"], "./output/markdown")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename from title or use default
            filename = f"{title.lower().replace(' ', '_')}.md" if title else "generated_document.md"
            output_path = os.path.join(output_dir, filename)
        
        try:
            # Prepare content
            final_content = ""
            
            # Add title if provided
            if title:
                final_content += f"# {title}\n\n"
            
            # Add metadata if provided
            if metadata:
                final_content += "---\n"
                for key, value in metadata.items():
                    final_content += f"{key}: {value}\n"
                final_content += "---\n\n"
            
            # Add main content
            final_content += content
            
            # Use the file_saver tool to save the content
            self.file_saver.run(
                content=final_content,
                file_path=output_path,
                mode="w",
                encoding="utf-8",
                create_dirs=True
            )
            
            # Save as artifact
            artifact_path = self._save_artifact(output_path, title, metadata)
            
            # Auto-open Markdown if specified in options
            auto_open = options.get('auto_open', False) if options else False
            if auto_open:
                try:
                    self._open_markdown(artifact_path)
                except Exception as e:
                    self.logger.warning(f"Could not automatically open Markdown: {str(e)}")
            
            self.logger.info(f"Markdown file successfully generated at {output_path}")
            
            return {
                "artifact_path": artifact_path,
                "original_path": output_path,
                "title": title,
                "metadata": metadata
            }
            
        except Exception as e:
            error_msg = f"Failed to generate Markdown file: {str(e)}"
            self.logger.error(error_msg)
            raise DocumentGenerationError(error_msg)


def create_markdown_from_input(input_data: GenerateDocumentInput) -> Dict[str, Any]:
    """
    Create a Markdown file from the GenerateDocumentInput.
    
    Args:
        input_data (GenerateDocumentInput): Input data for document generation
        
    Returns:
        Dict[str, Any]: Dictionary containing path to the generated Markdown file and additional information
    """
    tool = MarkdownGeneratorTool()
    options = {"auto_open": input_data.options.get("auto_open", False)} if input_data.options else None
    
    return tool.run(
        content=input_data.content,
        output_path=input_data.output_path,
        title=input_data.title,
        metadata=input_data.metadata,
        options=options,
        format=input_data.format.value if hasattr(input_data, 'format') else None,
        # Add compatibility with any other fields that might be present
        **{k: v for k, v in input_data.__dict__.items() if k not in [
            'content', 'output_path', 'title', 'metadata', 'options', 'format'
        ] and not k.startswith('_')}
    )
