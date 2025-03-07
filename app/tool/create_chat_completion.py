from typing import Dict, List, Optional, Any, Union

from app.tool.base import BaseTool
from app.exceptions import LLMError
from app.llm import llm_manager
from app.config import config


class CreateChatCompletionTool(BaseTool):
    """Tool for creating chat completions using LLM."""
    
    def __init__(self):
        """Initialize the chat completion tool."""
        super().__init__(
            name="create_chat_completion",
            description="Generate text completions using the LLM"
        )
    
    def _run(self, 
             prompt: Optional[str] = None, 
             system_prompt: Optional[str] = None,
             messages: Optional[List[Dict[str, str]]] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a chat completion using the LLM.
        
        Args:
            prompt (str, optional): User prompt (used if messages not provided)
            system_prompt (str, optional): System prompt (used if messages not provided)
            messages (List[Dict[str, str]], optional): List of message dictionaries
            temperature (float, optional): Temperature for generation
            max_tokens (int, optional): Maximum tokens for generation
            
        Returns:
            Dict[str, Any]: Generated completion
        """
        try:
            # Use either messages or prompt
            if messages:
                # Use provided messages
                result = llm_manager.generate_from_messages(messages)
            else:
                # Use prompt and system_prompt
                if not prompt:
                    raise LLMError("Either 'messages' or 'prompt' must be provided")
                
                result = llm_manager.generate_text(prompt, system_prompt)
            
            # Return formatted result
            return {
                "content": result,
                "success": True
            }
            
        except Exception as e:
            error_msg = f"Failed to create chat completion: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "content": "",
                "success": False,
                "error": str(e)
            }
    
    def create_chat_with_functions(self, 
                                 messages: List[Dict[str, str]], 
                                 functions: List[Dict[str, Any]], 
                                 function_call: Optional[Union[str, Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Create a chat completion with function calling.
        
        Args:
            messages (List[Dict[str, str]]): List of message dictionaries
            functions (List[Dict[str, Any]]): List of function definitions
            function_call (Union[str, Dict[str, str]], optional): Function call instruction
            
        Returns:
            Dict[str, Any]: Generated completion with possible function call
        """
        try:
            # Note: This is a placeholder - in a real implementation, you would use 
            # the OpenAI API's function calling feature. Since we're using a generic
            # LLM wrapper, we'll simulate the function calling behavior.
            
            # Construct a prompt that includes function info
            functions_str = "\n".join([
                f"Function {i+1}: {fn.get('name', 'unknown')}\n"
                f"Description: {fn.get('description', 'No description')}\n"
                f"Parameters: {fn.get('parameters', {})}\n"
                for i, fn in enumerate(functions)
            ])
            
            messages_with_functions = messages.copy()
            if messages[-1]["role"] == "user":
                # Append function information to the user's message
                messages_with_functions[-1]["content"] += (
                    f"\n\nYou have access to the following functions:\n{functions_str}\n"
                    f"To call a function, respond with the function name and parameters in JSON format."
                )
            
            # Generate response
            result = llm_manager.generate_from_messages(messages_with_functions)
            
            # Simple heuristic to detect if the response is a function call
            is_function_call = (
                result.strip().startswith("{") and 
                result.strip().endswith("}") and
                "function" in result.lower()
            )
            
            if is_function_call:
                # Try to parse as a function call
                try:
                    # Extract JSON content if needed
                    json_start = result.find("{")
                    json_end = result.rfind("}") + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        import json
                        function_data = json.loads(result[json_start:json_end])
                        
                        return {
                            "content": None,
                            "function_call": {
                                "name": function_data.get("function", function_data.get("name", "")),
                                "arguments": json.dumps(function_data.get("parameters", function_data.get("arguments", {})))
                            },
                            "success": True
                        }
                except Exception:
                    # If parsing fails, return as regular text
                    pass
            
            # Regular text response
            return {
                "content": result,
                "success": True
            }
            
        except Exception as e:
            error_msg = f"Failed to create chat completion with functions: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "content": "",
                "success": False,
                "error": str(e)
            }


def create_chat_completion(prompt: Optional[str] = None, system_prompt: Optional[str] = None,
                       messages: Optional[List[Dict[str, str]]] = None,
                       temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """
    Create a chat completion using the CreateChatCompletionTool.
    
    Args:
        prompt (str, optional): User prompt (used if messages not provided)
        system_prompt (str, optional): System prompt (used if messages not provided)
        messages (List[Dict[str, str]], optional): List of message dictionaries
        temperature (float, optional): Temperature for generation
        max_tokens (int, optional): Maximum tokens for generation
        
    Returns:
        Dict[str, Any]: Generated completion
    """
    tool = CreateChatCompletionTool()
    return tool.run(
        prompt=prompt,
        system_prompt=system_prompt,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
