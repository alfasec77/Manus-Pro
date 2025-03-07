"""
Planning tool for generating and executing task plans.
"""
from typing import Any, Dict, List, Optional

from app.tool.base import BaseTool
from app.exceptions import ToolError
from app.llm import llm_manager
from app.prompt.planning import PLANNING_PROMPT


class PlanningTool(BaseTool):
    """Tool for generating and executing task plans."""
    
    def __init__(self):
        """Initialize the planning tool."""
        super().__init__(
            name="planning",
            description="Generate and execute task plans"
        )
    
    def _run(self, 
             task: str,
             max_steps: int = 10,
             generate_only: bool = True) -> Dict[str, Any]:
        """
        Generate a plan for the given task.
        
        Args:
            task (str): Task to plan for
            max_steps (int, optional): Maximum number of steps in the plan
            generate_only (bool, optional): Only generate the plan without executing it
            
        Returns:
            Dict[str, Any]: Generated plan
        """
        try:
            # Generate plan using LLM
            prompt = PLANNING_PROMPT.format(task=task)
            response = llm_manager.generate_text(prompt)
            
            # Parse steps from response
            steps = []
            for line in response.split("\n"):
                line = line.strip()
                if line and (line.startswith("- ") or line.startswith("* ") or 
                             (line[0].isdigit() and line[1] in [".", ")", ":"])):
                    steps.append(line.lstrip("- *0123456789.):").strip())
            
            # Limit steps to max_steps
            steps = steps[:max_steps]
            
            # If generate_only, return the plan without executing
            if generate_only:
                return {
                    "task": task,
                    "plan": steps,
                    "generate_only": generate_only,
                    "num_steps": len(steps)
                }
            
            # Otherwise, execute the plan
            from app.agent.planning import PlanningAgent
            from app.schema import TaskInput, AgentType
            
            # Create planning agent
            planning_agent = PlanningAgent()
            
            # Create task input
            task_input = TaskInput(
                task_description=task,
                agent_type=AgentType.PLANNING,
                parameters={"plan": steps}
            )
            
            # Execute plan
            self.logger.info(f"Executing plan with {len(steps)} steps")
            result = planning_agent.run(task_input)
            
            # Process results
            if result.success:
                # Extract artifact information if available
                artifact_info = {}
                if result.metadata and "artifact_counts" in result.metadata:
                    artifact_info = result.metadata["artifact_counts"]
                
                # Extract generated files if available
                generated_files = []
                if result.metadata and "results" in result.metadata:
                    for step_result in result.metadata["results"]:
                        if isinstance(step_result.get("result"), dict) and "filepath" in step_result["result"]:
                            generated_files.append(step_result["result"]["filepath"])
                
                # Return execution results
                return {
                    "task": task,
                    "plan": steps,
                    "execution_result": result.result,
                    "num_steps": len(steps),
                    "tool_calls": artifact_info.get("tool_calls", 0),
                    "web_sources": artifact_info.get("web_sources", 0),
                    "generated_files": artifact_info.get("generated_files", 0),
                    "file_paths": generated_files
                }
            else:
                raise ToolError(f"Plan execution failed: {result.error}")
            
        except Exception as e:
            error_msg = f"Failed to generate plan: {str(e)}"
            self.logger.error(error_msg)
            raise ToolError(error_msg)
    
    def refine_plan(self, task: str, initial_plan: List[str], feedback: str) -> Dict[str, Any]:
        """
        Refine an existing plan based on feedback.
        
        Args:
            task (str): Original task
            initial_plan (List[str]): Initial plan steps
            feedback (str): Feedback for refinement
            
        Returns:
            Dict[str, Any]: Refined plan
        """
        try:
            # Format initial plan for prompt
            plan_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(initial_plan)])
            
            # Create refinement prompt
            prompt = f"""
            You are a planning assistant that helps refine task plans.
            
            Original Task: {task}
            
            Initial Plan:
            {plan_text}
            
            Feedback: {feedback}
            
            Please provide a revised plan based on the feedback.
            Each step should be clear and actionable.
            """
            
            # Generate refined plan
            response = llm_manager.generate_text(prompt)
            
            # Parse steps from response
            steps = []
            for line in response.split("\n"):
                line = line.strip()
                if line and (line.startswith("- ") or line.startswith("* ") or 
                             (line[0].isdigit() and line[1] in [".", ")", ":"])):
                    steps.append(line.lstrip("- *0123456789.):").strip())
            
            # Return refined plan
            return {
                "task": task,
                "original_plan": initial_plan,
                "refined_plan": steps,
                "feedback": feedback,
                "num_steps": len(steps)
            }
            
        except Exception as e:
            error_msg = f"Failed to refine plan: {str(e)}"
            self.logger.error(error_msg)
            raise ToolError(error_msg)


def generate_plan(task: str, max_steps: int = 10, generate_only: bool = True) -> Dict[str, Any]:
    """
    Generate a plan for the given task using the PlanningTool.
    
    Args:
        task (str): Task to plan for
        max_steps (int, optional): Maximum number of steps in the plan
        generate_only (bool, optional): Only generate the plan without executing it
        
    Returns:
        Dict[str, Any]: Generated plan
    """
    tool = PlanningTool()
    return tool.run(
        task=task,
        max_steps=max_steps,
        generate_only=generate_only
    )
