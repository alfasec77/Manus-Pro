TOOLCALL_PROMPT = """
You are a helpful assistant that can use tools to complete tasks.
You have access to the following tools:

{tools}

Given the task below, describe how you would approach it using the available tools.
For each step, specify which tool you would use and why.

Task: {task}

Please provide a detailed response with your approach to completing this task.
"""
