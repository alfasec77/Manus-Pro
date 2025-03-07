import os
import re
import uuid
import json
import logging
import tempfile
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from pydantic import BaseModel, Field
import datetime

from app.tool.base import BaseTool
from app.schema import CodeGenerationInput
from app.exceptions import CodeGenerationError
from app.llm import llm_manager
from app.config import config


# Define a Pydantic model for the tool parameters
class CodeGeneratorParams(BaseModel):
    description: str = Field(..., description="Description of the code to generate")
    language: str = Field("python", description="Programming language for the code (default: python)")
    output_path: Optional[str] = Field(None, description="Path to save the code file (optional)")
    dependencies: Optional[List[str]] = Field(None, description="List of dependencies for the code (optional)")
    template: Optional[str] = Field(None, description="Template for the code (optional)")
    execute_code: bool = Field(True, description="Whether to execute the generated code (default: True)")


class CodeGeneratorTool(BaseTool):
    """Tool for generating code based on descriptions."""
    
    def __init__(self):
        """Initialize the code generator tool."""
        parameters = {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Description of the code to generate"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language for the code",
                    "default": "python"
                },
                "output_path": {
                    "type": "string",
                    "description": "Path to save the code file (optional)"
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of dependencies for the code (optional)"
                },
                "template": {
                    "type": "string",
                    "description": "Template for the code (optional)"
                },
                "execute_code": {
                    "type": "boolean",
                    "description": "Whether to execute the generated code (default: True)"
                }
            },
            "required": ["description"]
        }
        
        super().__init__(
            name="code_generator",
            description="Generate code based on descriptions",
            parameters=parameters
        )
        
        # Define supported languages and file extensions
        self.language_extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "html": ".html",
            "css": ".css",
            "java": ".java",
            "c": ".c",
            "cpp": ".cpp",
            "go": ".go",
            "rust": ".rs",
            "ruby": ".rb",
            "php": ".php",
            "shell": ".sh",
            "bash": ".sh",
            "sql": ".sql",
            "r": ".r"
        }
        
        # Define languages that can be executed
        self.executable_languages = ["python", "javascript", "nodejs", "node", "shell", "bash"]
        
        # Create artifacts directory if it doesn't exist
        self.artifacts_dir = config.get_nested_value(["artifacts", "base_dir"], "./artifacts")
        self.code_artifacts_dir = os.path.join(self.artifacts_dir, "code")
        os.makedirs(self.code_artifacts_dir, exist_ok=True)
        
        # Create execution outputs directory
        self.execution_outputs_dir = os.path.join(self.artifacts_dir, "execution_outputs")
        os.makedirs(self.execution_outputs_dir, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _save_artifact(self, code: str, language: str, description: str, filename: Optional[str] = None) -> str:
        """
        Save code as an artifact.
        
        Args:
            code (str): Generated code
            language (str): Programming language
            description (str): Code description
            filename (Optional[str]): Optional filename
            
        Returns:
            str: Path to the saved artifact
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate a clean filename from description if not provided
        if not filename:
            # Create a sanitized filename from description
            clean_description = re.sub(r'[^\w\s-]', '', description.lower())
            clean_description = re.sub(r'[\s-]+', '_', clean_description).strip('_')
            
            # Limit to 30 chars to avoid overly long filenames
            if len(clean_description) > 30:
                clean_description = clean_description[:30]
                
            # Add timestamp for uniqueness
            filename = f"{clean_description}_{timestamp}{self._get_file_extension(language)}"
        else:
            # Make sure filename has correct extension
            if not any(filename.endswith(ext) for ext in self.language_extensions.values()):
                filename += self._get_file_extension(language)
        
        # Create artifact directory if it doesn't exist
        os.makedirs(self.code_artifacts_dir, exist_ok=True)
        
        # Create language-specific subdirectory
        language_dir = os.path.join(self.code_artifacts_dir, language.lower())
        os.makedirs(language_dir, exist_ok=True)
        
        # Save code to file
        file_path = os.path.join(language_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Save metadata
        metadata = {
            "description": description,
            "language": language,
            "timestamp": timestamp,
            "filename": filename
        }
        
        metadata_path = os.path.join(language_dir, f"{os.path.splitext(filename)[0]}_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"Code artifact saved: {file_path}")
        
        return file_path
    
    def _get_file_extension(self, language: str) -> str:
        """
        Get the file extension for a given programming language.
        
        Args:
            language (str): Programming language
            
        Returns:
            str: File extension for the language
        """
        language = language.lower()
        return self.language_extensions.get(language, ".txt")
        
    def _format_code(self, code: str, language: str) -> str:
        """
        Format code for better readability based on language.
        
        Args:
            code (str): Code to format
            language (str): Programming language
            
        Returns:
            str: Formatted code
        """
        # Remove excessive blank lines (more than 2 consecutive)
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        # Fix inconsistent indentation in Python
        if language.lower() == "python":
            lines = code.split('\n')
            formatted_lines = []
            for line in lines:
                # Convert any mix of tabs and spaces at the beginning of the line to spaces
                if line.strip():  # Skip empty lines
                    leading_whitespace = re.match(r'^[ \t]*', line).group()
                    if leading_whitespace:
                        # Convert tabs to 4 spaces and normalize indentation
                        space_count = leading_whitespace.count(' ') + (leading_whitespace.count('\t') * 4)
                        # Round to nearest multiple of 4
                        space_count = (space_count // 4) * 4
                        formatted_line = ' ' * space_count + line.lstrip()
                        formatted_lines.append(formatted_line)
                    else:
                        formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
            code = '\n'.join(formatted_lines)
            
        return code
        
    def _enhance_code_with_comments(self, code: str, language: str, description: str) -> str:
        """
        Enhance code with better comments and documentation.
        
        Args:
            code (str): Generated code
            language (str): Programming language
            description (str): Code description
            
        Returns:
            str: Enhanced code with better comments
        """
        if not code:
            return code
            
        # Add a header comment based on language
        header = ""
        language = language.lower()
        
        description_lines = description.split('\n')
        description_text = '\n'.join([f"{line}" for line in description_lines])
        
        if language in ["python", "ruby", "shell", "bash", "r"]:
            header = f"#!/usr/bin/env {language}\n"
            header += "# " + "-" * 78 + "\n"
            header += f"# Description: {description_text}\n"
            header += "# Generated by: Manus Code Generator\n"
            header += f"# Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            header += "# " + "-" * 78 + "\n\n"
        elif language in ["javascript", "typescript", "java", "c", "cpp", "csharp", "go", "rust", "kotlin", "scala", "php", "swift"]:
            header = "/**\n"
            header += f" * Description: {description_text}\n"
            header += " * Generated by: Manus Code Generator\n"
            header += f" * Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            header += " */\n\n"
        elif language in ["html"]:
            header = "<!-- \n"
            header += f"  Description: {description_text}\n"
            header += "  Generated by: Manus Code Generator\n"
            header += f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            header += "-->\n\n"
            
        # Only add the header if it doesn't already exist
        if not code.startswith(header.strip()):
            code = header + code
            
        return code
        
    def _run(self, 
             description: str, 
             language: str = "python", 
             output_path: Optional[str] = None, 
             dependencies: Optional[List[str]] = None, 
             template: Optional[str] = None,
             execute_code: bool = True,
             action: Optional[str] = None,
             file_name: Optional[str] = None,
             file_path: Optional[str] = None,
             content: Optional[str] = None,
             text: Optional[str] = None,
             file: Optional[str] = None,
             format: Optional[str] = None,
             **kwargs) -> Dict[str, Any]:
        """
        Generate code based on a description.
        
        Args:
            description (str): Description of the code to generate
            language (str, optional): Programming language for the code. Defaults to "python".
            output_path (str, optional): Path to save the code file. Defaults to None.
            dependencies (List[str], optional): List of dependencies for the code. Defaults to None.
            template (str, optional): Template for the code. Defaults to None.
            execute_code (bool, optional): Whether to execute the generated code. Defaults to True.
            **kwargs: Additional arguments for compatibility with other tools
            
        Returns:
            Dict[str, Any]: Dictionary containing generated code and additional information
        """
        try:
            # Normalize language
            language = language.lower()
            
            # Use content/text parameter as description if description is empty
            if not description:
                if content:
                    description = content
                elif text:
                    description = text
                    
            if not description:
                raise ValueError("Description is required for code generation")
                
            # Handle file parameters for compatibility
            if not output_path:
                if file_path:
                    output_path = file_path
                elif file:
                    output_path = file
                elif file_name:
                    output_dir = config.get_nested_value(["document", "code_output_dir"], "./output/code")
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, file_name)
            
            # Create prompt for code generation
            system_prompt = """You are an experienced software developer skilled in writing clean, efficient, and well-documented code.
Your task is to generate code based on the provided description and specifications. 
Follow these guidelines:
1. Write code that is idiomatic for the specified language
2. Include comprehensive comments and documentation
3. Follow best practices and design patterns
4. Ensure the code is secure, efficient, and maintainable
5. Organize the code logically with clear structure
6. Include error handling and edge case management
7. Add meaningful variable and function names
8. Write reusable, modular code
9. If the language supports them, add appropriate types and interfaces

Output only the code without any additional explanations, markdown formatting, or code block markers."""

            # Add language-specific instructions and dependencies
            if language == "python":
                system_prompt += "\nFor Python, follow PEP 8, add docstrings, use type hints, and handle exceptions properly."
                if dependencies:
                    system_prompt += f"\nInclude imports for these dependencies: {', '.join(dependencies)}"
            elif language in ["javascript", "typescript"]:
                system_prompt += "\nFor JavaScript/TypeScript, follow standard conventions, use async/await for asynchronous operations, and handle errors appropriately."
                if dependencies:
                    system_prompt += f"\nInclude imports/requires for these dependencies: {', '.join(dependencies)}"
            
            # Add template instructions if provided
            if template:
                system_prompt += f"\nBase your code on this template: {template}"
                
            # Generate code
            human_prompt = f"Generate {language} code for: {description}"
            
            # Use LLM manager to generate code
            code = llm_manager.generate_text(human_prompt, system_prompt)
            
            # Remove code block markers if present
            code = re.sub(r'^```\w*\n', '', code)
            code = re.sub(r'\n```$', '', code)
            
            # Format and enhance the code
            code = self._format_code(code, language)
            code = self._enhance_code_with_comments(code, language, description)
            
            # Save to specified output path if provided
            if output_path:
                # Create directory if it doesn't exist
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    
                # Make sure the file has the correct extension
                if not any(output_path.endswith(ext) for ext in self.language_extensions.values()):
                    output_path += self._get_file_extension(language)
                
                # Save the code
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                    
                self.logger.info(f"Generated code saved to: {output_path}")
            
            # Save as artifact
            artifact_path = self._save_artifact(code, language, description, file_name)
            
            # Execute the code in a subprocess regardless of auto-execute settings
            execution_result = None
            if language.lower() in self.executable_languages and execute_code:
                self.logger.info(f"Automatically executing generated {language} code")
                execution_result = self._execute_code(artifact_path, language)
            else:
                self.logger.info(f"Execution not supported for language: {language}")
                
            # Prepare result
            result = {
                "language": language,
                "description": description,
                "artifact_path": artifact_path,
                "status": "success",
                "message": f"Generated {language} code based on the description"
            }
            
            # Include a summary of the code instead of the full code
            code_summary = self._generate_code_summary(code, language)
            result["code_summary"] = code_summary
            
            if output_path:
                result["output_path"] = output_path
                
            if dependencies:
                result["dependencies"] = dependencies
                
            if execution_result:
                # Don't include stdout/stderr in the result to avoid terminal output
                execution_status = "succeeded" if execution_result.get("success", False) else "failed"
                
                # Add execution info to result
                result["execution"] = {
                    "success": execution_result.get("success", False),
                    "return_code": execution_result.get("return_code", -1)
                }
                
                # If output file was created, add it to the result
                if "output_file" in execution_result and execution_result["output_file"]:
                    result["execution"]["output_file"] = execution_result["output_file"]
                    
                    # Update message to refer to the artifact instead of showing in terminal
                    result["message"] += f"\nCode execution {execution_status}. See output at: {execution_result['output_file']}"
                else:
                    # Fallback for when saving output failed
                    result["message"] += f"\nCode execution {execution_status}."
            
            # Format a clear artifact message that can be extracted by the Manus agent
            artifact_message = f"\nGenerated code file saved as: {artifact_path}"
            result["message"] += artifact_message
                
            return result
            
        except Exception as e:
            self.logger.error(f"Code generation failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Code generation failed: {str(e)}",
                "error": str(e)
            }
            
    def _should_auto_execute(self, language: str, code: str) -> bool:
        """
        Determine if the code should be automatically executed.
        
        Args:
            language (str): Programming language
            code (str): Generated code
            
        Returns:
            bool: True if the code should be auto-executed, False otherwise
        """
        # Only execute for supported languages
        if language.lower() not in self.executable_languages:
            return False
            
        # Check config for auto-execution setting
        auto_execute = config.get_nested_value(["code_generator", "auto_execute"], False)
        if not auto_execute:
            return False
            
        # Basic safety checks for Python
        if language.lower() == "python":
            # Don't execute code that imports potentially dangerous modules
            dangerous_modules = ["os.system", "subprocess", "shutil.rmtree", "eval(", "exec("]
            for module in dangerous_modules:
                if module in code:
                    self.logger.warning(f"Code contains potentially dangerous module/function: {module}")
                    return False
                    
        # Limit execution to small code samples
        if len(code.split('\n')) > 100:
            self.logger.info("Code is too large for auto-execution (>100 lines)")
            return False
            
        return True
        
    def _execute_code(self, file_path: str, language: str) -> Dict[str, Any]:
        """
        Execute the generated code.
        
        Args:
            file_path (str): Path to the code file
            language (str): Programming language
            
        Returns:
            Dict[str, Any]: Execution results
        """
        try:
            language = language.lower()
            
            # Create a temporary directory for execution
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy the file to the temp directory
                temp_file_path = os.path.join(temp_dir, os.path.basename(file_path))
                with open(file_path, 'r', encoding='utf-8') as src_file:
                    code = src_file.read()
                    
                with open(temp_file_path, 'w', encoding='utf-8') as dst_file:
                    dst_file.write(code)
                    
                # Execute based on language
                if language == "python":
                    cmd = ["python", temp_file_path]
                    timeout = 10  # 10 seconds timeout
                    
                    self.logger.info(f"Executing Python code: {temp_file_path}")
                    process = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=temp_dir
                    )
                    
                    # Create execution output file
                    output_file_path = self._save_execution_output(
                        file_path=file_path,
                        language=language,
                        stdout=process.stdout,
                        stderr=process.stderr,
                        return_code=process.returncode
                    )
                    
                    return {
                        "stdout": process.stdout,
                        "stderr": process.stderr,
                        "return_code": process.returncode,
                        "success": process.returncode == 0,
                        "output_file": output_file_path
                    }
                    
                elif language in ["javascript", "node", "nodejs"]:
                    # Check if there's a package.json file in the same directory
                    package_json_path = os.path.join(os.path.dirname(temp_file_path), "package.json")
                    dir_has_package_json = os.path.exists(package_json_path)
                    
                    # If we have a package.json, copy it to the temp directory as well
                    if os.path.exists(os.path.join(os.path.dirname(file_path), "package.json")):
                        with open(os.path.join(os.path.dirname(file_path), "package.json"), 'r', encoding='utf-8') as pkg_src:
                            pkg_content = pkg_src.read()
                            
                        with open(package_json_path, 'w', encoding='utf-8') as pkg_dst:
                            pkg_dst.write(pkg_content)
                        dir_has_package_json = True
                    
                    # If package.json exists and has a "scripts" section with start script, use npm run
                    if dir_has_package_json:
                        try:
                            with open(package_json_path, 'r', encoding='utf-8') as pkg_file:
                                pkg_data = json.loads(pkg_file.read())
                                
                            if "scripts" in pkg_data and "start" in pkg_data["scripts"]:
                                self.logger.info(f"Executing npm start for JavaScript project: {temp_file_path}")
                                
                                # First install dependencies
                                install_process = subprocess.run(
                                    ["npm", "install"],
                                    capture_output=True,
                                    text=True,
                                    timeout=60,  # Longer timeout for npm install
                                    cwd=os.path.dirname(temp_file_path)
                                )
                                
                                if install_process.returncode != 0:
                                    self.logger.warning(f"npm install failed: {install_process.stderr}")
                                
                                # Then run the start script
                                process = subprocess.run(
                                    ["npm", "start"],
                                    capture_output=True,
                                    text=True,
                                    timeout=15,  # 15 seconds timeout
                                    cwd=os.path.dirname(temp_file_path)
                                )
                                
                                # Create execution output file
                                output_file_path = self._save_execution_output(
                                    file_path=file_path,
                                    language="npm",
                                    stdout=f"npm install output:\n{install_process.stdout}\n\nnpm start output:\n{process.stdout}",
                                    stderr=f"npm install errors:\n{install_process.stderr}\n\nnpm start errors:\n{process.stderr}",
                                    return_code=process.returncode
                                )
                                
                                return {
                                    "stdout": process.stdout,
                                    "stderr": process.stderr,
                                    "return_code": process.returncode,
                                    "success": process.returncode == 0,
                                    "output_file": output_file_path,
                                    "executed_with": "npm"
                                }
                        except Exception as e:
                            self.logger.warning(f"Failed to use npm: {str(e)}, falling back to node")
                    
                    # Default to using node directly
                    cmd = ["node", temp_file_path]
                    timeout = 10  # 10 seconds timeout
                    
                    self.logger.info(f"Executing JavaScript code: {temp_file_path}")
                    process = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=temp_dir
                    )
                    
                    # Create execution output file
                    output_file_path = self._save_execution_output(
                        file_path=file_path,
                        language=language,
                        stdout=process.stdout,
                        stderr=process.stderr,
                        return_code=process.returncode
                    )
                    
                    return {
                        "stdout": process.stdout,
                        "stderr": process.stderr,
                        "return_code": process.returncode,
                        "success": process.returncode == 0,
                        "output_file": output_file_path
                    }
                    
                elif language in ["shell", "bash"]:
                    # Make the script executable
                    os.chmod(temp_file_path, 0o755)
                    
                    cmd = ["/bin/bash", temp_file_path]
                    timeout = 10  # 10 seconds timeout
                    
                    self.logger.info(f"Executing shell script: {temp_file_path}")
                    process = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=temp_dir
                    )
                    
                    # Create execution output file
                    output_file_path = self._save_execution_output(
                        file_path=file_path,
                        language=language,
                        stdout=process.stdout,
                        stderr=process.stderr,
                        return_code=process.returncode
                    )
                    
                    return {
                        "stdout": process.stdout,
                        "stderr": process.stderr,
                        "return_code": process.returncode,
                        "success": process.returncode == 0,
                        "output_file": output_file_path
                    }
                    
                else:
                    return {
                        "message": f"Execution not supported for language: {language}",
                        "success": False
                    }
                    
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Code execution timed out for {file_path}")
            return {
                "message": "Execution timed out",
                "success": False,
                "error": "timeout"
            }
        except Exception as e:
            self.logger.error(f"Code execution failed: {str(e)}")
            return {
                "message": f"Execution failed: {str(e)}",
                "success": False,
                "error": str(e)
            }
            
    def _save_execution_output(self, file_path: str, language: str, stdout: str, stderr: str, return_code: int) -> str:
        """
        Save execution output to a file.
        
        Args:
            file_path (str): Path to the executed code file
            language (str): Programming language
            stdout (str): Standard output from execution
            stderr (str): Standard error from execution
            return_code (int): Return code from execution
            
        Returns:
            str: Path to the saved output file
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = self.execution_outputs_dir
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename based on code filename
            base_name = os.path.basename(file_path)
            output_filename = f"{os.path.splitext(base_name)[0]}_output.md"
            output_path = os.path.join(output_dir, output_filename)
            
            # Create formatted output content
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            output_content = f"""# Execution Output - {base_name}

## Execution Details
- **File**: `{base_name}`
- **Language**: {language}
- **Timestamp**: {timestamp}
- **Status**: {"Success" if return_code == 0 else f"Failed (Return Code: {return_code})"}

## Standard Output
```
{stdout if stdout.strip() else "(No output)"}
```

## Standard Error
```
{stderr if stderr.strip() else "(No errors)"}
```
"""
            
            # Save output to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
                
            self.logger.info(f"Execution output saved to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to save execution output: {str(e)}")
            return ""

    def _generate_code_summary(self, code: str, language: str) -> str:
        """
        Generate a summary of the code for display purposes.
        
        Args:
            code (str): Full code
            language (str): Programming language
            
        Returns:
            str: Summary of the code
        """
        lines = code.strip().split("\n")
        total_lines = len(lines)
        
        if total_lines <= 10:
            return code
            
        # Extract imports/includes
        import_lines = []
        for line in lines[:20]:  # Check just the first 20 lines
            line = line.strip()
            if language == "python" and (line.startswith("import ") or line.startswith("from ")):
                import_lines.append(line)
            elif language in ["javascript", "typescript"] and (line.startswith("import ") or line.startswith("require(")):
                import_lines.append(line)
            elif language in ["c", "cpp"] and line.startswith("#include"):
                import_lines.append(line)
        
        # Extract function/class definitions
        definitions = []
        definition_patterns = {
            "python": r"^\s*(def|class|async def)\s+\w+",
            "javascript": r"^\s*(function|class|const|let|var)\s+\w+|^\s*\w+\s*=\s*(function|class|=>)",
            "typescript": r"^\s*(function|class|interface|type|const|let|var)\s+\w+|^\s*\w+\s*=\s*(function|class|=>)",
            "java": r"^\s*(public|private|protected|class|interface|enum)\s+\w+",
            "c": r"^\s*\w+\s+\w+\s*\(",
            "cpp": r"^\s*(class|struct|enum|template|namespace)\s+\w+|^\s*\w+\s+\w+\s*\("
        }
        
        pattern = definition_patterns.get(language.lower(), r"^\s*\w+")
        for line in lines:
            if re.match(pattern, line):
                # Truncate long lines
                if len(line) > 80:
                    definitions.append(line[:77] + "...")
                else:
                    definitions.append(line)
                    
        # Build summary
        summary = []
        
        # Add language and total lines
        summary.append(f"// {language.upper()} code - {total_lines} lines total")
        summary.append("")
        
        # Add imports if any
        if import_lines:
            summary.append("// Imports:")
            summary.extend(import_lines[:5])  # Show at most 5 imports
            if len(import_lines) > 5:
                summary.append(f"// ... ({len(import_lines) - 5} more imports)")
            summary.append("")
        
        # Add definitions if any
        if definitions:
            summary.append("// Definitions:")
            summary.extend(definitions[:7])  # Show at most 7 definitions
            if len(definitions) > 7:
                summary.append(f"// ... ({len(definitions) - 7} more definitions)")
                
        # Add note about full code
        summary.append("")
        summary.append(f"// The full code is available in the artifact file")
        
        return "\n".join(summary)


def generate_code_from_input(input_data: CodeGenerationInput) -> Dict[str, Any]:
    """
    Generate code from the CodeGenerationInput.
    
    Args:
        input_data (CodeGenerationInput): Input data for code generation
        
    Returns:
        Dict[str, Any]: Dictionary containing the generated code and other information
    """
    tool = CodeGeneratorTool()
    return tool.run(
        description=input_data.description,
        language=input_data.language,
        output_path=input_data.output_path,
        dependencies=input_data.dependencies,
        template=input_data.template,
        execute_code=input_data.execute_code,
        # Add compatibility with any other fields that might be present
        **{k: v for k, v in input_data.__dict__.items() if k not in [
            'description', 'language', 'output_path', 'dependencies', 'template', 'execute_code'
        ] and not k.startswith('_')}
    )

