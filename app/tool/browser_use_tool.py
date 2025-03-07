import os
import time
from typing import Any, Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.safari.service import Service as SafariService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from app.tool.base import BaseTool
from app.schema import BrowserTaskInput, WebDriverType
from app.exceptions import BrowserError
from app.config import config


class BrowserTool(BaseTool):
    """Tool for automating browser tasks using Selenium."""
    
    def __init__(self):
        """Initialize the browser tool."""
        super().__init__(
            name="browser",
            description="Automate browser tasks using Selenium",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to (required)"
                    },
                    "actions": {
                        "type": "array",
                        "description": "List of actions to perform (required)",
                        "items": {
                            "type": "object"
                        }
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (will create a search URL if provided)"
                    },
                    "webdriver": {
                        "type": "string",
                        "description": "Web driver to use (chrome, firefox, edge, safari)",
                        "default": "chrome"
                    },
                    "headless": {
                        "type": "boolean",
                        "description": "Whether to run in headless mode",
                        "default": True
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 30
                    }
                },
                "required": ["url", "actions"]
            }
        )
        self.driver = None
    
    def _initialize_driver(self, webdriver_type: str, headless: bool) -> None:
        """
        Initialize the web driver.
        
        Args:
            webdriver_type (str): Type of web driver to use
            headless (bool): Whether to run the browser in headless mode
        """
        try:
            if webdriver_type.lower() == WebDriverType.CHROME.value:
                options = webdriver.ChromeOptions()
                if headless:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                self.driver = webdriver.Chrome(
                    service=ChromeService(ChromeDriverManager().install()),
                    options=options
                )
            elif webdriver_type.lower() == WebDriverType.FIREFOX.value:
                options = webdriver.FirefoxOptions()
                if headless:
                    options.add_argument("--headless")
                self.driver = webdriver.Firefox(
                    service=FirefoxService(GeckoDriverManager().install()),
                    options=options
                )
            elif webdriver_type.lower() == WebDriverType.EDGE.value:
                options = webdriver.EdgeOptions()
                if headless:
                    options.add_argument("--headless")
                self.driver = webdriver.Edge(
                    service=EdgeService(EdgeChromiumDriverManager().install()),
                    options=options
                )
            elif webdriver_type.lower() == WebDriverType.SAFARI.value:
                self.driver = webdriver.Safari(service=SafariService())
            else:
                raise BrowserError(f"Unsupported web driver type: {webdriver_type}")
            
            # Set timeout
            self.driver.set_page_load_timeout(60)
            
        except Exception as e:
            raise BrowserError(f"Failed to initialize web driver: {str(e)}")
    
    def _find_element(self, by_type: str, selector: str, timeout: int = 10) -> Any:
        """
        Find an element on the page.
        
        Args:
            by_type (str): Type of selector (e.g., "id", "xpath", "css")
            selector (str): Selector value
            timeout (int, optional): Timeout in seconds
            
        Returns:
            Any: Found element
        """
        by_map = {
            "id": By.ID,
            "name": By.NAME,
            "xpath": By.XPATH,
            "css": By.CSS_SELECTOR,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME,
            "link_text": By.LINK_TEXT,
            "partial_link_text": By.PARTIAL_LINK_TEXT,
        }
        
        by_value = by_map.get(by_type.lower())
        if not by_value:
            raise BrowserError(f"Invalid selector type: {by_type}")
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by_value, selector))
            )
            return element
        except TimeoutException:
            raise BrowserError(f"Timed out waiting for element with {by_type}='{selector}'")
    
    def _perform_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """
        Perform a browser action.
        
        Args:
            action_type (str): Type of action to perform
            params (Dict[str, Any]): Action parameters
            
        Returns:
            Any: Result of the action
        """
        # Navigation actions
        if action_type == "navigate":
            url = params.get("url")
            if not url:
                raise BrowserError("URL is required for navigate action")
            self.driver.get(url)
            return {"status": "success", "message": f"Navigated to {url}"}
        
        # Click actions
        elif action_type == "click":
            by_type = params.get("by", "css")
            selector = params.get("selector")
            if not selector:
                raise BrowserError("Selector is required for click action")
            
            element = self._find_element(by_type, selector)
            element.click()
            return {"status": "success", "message": f"Clicked element {by_type}='{selector}'"}
        
        # Input actions
        elif action_type == "input":
            by_type = params.get("by", "css")
            selector = params.get("selector")
            text = params.get("text", "")
            clear = params.get("clear", True)
            
            if not selector:
                raise BrowserError("Selector is required for input action")
            
            element = self._find_element(by_type, selector)
            if clear:
                element.clear()
            element.send_keys(text)
            return {"status": "success", "message": f"Input text into {by_type}='{selector}'"}
        
        # Scroll actions
        elif action_type == "scroll":
            x = params.get("x", 0)
            y = params.get("y", 0)
            self.driver.execute_script(f"window.scrollTo({x}, {y});")
            return {"status": "success", "message": f"Scrolled to position ({x}, {y})"}
        
        # Wait actions
        elif action_type == "wait":
            seconds = params.get("seconds", 1)
            time.sleep(seconds)
            return {"status": "success", "message": f"Waited for {seconds} seconds"}
        
        # Get text action
        elif action_type == "get_text":
            by_type = params.get("by", "css")
            selector = params.get("selector")
            
            if not selector:
                raise BrowserError("Selector is required for get_text action")
            
            element = self._find_element(by_type, selector)
            text = element.text
            return {"status": "success", "text": text}
        
        # Screenshot action
        elif action_type == "screenshot":
            path = params.get("path", "screenshot.png")
            self.driver.save_screenshot(path)
            return {"status": "success", "message": f"Screenshot saved to {path}"}
        
        # Execute JavaScript action
        elif action_type == "execute_script":
            script = params.get("script")
            if not script:
                raise BrowserError("Script is required for execute_script action")
            
            result = self.driver.execute_script(script)
            return {"status": "success", "result": result}
        
        else:
            raise BrowserError(f"Unsupported action type: {action_type}")
    
    def _run(self, **kwargs) -> Any:
        """
        This method has been removed.
        
        Args:
            **kwargs: Tool-specific arguments (ignored)
            
        Returns:
            Dict: A message indicating this tool has been disabled
        """
        self.logger.warning("BrowserTool._run has been removed/disabled")
        return {
            "status": "error",
            "message": "The browser tool functionality has been removed. Please use an alternative tool."
        }


def execute_browser_task(input_data: BrowserTaskInput) -> List[Dict[str, Any]]:
    """
    This function previously executed a browser task from BrowserTaskInput,
    but the browser tool functionality has been removed.
    
    Args:
        input_data (BrowserTaskInput): Input data for browser task
        
    Returns:
        List[Dict[str, Any]]: Error message indicating removal
    """
    return [{
        "status": "error",
        "message": "The browser tool functionality has been removed. Please use an alternative tool."
    }]
