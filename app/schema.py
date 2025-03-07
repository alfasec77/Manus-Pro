from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of agents available in the system."""
    MANUS = "manus"
    REACT = "react"
    PLANNING = "planning"
    SWE = "swe"
    TOOLCALL = "toolcall"


class ToolType(str, Enum):
    """Types of tools available in the system."""
    PDF_GENERATOR = "pdf_generator"
    MARKDOWN_GENERATOR = "markdown_generator"
    CODE_GENERATOR = "code_generator"
    BROWSER = "browser"
    FIRECRAWL = "firecrawl"
    BASH = "bash"
    PYTHON_EXECUTE = "python_execute"
    FILE_SAVER = "file_saver"
    GOOGLE_SEARCH = "google_search"
    CREATE_CHAT_COMPLETION = "create_chat_completion"
    STR_REPLACE_EDITOR = "str_replace_editor"
    TERMINATE = "terminate"


class DocumentFormat(str, Enum):
    """Document formats supported by generators."""
    PDF = "pdf"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


class WebDriverType(str, Enum):
    """Web browsers supported by Selenium."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"


class Message(BaseModel):
    """A message in a conversation."""
    role: str = Field(..., description="Role of the message sender (system, user, assistant)")
    content: str = Field(..., description="Content of the message")


class Conversation(BaseModel):
    """A conversation consisting of messages."""
    messages: List[Message] = Field(default_factory=list, description="List of messages in the conversation")


class TaskInput(BaseModel):
    """Input for a task to be executed by the agent."""
    task_description: str = Field(..., description="Natural language description of the task")
    conversation: Optional[Conversation] = Field(None, description="Optional conversation context")
    tools: Optional[List[str]] = Field(None, description="Optional list of tools to use")
    agent_type: Optional[AgentType] = Field(None, description="Type of agent to use")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters for the task")


class WebResearchInput(BaseModel):
    """Input for web research tasks."""
    query: str = Field(..., description="Research query or URL to crawl")
    output_format: Optional[DocumentFormat] = Field(DocumentFormat.MARKDOWN, description="Format for the research output")
    max_depth: Optional[int] = Field(1, description="Maximum depth for web crawling")
    max_pages: Optional[int] = Field(10, description="Maximum number of pages to crawl")
    include_visualizations: Optional[bool] = Field(True, description="Whether to include visualization suggestions")


class BrowserTaskInput(BaseModel):
    """Input for browser automation tasks."""
    url: str = Field(..., description="URL to navigate to")
    actions: List[Dict[str, Any]] = Field(..., description="List of actions to perform")
    webdriver: Optional[WebDriverType] = Field(WebDriverType.CHROME, description="Web driver to use")
    headless: Optional[bool] = Field(True, description="Whether to run the browser in headless mode")
    timeout: Optional[int] = Field(30, description="Timeout for browser actions in seconds")
    query: Optional[str] = Field(None, description="Search query parameter (will navigate to search engine with this query)")


class CodeGenerationInput(BaseModel):
    """Input for code generation tasks."""
    description: str = Field(..., description="Description of the code to generate")
    language: str = Field(..., description="Programming language for the code")
    output_path: Optional[str] = Field(None, description="Optional output path for the code")
    dependencies: Optional[List[str]] = Field(None, description="Optional list of dependencies")
    template: Optional[str] = Field(None, description="Optional template for the code")
    save_as_artifact: Optional[bool] = Field(True, description="Whether to save the code as an artifact")
    execute_code: Optional[bool] = Field(True, description="Whether to execute the generated code")


class TaskOutput(BaseModel):
    """Output from a task execution."""
    success: bool = Field(..., description="Whether the task was successful")
    result: Optional[Any] = Field(None, description="Result of the task")
    error: Optional[str] = Field(None, description="Error message if task failed")
    conversation: Optional[Conversation] = Field(None, description="Updated conversation after task execution")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata about the task execution")


class VisualizationData(BaseModel):
    """Data for a visualization."""
    title: str = Field(..., description="Title of the visualization")
    visualization_type: str = Field(..., description="Type of visualization (e.g., bar_chart, line_chart)")
    description: Optional[str] = Field(None, description="Description of what this visualization shows")
    data: Dict[str, Any] = Field(..., description="Data for the visualization")
    x_axis: Optional[str] = Field(None, description="Label for the x-axis")
    y_axis: Optional[str] = Field(None, description="Label for the y-axis")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options for the visualization")


class DataTable(BaseModel):
    """Representation of a data table."""
    title: str = Field(..., description="Title of the table")
    description: Optional[str] = Field(None, description="Description of what this table represents")
    columns: List[str] = Field(..., description="Column headers for the table")
    rows: List[List[Any]] = Field(..., description="Data rows for the table")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the table")


class DocumentGenerationOptions(BaseModel):
    """Options for document generation."""
    include_table_of_contents: Optional[bool] = Field(True, description="Whether to include a table of contents")
    include_cover_page: Optional[bool] = Field(True, description="Whether to include a cover page")
    include_visualizations: Optional[bool] = Field(True, description="Whether to include visualizations")
    include_data_tables: Optional[bool] = Field(True, description="Whether to include data tables")
    include_sources: Optional[bool] = Field(True, description="Whether to include sources")
    template: Optional[str] = Field(None, description="Template to use for the document")
    style: Optional[Dict[str, Any]] = Field(None, description="Style options for the document")


class GenerateDocumentInput(BaseModel):
    """Input for document generation tasks."""
    content: str = Field(..., description="Content to be included in the document")
    format: DocumentFormat = Field(..., description="Format of the document to generate")
    output_path: Optional[str] = Field(None, description="Optional output path for the document")
    title: Optional[str] = Field(None, description="Optional title for the document")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for the document")
    visualizations: Optional[List[VisualizationData]] = Field(None, description="List of visualizations to include")
    data_tables: Optional[List[DataTable]] = Field(None, description="List of data tables to include")
    options: Optional[DocumentGenerationOptions] = Field(None, description="Options for document generation")
