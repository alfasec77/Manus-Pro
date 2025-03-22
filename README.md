# OpenManus - Python Agent System
[![Discord](https://img.shields.io/badge/Join-Discord-5865F2?logo=discord&logoColor=white)](https://discord.gg/jkT5udP9bw)
[![Twitter](https://img.shields.io/badge/Follow-@xinyzng-1DA1F2?logo=twitter&logoColor=white)](https://x.com/xinyzng)

ManusPro is an agent-based system that can execute tasks, generate documents, conduct research, and more.

## Demo video
https://github.com/user-attachments/assets/9af20224-d496-4b54-9634-d72c7c8139b7

Checkout the frontend branch:
<img width="1307" alt="image" src="https://github.com/user-attachments/assets/9059d1b4-ba4e-422e-94b3-fee693a3411b" />

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/open-manus.git
cd open-manus/python
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Optional dependencies:
- For generating visualizations in PDFs: `pip install matplotlib numpy`

## Features

- Task planning and execution
- Document generation
  - PDF generation with data tables and visualizations (auto-opens generated PDFs)
  - Markdown generation with auto-open capability
- Web research using Firecrawl API
- Code generation and automatic execution
- Terminal command integration
- Artifact management and tracking
- Conversation handling

## Configuration

Create a `.env` file in the project root with your API keys:

```
OPENAI_API_KEY=your_openai_key
FIRECRAWL_API_KEY=your_firecrawl_key  # For web research capabilities
# Optional: If using Claude
ANTHROPIC_API_KEY=your_anthropic_key
```

## Usage

```python
from app.agent.manus import Manus
import asyncio

# Create Manus agent
agent = Manus()

# Run a task
async def main():
    await agent.run("Generate a report about renewable energy technologies")

if __name__ == "__main__":
    asyncio.run(main())
```

## Document Generation

OpenManus can generate different types of documents:

### PDF Generation

```python
from app.tool.pdf_generator import PDFGeneratorTool

pdf_tool = PDFGeneratorTool()
result = pdf_tool.run(
    content="# This is a PDF report\n\nContent goes here...",
    title="Sample Report",
    options={"auto_open": True}  # Automatically open the PDF after generation
)
print(f"PDF created at: {result['artifact_path']}")
```

### Markdown Generation

```python
from app.tool.markdown_generator import MarkdownGeneratorTool

md_tool = MarkdownGeneratorTool()
result = md_tool.run(
    content="## This is a Markdown document\n\nContent goes here...",
    title="Sample Document",
    options={"auto_open": True}  # Automatically open the markdown file
)
print(f"Markdown created at: {result['artifact_path']}")
```

## Code Generation and Execution

Generate and automatically execute code:

```python
from app.tool.code_generator import CodeGeneratorTool

code_tool = CodeGeneratorTool()
result = code_tool.run(
    description="Create a function that calculates the factorial of a number",
    language="python"  # Code will be auto-executed if it's safe
)
print(f"Code created at: {result['artifact_path']}")
if result.get("executed"):
    print(f"Execution result: {result['execution_result']['output']}")
```

## Web Research

Perform web research using the Firecrawl API:

```python
from app.tool.firecrawl_research import FirecrawlResearchTool

research_tool = FirecrawlResearchTool()
result = research_tool.run(
    query="Latest advancements in quantum computing",
    output_format="markdown",
    include_visualizations=True
)
print(f"Research data saved to: {result['artifact_path']}")
```

## Optional Modules

### Visualization Support

The PDF generator can include data visualizations if matplotlib is installed. To enable this feature:

```bash
pip install matplotlib numpy
```

Without matplotlib, the system will still work but will display a message in the PDF when visualizations are requested.

### Browser Automation

For automating browser tasks, Selenium is used:

```bash
pip install selenium webdriver-manager
```

### Web Research

For web research capabilities, the firecrawl-py package is required:

```bash
pip install firecrawl-py
```

## License

[MIT License](LICENSE)
