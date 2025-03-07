from typing import Any, Dict, List, Optional

from app.agent.base import BaseAgent
from app.schema import AgentType, TaskInput, TaskOutput
from app.llm import llm_manager
from app.prompt.toolcall import TOOLCALL_PROMPT


class ToolCallAgent(BaseAgent):
    """
    ToolCall agent that specializes in using tools via function calling.
    """
    
    def __init__(self, tools: Optional[List[str]] = None):
        """
        Initialize the ToolCall agent.
        
        Args:
            tools (List[str], optional): List of tool names to use
        """
        super().__init__(name=AgentType.TOOLCALL.value, tools=tools)
        
        # Define default tools if none provided
        if not tools:
            default_tools = [
                "pdf_generator",
                "markdown_generator",
                "browser",
                "firecrawl_research",
                "code_generator"
            ]
            for tool_name in default_tools:
                self.add_tool(tool_name)
    
    def _run(self, task_input: TaskInput) -> TaskOutput:
        """
        Execute the ToolCall agent with the given task input.
        
        Args:
            task_input (TaskInput): Task input
            
        Returns:
            TaskOutput: Task output
        """
        # This is a placeholder implementation
        # In a real implementation, this would use OpenAI function calling
        # to select and execute tools
        
        self.logger.info(f"ToolCall agent received task: {task_input.task_description}")
        
        # Get available tools
        available_tools = [
            {"name": tool.name, "description": tool.description}
            for tool in self.tools.values()
        ]
        
        # Format prompt with available tools
        tools_text = "\n".join([f"- {t['name']}: {t['description']}" for t in available_tools])
        prompt = TOOLCALL_PROMPT.format(
            task=task_input.task_description,
            tools=tools_text
        )
        
        # Generate response
        response = llm_manager.generate_text(prompt)
        
        # Create output
        output = TaskOutput(
            success=True,
            result=response,
            conversation=task_input.conversation,
            metadata={"tools_available": [t["name"] for t in available_tools]}
        )
        
        return output
