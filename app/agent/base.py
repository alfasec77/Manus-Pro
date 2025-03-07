from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.schema import Conversation, TaskInput, TaskOutput
from app.logger import get_logger
from app.exceptions import AgentError
from app.tool.base import ToolRegistry


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str, tools: Optional[List[str]] = None):
        """
        Initialize an agent.
        
        Args:
            name (str): Agent name
            tools (List[str], optional): List of tool names to use
        """
        self.name = name
        self.logger = get_logger(f"agent.{name}")
        self.tool_registry = ToolRegistry()
        
        # Initialize tools
        self.tools = {}
        if tools:
            for tool_name in tools:
                tool = self.tool_registry.get(tool_name)
                if tool:
                    self.tools[tool_name] = tool
                else:
                    self.logger.warning(f"Tool '{tool_name}' not found in registry")
    
    @abstractmethod
    def _run(self, task_input: TaskInput) -> TaskOutput:
        """
        Execute the agent with the given task input.
        
        Args:
            task_input (TaskInput): Task input
            
        Returns:
            TaskOutput: Task output
        """
        pass
    
    def run(self, task_input: TaskInput) -> TaskOutput:
        """
        Run the agent with error handling.
        
        Args:
            task_input (TaskInput): Task input
            
        Returns:
            TaskOutput: Task output
        """
        try:
            self.logger.info(f"Running agent '{self.name}' with task: {task_input.task_description}")
            
            # Add specific tools if specified in the task input
            if task_input.tools:
                for tool_name in task_input.tools:
                    if tool_name not in self.tools:
                        tool = self.tool_registry.get(tool_name)
                        if tool:
                            self.tools[tool_name] = tool
                            self.logger.debug(f"Added tool '{tool_name}' to agent '{self.name}'")
                        else:
                            self.logger.warning(f"Tool '{tool_name}' not found in registry")
            
            # Execute the agent
            result = self._run(task_input)
            
            self.logger.info(f"Agent '{self.name}' completed task successfully")
            return result
            
        except Exception as e:
            error_msg = f"Error running agent '{self.name}': {str(e)}"
            self.logger.error(error_msg)
            
            # Create error output
            return TaskOutput(
                success=False,
                error=error_msg,
                conversation=task_input.conversation
            )
    
    def get_tool(self, name: str) -> Any:
        """
        Get a tool by name.
        
        Args:
            name (str): Tool name
            
        Returns:
            Any: The tool if found
            
        Raises:
            AgentError: If tool not found
        """
        tool = self.tools.get(name)
        if not tool:
            tool = self.tool_registry.get(name)
            if tool:
                self.tools[name] = tool
            else:
                raise AgentError(f"Tool '{name}' not found")
        return tool
    
    def add_tool(self, tool_name: str) -> bool:
        """
        Add a tool to the agent.
        
        Args:
            tool_name (str): Tool name
            
        Returns:
            bool: True if tool was added, False otherwise
        """
        tool = self.tool_registry.get(tool_name)
        if tool:
            self.tools[tool_name] = tool
            return True
        return False
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all tools available to the agent.
        
        Returns:
            List[Dict[str, Any]]: List of tool dictionaries
        """
        return [tool.to_dict() for tool in self.tools.values()]
