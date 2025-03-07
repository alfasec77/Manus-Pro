"""
Tool collection module for registering all available tools in the system.
"""
from app.tool.base import ToolRegistry
from app.logger import get_logger

logger = get_logger("tool_collection")

# Import core tools that should always be available
from app.tool.file_saver import FileSaverTool
try:
    from app.tool.browser_use_tool import BrowserTool
except ImportError:
    logger.warning("Unable to import BrowserTool")
    BrowserTool = None

# Registry singleton
registry = ToolRegistry()

def register_all_tools():
    """Register all available tools in the tool registry."""
    # Clear existing tools to avoid duplicates
    registry.clear()
    
    # Register core tools
    registry.register(FileSaverTool())
    if BrowserTool:
        registry.register(BrowserTool())
    
    # Try to register tools with external dependencies
    try_register_tool("app.tool.pdf_generator", "PDFGeneratorTool")
    try_register_tool("app.tool.markdown_generator", "MarkdownGeneratorTool")
    try_register_tool("app.tool.code_generator", "CodeGeneratorTool")
    try_register_tool("app.tool.firecrawl_research", "FirecrawlResearchTool")
    try_register_tool("app.tool.google_search", "GoogleSearchTool")
    try_register_tool("app.tool.planning", "PlanningTool")
    
    # Log registered tools
    logger.info(f"Registered {len(registry.tools)} tools")
    
    return registry

def try_register_tool(module_path, class_name):
    """Try to import and register a tool, handling any import errors gracefully."""
    try:
        module = __import__(module_path, fromlist=[class_name])
        tool_class = getattr(module, class_name)
        registry.register(tool_class())
        logger.debug(f"Registered tool: {class_name}")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to register {class_name}: {str(e)}")
        
    # Log successful registrations
    if class_name == "CodeGeneratorTool" and class_name in registry.tools:
        logger.info("Successfully registered CodeGeneratorTool")

def get_tool_registry():
    """Get the tool registry with all tools registered."""
    return registry

# Initialize the tool registry when the module is imported
register_all_tools()
