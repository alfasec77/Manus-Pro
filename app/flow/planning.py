from typing import Any, Dict, List, Optional
import re

from app.flow.base import BaseFlow
from app.schema import TaskInput, TaskOutput
from app.agent.planning import PlanningAgent
from app.llm import llm_manager
from app.prompt.planning import PLANNING_PROMPT


class PlanningFlow(BaseFlow):
    """
    Flow for planning and executing tasks using the planning agent.
    """
    
    def __init__(self):
        """Initialize the planning flow."""
        super().__init__(name="planning")
        self.agent = PlanningAgent()
    
    def _generate_plan(self, task_description: str) -> List[str]:
        """
        Generate a detailed, step-by-step plan for the given task.
        
        Args:
            task_description (str): Description of the task
            
        Returns:
            List[str]: List of detailed steps in the plan
        """
        # Generate plan using LLM with improved prompt for more detailed steps
        prompt = f"""
        You are a task planning expert. Create a comprehensive, structured plan to accomplish the following task:
        
        TASK: {task_description}
        
        Your plan should:
        1. Break down the task into logical stages
        2. Include specific, actionable steps for each stage
        3. Specify required dependencies, tools, or resources for each step
        4. Consider potential challenges and alternative approaches
        5. Define clear success criteria for each step
        
        FORMAT GUIDELINES:
        - Use clear, numbered steps (e.g., "1. Research X", "2. Implement Y")
        - Group related steps under descriptive headings
        - Keep each step focused on a single, well-defined action
        - Include estimated complexity/effort for each step (Low/Medium/High)
        - For code-related tasks, specify programming language and key components
        - For document tasks, outline document structure and key sections
        
        Avoid vague steps like "research" without specifying what to research.
        Ensure each step has a clear, measurable outcome.
        """
        
        response = llm_manager.generate_text(prompt)
        
        # Parse steps from response with improved parsing logic
        steps = []
        current_step = ""
        in_step = False
        step_pattern = re.compile(r'^(?:\d+\.|\-|\*)\s+(.+)$')
        
        for line in response.split("\n"):
            line = line.strip()
            if not line:
                continue
                
            # Check for step markers with more robust pattern matching
            step_match = step_pattern.match(line)
            
            if step_match or line.startswith("Step ") or line.upper().startswith("STAGE "):
                # If we were already processing a step, save it
                if in_step and current_step:
                    steps.append(current_step.strip())
                
                # Start a new step
                current_step = line
                in_step = True
            elif in_step:
                # Continue current step
                current_step += "\n" + line
        
        # Add the last step if there is one
        if in_step and current_step:
            steps.append(current_step.strip())
            
        # If no steps were found with the pattern matching, fall back to splitting by newlines
        if not steps and response.strip():
            steps = [line.strip() for line in response.split("\n") if line.strip()]
            
        # Sanitize steps - remove any markdown formatting characters
        sanitized_steps = []
        for step in steps:
            # Remove markdown headers
            step = re.sub(r'^#+\s+', '', step)
            # Remove bullet points if they weren't caught by the main parsing
            step = re.sub(r'^[-*+]\s+', '', step)
            sanitized_steps.append(step)
            
        return sanitized_steps
    
    def _run(self, content: str, output_path: Optional[str] = None, **kwargs) -> TaskOutput:
        """
        Run the planning flow.
        
        Args:
            content (str): Task description
            output_path (Optional[str]): Path to save the output (unused)
            **kwargs: Additional arguments
            
        Returns:
            TaskOutput: Task output containing the plan
        """
        # Generate a plan
        plan = self._generate_plan(content)
        
        # Parse key files needed from the plan (if any)
        files = []
        for step in plan:
            # Extract filenames using regex patterns
            file_patterns = [
                r'Create (?:a|the) file[:\s]+[\'"]?([^\s\'"]+)[\'"]?',
                r'Save (?:to|as) [\'"]?([^\s\'"]+)[\'"]?',
                r'Generate [\'"]?([^\s\'"\.]+\.(?:py|js|html|css|md|json|yaml|txt))[\'"]?',
                r'(?:Edit|Modify|Update) [\'"]?([^\s\'"]+)[\'"]?',
                r'(?:Named|called)[:\s]+[\'"]?([^\s\'"]+\.[a-zA-Z0-9]+)[\'"]?'
            ]
            
            for pattern in file_patterns:
                matches = re.findall(pattern, step)
                files.extend(matches)
        
        # Remove duplicates
        files = list(set(files))
        
        # Create summary
        summary = f"## Task Planning Summary\n\n"
        summary += f"**Task:** {content}\n\n"
        summary += f"### Plan\n\n"
        summary += self._format_plan_for_summary(plan)
        
        if files:
            summary += f"\n### Key Files\n\n"
            summary += self._format_files_for_summary(files)
            
        # Create output with the plan
        output = TaskOutput(
            content=summary,
            result={
                "plan": plan,
                "files": files,
                "summary": summary
            },
            status="success"
        )
        
        self.logger.info(f"Generated plan with {len(plan)} steps")
        return output
    
    def _format_plan_for_summary(self, plan: List[str]) -> str:
        """Format the plan for inclusion in the summary."""
        return "\n".join([f"- {step}" for step in plan])
    
    def _format_files_for_summary(self, files: List[str]) -> str:
        """Format the files list for inclusion in the summary."""
        return "\n".join([f"- `{file}`" for file in files])
