class OpenManusError(Exception):
    """Base exception for OpenManus errors."""
    
    def __init__(self, message="An error occurred in OpenManus"):
        self.message = message
        super().__init__(self.message)


class ConfigError(OpenManusError):
    """Exception raised for configuration errors."""
    
    def __init__(self, message="Configuration error"):
        super().__init__(message)


class LLMError(OpenManusError):
    """Exception raised for LLM-related errors."""
    
    def __init__(self, message="LLM error"):
        super().__init__(message)


class ToolError(OpenManusError):
    """Exception raised for tool-related errors."""
    
    def __init__(self, message="Tool error"):
        super().__init__(message)


class AgentError(OpenManusError):
    """Exception raised for agent-related errors."""
    
    def __init__(self, message="Agent error"):
        super().__init__(message)


class BrowserError(OpenManusError):
    """Exception raised for browser automation errors."""
    
    def __init__(self, message="Browser automation error"):
        super().__init__(message)


class DocumentGenerationError(OpenManusError):
    """Exception raised for document generation errors."""
    
    def __init__(self, message="Document generation error"):
        super().__init__(message)


class CodeGenerationError(OpenManusError):
    """Exception raised for code generation errors."""
    
    def __init__(self, message="Code generation error"):
        super().__init__(message)


class WebResearchError(OpenManusError):
    """Exception raised for web research errors."""
    
    def __init__(self, message="Web research error"):
        super().__init__(message)


class APIKeyError(OpenManusError):
    """Exception raised for API key-related errors."""
    
    def __init__(self, message="API key error"):
        super().__init__(message)


class ValidationError(OpenManusError):
    """Exception raised for validation errors."""
    
    def __init__(self, message="Validation error"):
        super().__init__(message)


class FileOperationError(OpenManusError):
    """Exception raised for file operation errors."""
    
    def __init__(self, message="File operation error"):
        super().__init__(message)
