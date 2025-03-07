import os
from typing import Dict, List, Any, Optional
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.config import config
from app.logger import get_logger

logger = get_logger("llm")

def get_llm_from_config(config_data: Dict[str, Any] = None) -> BaseChatModel:
    """
    Create a language model instance from configuration.
    
    Args:
        config_data (Dict[str, Any], optional): Configuration dictionary
        
    Returns:
        BaseChatModel: Language model instance
    """
    if config_data is None:
        config_data = config.config_data
    
    # Extract LLM configuration
    api_key = config.get_nested_value(["api", "openai_api_key"])
    model = config.get_nested_value(["llm", "model"], "gpt-4")
    temperature = config.get_nested_value(["llm", "temperature"], 0.7)
    max_tokens = config.get_nested_value(["llm", "max_tokens"], 4000)
    timeout = config.get_nested_value(["llm", "timeout"], 120)
    
    # Check if API key is available
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found in config or environment variables.")
    
    # Initialize OpenAI chat model
    try:
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=api_key,
            request_timeout=timeout,
        )
        return llm
    except Exception as e:
        logger.error(f"Error initializing ChatOpenAI: {e}")
        raise


class LLMManager:
    """Manager for LLM interactions."""
    
    def __init__(self, llm: Optional[BaseChatModel] = None, config_data: Dict[str, Any] = None):
        """
        Initialize LLM manager.
        
        Args:
            llm (BaseChatModel, optional): Language model instance
            config_data (Dict[str, Any], optional): Configuration dictionary
        """
        self.llm = llm or get_llm_from_config(config_data)
        self.logger = get_logger("llm_manager")
    
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text using the LLM.
        
        Args:
            prompt (str): User prompt
            system_prompt (str, optional): System prompt
            
        Returns:
            str: Generated text
        """
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        messages.append(HumanMessage(content=prompt))
        
        try:
            self.logger.debug(f"Sending prompt to LLM: {prompt[:100]}...")
            result = self.llm.invoke(messages)
            return result.content
        except Exception as e:
            self.logger.error(f"Error generating text: {e}")
            return f"Error: {str(e)}"
    
    def generate_from_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate text from a list of messages.
        
        Args:
            messages (List[Dict[str, str]]): List of message dictionaries
            
        Returns:
            str: Generated text
        """
        langchain_messages = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
        
        try:
            self.logger.debug(f"Sending {len(messages)} messages to LLM")
            result = self.llm.invoke(langchain_messages)
            return result.content
        except Exception as e:
            self.logger.error(f"Error generating from messages: {e}")
            return f"Error: {str(e)}"


# Global LLM manager instance
llm_manager = LLMManager()
