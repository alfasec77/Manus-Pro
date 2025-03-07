from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable

from app.logger import get_logger
from app.exceptions import ToolError


class BaseTool(ABC):
    """Base class for all tools in the system."""
    
    def __init__(self, name: str, description: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize a tool.
        
        Args:
            name (str): Tool name
            description (str): Tool description
            parameters (Dict[str, Any], optional): JSON Schema for parameters
        """
        self.name = name
        self.description = description
        self.parameters = parameters or self._default_parameters()
        self.logger = get_logger(f"tool.{name}")
    
    def _default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters schema for the tool.
        Override this in subclasses to provide a specific schema.
        
        Returns:
            Dict[str, Any]: Default parameters schema
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """
        Execute the tool with the given arguments.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Any: Result of the tool execution
        """
        pass
    
    def run(self, **kwargs) -> Any:
        """
        Run the tool with error handling.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Any: Result of the tool execution
        """
        try:
            self.logger.debug(f"Running tool '{self.name}' with args: {kwargs}")
            
            # Special handling for firecrawl_research tool to ensure query parameter is present
            if self.name == "firecrawl_research" and "query" not in kwargs:
                # Check if we have any parameter that could be used as query
                query_param = None
                for param in ['input', 'text', 'content', 'search_query']:
                    if param in kwargs and isinstance(kwargs[param], str):
                        query_param = kwargs.pop(param)
                        self.logger.debug(f"Using '{param}' value as 'query' for firecrawl_research")
                        break
                
                if query_param:
                    kwargs['query'] = query_param
                else:
                    raise ValueError("Missing required parameter 'query' for firecrawl_research tool")
            
            result = self._run(**kwargs)
            self.logger.debug(f"Tool '{self.name}' completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Error running tool '{self.name}': {e}")
            raise ToolError(f"Error running tool '{self.name}': {str(e)}")
    
    def safe_run(self, *args, **kwargs) -> Any:
        """
        Safe run method that can be used with LangChain.
        This handles various ways LangChain might call tools.
        
        Args:
            *args: Positional arguments (could include string input or tool instance)
            **kwargs: Keyword arguments for the tool
            
        Returns:
            Any: Result of the tool execution
        """
        # Log what's being passed for debugging
        self.logger.debug(f"Safe run called with args: {args}, kwargs: {kwargs}")
        
        # Handle parameter name differences for certain tools
        if self.name == "browser":
            # Map search_query to query for browser tool
            if 'search_query' in kwargs and 'query' not in kwargs:
                self.logger.debug(f"Mapping 'search_query' to 'query' for browser tool")
                kwargs['query'] = kwargs.pop('search_query')
            
            # Set default URL if not provided
            if 'url' not in kwargs:
                # Use query as URL if provided, otherwise use a default URL
                if 'query' in kwargs:
                    kwargs['url'] = f"https://www.google.com/search?q={kwargs['query']}"
                    self.logger.debug(f"Setting default URL from query: {kwargs['url']}")
                else:
                    kwargs['url'] = "https://www.google.com"
                    self.logger.debug("Setting default URL to google.com")
                
            # Ensure actions exists and is an empty list if not provided
            if 'actions' not in kwargs:
                kwargs['actions'] = []
                self.logger.debug("Setting default empty actions list")
        
        # Handle 'args' parameter which LangChain sometimes uses
        if 'args' in kwargs:
            args_value = kwargs.pop('args')
            self.logger.debug(f"Found 'args' in kwargs: {args_value}")
            
            # If args is a list with one element and it's a string, use it for content/description
            if isinstance(args_value, list) and len(args_value) == 1 and isinstance(args_value[0], str):
                # Determine parameter name based on tool
                if self.name == "code_generator":
                    kwargs['description'] = args_value[0]
                    kwargs['language'] = 'python'  # Default to Python if not specified
                elif self.name in ["pdf_generator", "markdown_generator"]:
                    kwargs['content'] = args_value[0]
                elif self.name in ["firecrawl_research", "google_search"]:
                    kwargs['query'] = args_value[0]
                elif self.name == "browser":
                    # For browser tool, interpret the string as a URL
                    kwargs['url'] = args_value[0]
                    # Ensure actions exists and is an empty list if not provided
                    if 'actions' not in kwargs:
                        kwargs['actions'] = []
                else:
                    # For unknown tools, try a generic parameter name
                    kwargs['input'] = args_value[0]
        
        # Check for different calling patterns
        if len(args) == 1 and isinstance(args[0], str) and not kwargs:
            # This is the single-string argument case
            self.logger.debug("Single string argument detected, using as content/query")
            
            # Determine what parameter to use based on tool name
            if self.name == "pdf_generator" or self.name == "markdown_generator":
                return self.run(content=args[0])
            elif self.name == "code_generator":
                return self.run(description=args[0], language="python")
            elif self.name in ["firecrawl_research", "google_search"]:
                return self.run(query=args[0])
            elif self.name == "browser":
                # For browser tool, interpret the single string as a URL with no actions
                return self.run(url=args[0], actions=[])
            else:
                # Default for other tools
                return self.run(input=args[0])
        
        # Handle special case for firecrawl_research tool
        if self.name == "firecrawl_research":
            self.logger.debug(f"Handling firecrawl_research tool, kwargs: {kwargs}")
            
            # Check if query parameter is missing but we have another parameter that could be used
            if 'query' not in kwargs:
                potential_query_params = ['input', 'text', 'content', 'search_query', 'question', 'prompt']
                for param in potential_query_params:
                    if param in kwargs and isinstance(kwargs[param], str):
                        self.logger.debug(f"Mapping '{param}' to 'query' for firecrawl_research")
                        kwargs['query'] = kwargs.pop(param)
                        break
                
                # If we still don't have a query parameter but have args, use the first string arg
                if 'query' not in kwargs and len(args) > 0 and isinstance(args[0], str):
                    self.logger.debug(f"Using first positional argument as query for firecrawl_research")
                    kwargs['query'] = args[0]
                
                # If we still don't have a query, ensure we'll raise a clear error
                if 'query' not in kwargs:
                    self.logger.warning(f"No suitable query parameter found for firecrawl_research: {kwargs}")
        
        # For most tools, just use the kwargs
        return self.run(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the tool to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the tool
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    def to_openai_function(self) -> Dict[str, Any]:
        """
        Convert the tool to OpenAI function format.
        
        Returns:
            Dict[str, Any]: OpenAI function representation
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    """Registry for tools in the system."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for tool registry."""
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance.tools = {}
        return cls._instance
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool (BaseTool): Tool to register
        """
        if tool.name in self.tools:
            get_logger("tool_registry").warning(f"Tool '{tool.name}' already registered, overwriting")
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name (str): Tool name
            
        Returns:
            Optional[BaseTool]: The tool if found, None otherwise
        """
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered tools.
        
        Returns:
            List[Dict[str, Any]]: List of tool dictionaries
        """
        return [tool.to_dict() for tool in self.tools.values()]
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self.tools = {}
