from typing import Any, Dict, List, Optional
import os

from app.agent.base import BaseAgent
from app.schema import AgentType, TaskInput, TaskOutput
from app.llm import llm_manager
from app.prompt.planning import EXECUTION_PROMPT


class PlanningAgent(BaseAgent):
    """
    Planning agent that executes tasks based on a predefined plan.
    """
    
    def __init__(self, tools: Optional[List[str]] = None):
        """
        Initialize the planning agent.
        
        Args:
            tools (List[str], optional): List of tool names to use
        """
        super().__init__(name=AgentType.PLANNING.value, tools=tools)
        
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
        
        # Initialize memory store for artifacts and context
        self.memory = {}
    
    def _execute_plan(self, plan: List[str], task_description: str, 
                     memory_enabled: bool = True, store_artifacts: bool = True,
                     output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a plan step by step with improved context management.
        
        Args:
            plan (List[str]): List of steps in the plan
            task_description (str): Original task description
            memory_enabled (bool): Whether to use memory between steps
            store_artifacts (bool): Whether to store artifacts
            output_path (str, optional): Path for generated outputs
            
        Returns:
            Dict[str, Any]: Results of plan execution
        """
        results = []
        artifact_memory = {} # Memory to pass context between steps
        total_steps = len(plan)
        artifact_counts = {
            "web_sources": 0,
            "generated_files": 0,
            "tool_calls": 0
        }
        
        # Create artifact directory if needed
        artifacts_dir = None
        if output_path and store_artifacts:
            artifacts_dir = output_path
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir, exist_ok=True)
            self.logger.info(f"Storing artifacts in: {artifacts_dir}")
        
        # Format plan for prompt
        plan_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(plan)])
        
        # Display execution information in the terminal
        print(f"\n--- Executing Plan: {total_steps} steps ---")
        
        # Execute each step and collect results
        for i, step in enumerate(plan):
            step_number = i + 1
            print(f"\n[Step {step_number}/{total_steps}] Executing: {step}")
            
            # Generate tool selection for this specific step using LLM with improved context
            memory_context = ""
            if memory_enabled and artifact_memory:
                memory_context = "CONTEXT FROM PREVIOUS STEPS:\n"
                for key, value in artifact_memory.items():
                    if isinstance(value, str) and len(value) < 500:  # Only include reasonable sized content
                        memory_context += f"- {key}: {value}\n"
                    else:
                        memory_context += f"- {key}: [Content available but not shown due to size]\n"
            
            tool_selection_prompt = f"""
            You are executing a specific step in a plan. Choose the most appropriate tool and parameters.
            
            ORIGINAL TASK: {task_description}
            
            COMPLETE PLAN:
            {plan_text}
            
            CURRENT STEP TO EXECUTE: Step {step_number}: {step}
            
            {memory_context}
            
            Available tools: {', '.join(self.tools.keys())}
            
            Tool descriptions:
            {self._get_tool_descriptions()}
            
            Determine which tool should be used to execute this step.
            Respond with just the name of the tool and the parameters needed.
            Format: TOOL_NAME: param1=value1, param2=value2
            
            Choose parameters that will produce a high-quality result.
            """
            
            try:
                # Determine which tool to use
                tool_selection = llm_manager.generate_text(tool_selection_prompt)
                
                # Parse tool selection
                tool_parts = tool_selection.strip().split(':', 1)
                if len(tool_parts) != 2:
                    raise ValueError(f"Invalid tool selection format: {tool_selection}")
                
                tool_name = tool_parts[0].strip().lower()
                params_str = tool_parts[1].strip()
                
                # Check if selected tool exists
                if tool_name not in self.tools:
                    available_tools = list(self.tools.keys())
                    self.logger.warning(f"Selected tool '{tool_name}' not found. Using closest match.")
                    # Find closest match
                    for available_tool in available_tools:
                        if tool_name in available_tool or available_tool in tool_name:
                            tool_name = available_tool
                            break
                    else:
                        # Default to a common tool if no match found
                        if "browser" in self.tools:
                            tool_name = "browser"
                        elif len(available_tools) > 0:
                            tool_name = available_tools[0]
                        else:
                            raise ValueError(f"No available tools to execute step")
                
                self.logger.info(f"[Step {step_number}] Selected tool: {tool_name}")
                
                # Parse parameters for the tool
                params = {}
                if params_str:
                    param_pairs = params_str.split(',')
                    for pair in param_pairs:
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            params[key.strip()] = value.strip().strip('"\'')
                
                # Add task-related parameters with context from memory
                if "task" not in params and "query" not in params and "content" not in params:
                    if tool_name in ["browser", "firecrawl_research"]:
                        # For research tools, focus on the specific step
                        params["query"] = step
                    else:
                        # For generation tools, provide context from memory
                        context = f"{task_description}\n\nStep {step_number}/{total_steps}: {step}"
                        
                        # Add memory context if available and enabled
                        if memory_enabled and artifact_memory:
                            context += "\n\nContext from previous steps:"
                            for key, value in artifact_memory.items():
                                if isinstance(value, str) and len(value) < 1000:
                                    context += f"\n- {key}: {value}"
                                else:
                                    context += f"\n- {key}: [Available but not shown due to size]"
                        
                        params["content"] = context
                
                # If output path specified, add it for generators
                if artifacts_dir and "output_path" not in params and tool_name in ["pdf_generator", "markdown_generator", "code_generator"]:
                    # Create step-specific filename
                    step_filename = f"step_{step_number}_output"
                    if tool_name == "pdf_generator":
                        step_filename += ".pdf"
                    elif tool_name == "markdown_generator":
                        step_filename += ".md"
                    elif tool_name == "code_generator":
                        step_filename += ".py"  # Default to Python, tool might override
                    
                    params["output_path"] = os.path.join(artifacts_dir, step_filename)
                
                # Ensure all generator tools have required content parameter
                generator_tools = ["pdf_generator", "markdown_generator", "code_generator"]
                if tool_name in generator_tools and "content" not in params:
                    self.logger.warning(f"[Step {step_number}] {tool_name} missing 'content' parameter, adding default content")
                    
                    # Generate appropriate content based on tool type
                    content_type = "document"
                    if tool_name == "code_generator":
                        content_type = "code"
                    elif tool_name == "markdown_generator":
                        content_type = "markdown document"
                    
                    # Create content prompt
                    content_prompt = f"""
                    Generate appropriate {content_type} content for this task:
                    
                    TASK: {task_description}
                    CURRENT STEP: {step}
                    
                    The content should be comprehensive, well-structured, and directly address the current step.
                    """
                    
                    try:
                        generated_content = llm_manager.generate_text(content_prompt)
                        params["content"] = generated_content
                    except Exception as content_error:
                        self.logger.error(f"Error generating content: {str(content_error)}")
                        params["content"] = f"{content_type.capitalize()} for: {task_description}\n\nStep: {step}"
                
                # Execute the tool with parameters
                self.logger.info(f"[Step {step_number}] Executing tool {tool_name} with params: {params}")
                print(f"[Step {step_number}/{total_steps}] Running tool: {tool_name}")
                
                # Perform the tool call
                tool = self.tools[tool_name]
                artifact_counts["tool_calls"] += 1
                
                # Track specific types of tools
                if tool_name in ["firecrawl_research", "browser"]:
                    artifact_counts["web_sources"] += 1
                elif tool_name in ["pdf_generator", "markdown_generator", "code_generator"]:
                    artifact_counts["generated_files"] += 1
                
                # Execute tool with better error handling
                tool_result = tool.run(**params)
                
                # Store results in memory if enabled
                if memory_enabled:
                    # Store different aspects depending on tool type
                    if tool_name in ["browser", "firecrawl_research"] and isinstance(tool_result, dict):
                        if "content" in tool_result:
                            artifact_memory[f"step_{step_number}_content"] = tool_result["content"]
                        if "sources" in tool_result:
                            sources = tool_result["sources"]
                            if isinstance(sources, list):
                                artifact_memory[f"step_{step_number}_sources"] = [
                                    s.get("title", "") for s in sources if isinstance(s, dict)
                                ]
                    elif tool_name in ["pdf_generator", "markdown_generator", "code_generator"] and isinstance(tool_result, dict):
                        if "filepath" in tool_result:
                            artifact_memory[f"step_{step_number}_filepath"] = tool_result["filepath"]
                        if "content" in tool_result:
                            artifact_memory[f"step_{step_number}_content"] = tool_result["content"]
                    
                    # Always store the step result summary
                    if isinstance(tool_result, dict) and "summary" in tool_result:
                        artifact_memory[f"step_{step_number}_summary"] = tool_result["summary"]
                    else:
                        # Generate a summary of the step's result if not provided
                        summary_prompt = f"""
                        Provide a brief summary (2-3 sentences) of the following information:
                        
                        {str(tool_result)[:1000] if isinstance(tool_result, str) else str(tool_result)}
                        
                        Focus on extracting the key facts or insights.
                        """
                        try:
                            summary = llm_manager.generate_text(summary_prompt)
                            artifact_memory[f"step_{step_number}_summary"] = summary
                        except Exception as e:
                            self.logger.warning(f"Failed to generate summary: {str(e)}")
                            artifact_memory[f"step_{step_number}_summary"] = "Step completed successfully."
                
                # Log details about the results
                if isinstance(tool_result, dict):
                    if "sources" in tool_result:
                        num_sources = len(tool_result["sources"]) if isinstance(tool_result["sources"], list) else 1
                        print(f"[Step {step_number}/{total_steps}] Retrieved {num_sources} sources")
                        artifact_counts["web_sources"] += num_sources - 1  # -1 because we already counted one
                    
                    if "filepath" in tool_result:
                        print(f"[Step {step_number}/{total_steps}] Generated file: {tool_result['filepath']}")
                
                print(f"[Step {step_number}/{total_steps}] ✓ Completed")
                
                # Add to results
                results.append({
                    "step_number": step_number,
                    "step_description": step,
                    "tool": tool_name,
                    "parameters": params,
                    "result": tool_result,
                    "status": "completed"
                })
            except Exception as e:
                error_msg = f"Error executing step {step_number}: {str(e)}"
                print(f"[Step {step_number}/{total_steps}] ✗ Failed: {error_msg}")
                self.logger.error(error_msg)
                
                # Try to execute using LLM as fallback with memory context
                try:
                    memory_context_str = ""
                    if memory_enabled and artifact_memory:
                        memory_context_str = "Context from previous steps:\n"
                        for key, value in artifact_memory.items():
                            if isinstance(value, str) and len(value) < 500:
                                memory_context_str += f"- {key}: {value}\n"
                            else:
                                memory_context_str += f"- {key}: [Content available but not shown due to size]\n"
                    
                    step_prompt = f"""
                    You are executing a specific step in a plan, but the tool execution failed.
                    
                    ORIGINAL TASK: {task_description}
                    CURRENT STEP TO EXECUTE: Step {step_number}: {step}
                    
                    {memory_context_str}
                    
                    ERROR: {str(e)}
                    
                    Please generate a meaningful response for this step without using tools.
                    Be specific, detailed, and provide actual content that helps accomplish the step.
                    """
                    step_result = llm_manager.generate_text(step_prompt)
                    
                    # Store in memory
                    if memory_enabled:
                        artifact_memory[f"step_{step_number}_fallback"] = step_result
                    
                    results.append({
                        "step_number": step_number,
                        "step_description": step,
                        "result": step_result,
                        "error": error_msg,
                        "status": "fallback_completed"
                    })
                    print(f"[Step {step_number}/{total_steps}] ⚠ Completed with fallback")
                except Exception as fallback_error:
                    results.append({
                        "step_number": step_number,
                        "step_description": step,
                        "result": None,
                        "error": f"{error_msg}\nFallback also failed: {str(fallback_error)}",
                        "status": "failed"
                    })
        
        # Print execution summary
        print(f"\n--- Plan Execution Summary ---")
        print(f"Total steps executed: {total_steps}")
        print(f"Tool calls made: {artifact_counts['tool_calls']}")
        print(f"Web sources fetched: {artifact_counts['web_sources']}")
        print(f"Files generated: {artifact_counts['generated_files']}")
        print(f"--- End of Execution Summary ---\n")
        
        # Generate final summary with memory context
        summary_context = ""
        if memory_enabled and artifact_memory:
            summary_context = "CONTEXT FROM EXECUTION:\n"
            # Only include step summaries to keep it manageable
            for step_num in range(1, total_steps + 1):
                summary_key = f"step_{step_num}_summary"
                if summary_key in artifact_memory:
                    summary_context += f"Step {step_num} summary: {artifact_memory[summary_key]}\n"
        
        # Generate final summary
        summary_prompt = f"""
        Summarize the results of executing this plan:
        
        ORIGINAL TASK: {task_description}
        
        PLAN:
        {plan_text}
        
        {summary_context}
        
        EXECUTION DETAILS:
        - Total steps executed: {total_steps}
        - Tool calls made: {artifact_counts['tool_calls']}
        - Web sources fetched: {artifact_counts['web_sources']}
        - Files generated: {artifact_counts['generated_files']}
        
        Provide a comprehensive summary that includes:
        1. Key information gathered or produced
        2. Specific, factual content that was discovered
        3. Concrete conclusions or answers
        4. What artifacts were created and what they contain
        
        Focus on conveying actual content and knowledge, not just describing the process.
        """
        
        summary = llm_manager.generate_text(summary_prompt)
        print(f"\n--- Plan Execution Complete ---\n")
        
        # If this was a PDF generation task, generate final PDF using memory
        if store_artifacts and memory_enabled and "pdf_generator" in self.tools:
            try:
                # Check if we should generate a final PDF
                pdf_check_prompt = f"""
                Based on this task, should a final PDF be generated to summarize the results?
                
                TASK: {task_description}
                
                Answer with just YES or NO.
                """
                
                should_generate_pdf = llm_manager.generate_text(pdf_check_prompt).strip().upper()
                
                if "YES" in should_generate_pdf:
                    # Create content for final PDF
                    pdf_content_prompt = f"""
                    Create comprehensive, well-formatted content for a final PDF report on this task:
                    
                    TASK: {task_description}
                    
                    EXECUTION SUMMARY:
                    {summary}
                    
                    {summary_context}
                    
                    The content should be professional, well-structured, and ready for PDF generation.
                    Include all key information, findings, analyses, and conclusions.
                    Format with clear headings, bullet points where appropriate, and a logical flow.
                    """
                    
                    pdf_content = llm_manager.generate_text(pdf_content_prompt)
                    
                    # Ensure we actually have content before generating PDF
                    if not pdf_content or len(pdf_content.strip()) < 50:
                        self.logger.warning("Generated PDF content was too short, using fallback content")
                        pdf_content = f"""
                        # Final Report: {task_description}
                        
                        ## Summary
                        {summary}
                        
                        ## Execution Details
                        - Total steps executed: {total_steps}
                        - Tool calls made: {artifact_counts['tool_calls']}
                        - Web sources fetched: {artifact_counts['web_sources']}
                        - Files generated: {artifact_counts['generated_files']}
                        
                        ## Generated Files
                        {', '.join([r.get('filepath', 'Unknown') for r in results if isinstance(r.get('result'), dict) and 'filepath' in r.get('result', {})])}
                        """
                    
                    # Generate final PDF
                    final_pdf_path = os.path.join(artifacts_dir, "final_report.pdf") if artifacts_dir else "final_report.pdf"
                    pdf_tool = self.tools["pdf_generator"]
                    
                    # Make sure we explicitly pass content to avoid the parameter error
                    pdf_result = pdf_tool.run(content=pdf_content, output_path=final_pdf_path)
                    
                    # Add to results
                    if isinstance(pdf_result, dict) and "filepath" in pdf_result:
                        print(f"\nGenerated final report: {pdf_result['filepath']}")
                        
                        # Add to artifact counts
                        artifact_counts["generated_files"] += 1
                        artifact_counts["final_report"] = pdf_result.get("filepath")
                        
                        # Add to results
                        results.append({
                            "step_number": total_steps + 1,
                            "step_description": "Generate final report",
                            "tool": "pdf_generator",
                            "parameters": {"output_path": final_pdf_path, "content": "Final report content (not shown due to size)"},
                            "result": pdf_result,
                            "status": "completed"
                        })
            except Exception as e:
                self.logger.error(f"Error generating final PDF: {str(e)}")
        
        return {
            "plan": plan,
            "execution": summary,
            "results": results,
            "artifact_counts": artifact_counts,
            "memory": artifact_memory if memory_enabled else {}
        }
    
    def _get_tool_descriptions(self) -> str:
        """Get descriptions of all available tools."""
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"{name}: {tool.description}")
        return "\n".join(descriptions)
    
    def _run(self, task_input: TaskInput) -> TaskOutput:
        """
        Execute the planning agent with the given task input.
        
        Args:
            task_input (TaskInput): Task input
            
        Returns:
            TaskOutput: Task output
        """
        # Get plan from parameters or generate one
        plan = task_input.parameters.get("plan", []) if task_input.parameters else []
        
        if not plan:
            self.logger.warning("No plan provided, using default plan")
            plan = [
                "Research and gather information about the task",
                "Process and analyze the information",
                "Generate the requested output"
            ]
        
        # Check for memory and artifact storage settings
        memory_enabled = task_input.parameters.get("memory_enabled", True) if task_input.parameters else True
        store_artifacts = task_input.parameters.get("store_artifacts", True) if task_input.parameters else True
        output_path = task_input.parameters.get("output_path") if task_input.parameters else None
        
        # Execute the plan
        self.logger.info(f"Executing plan with {len(plan)} steps")
        execution_results = self._execute_plan(
            plan=plan,
            task_description=task_input.task_description,
            memory_enabled=memory_enabled,
            store_artifacts=store_artifacts,
            output_path=output_path
        )
        
        # Create output with metadata
        output = TaskOutput(
            success=True,
            result=execution_results["execution"],
            conversation=task_input.conversation,
            metadata=execution_results
        )
        
        return output
