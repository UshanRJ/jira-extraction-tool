"""
Configuration Management Module
Handles secure configuration for both local and Streamlit deployment
"""

import os
import streamlit as st
from typing import Optional
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


class JiraConfig(BaseModel):
    """Jira Configuration Model with validation"""
    
    cloud_id: str = Field(..., min_length=1, description="Atlassian Cloud ID")
    project_key: str = Field(..., min_length=1, max_length=10, description="Jira Project Key")
    base_url: str = Field(..., description="Jira Base URL")
    email: Optional[str] = Field(None, description="Jira user email for API authentication")
    api_token: Optional[str] = Field(None, description="Jira API token")
    
    @validator('project_key')
    def validate_project_key(cls, v):
        """Validate project key format"""
        if not v.isupper():
            raise ValueError("Project key must be uppercase")
        if not v.replace('_', '').isalnum():
            raise ValueError("Project key must be alphanumeric")
        return v
    
    @validator('base_url')
    def validate_url(cls, v):
        """Validate URL format"""
        if not v.startswith('https://'):
            raise ValueError("Base URL must use HTTPS")
        return v.rstrip('/')


class AppConfig:
    """Application Configuration Manager"""
    
    def __init__(self):
        self.is_streamlit = self._check_streamlit_env()
        self.jira_config: Optional[JiraConfig] = None
        
    def _check_streamlit_env(self) -> bool:
        """Check if running in Streamlit environment"""
        try:
            # Avoid statically importing Streamlit's internal module (which many linters/IDEs flag);
            # dynamically import the script_run_context module and call get_script_run_ctx if available.
            import importlib
            module = importlib.import_module("streamlit.runtime.scriptrunner.script_run_context")
            get_ctx = getattr(module, "get_script_run_ctx", None)
            if callable(get_ctx):
                return get_ctx() is not None
            return False
        except Exception:
            return False
    
    def load_config(self) -> JiraConfig:
        """Load configuration from appropriate source"""
        try:
            if self.is_streamlit:
                return self._load_streamlit_secrets()
            else:
                return self._load_env_vars()
        except Exception as e:
            logger.error(f"Configuration loading failed: {str(e)}")
            raise
    
    def _load_streamlit_secrets(self) -> JiraConfig:
        """Load configuration from Streamlit secrets"""
        try:
            # Try loading from [jira] section first, then fall back to root level
            jira_section = st.secrets.get("jira", {})
            
            cloud_id = jira_section.get("cloud_id")
            project_key = jira_section.get("project_key")
            base_url = jira_section.get("base_url")
            email = jira_section.get("email") or st.secrets.get("JIRA_EMAIL")
            api_token = jira_section.get("api_token") or st.secrets.get("JIRA_API_TOKEN")
            
            if not all([cloud_id, project_key, base_url]):
                raise ValueError("Missing required Jira configuration in secrets.toml")
            
            return JiraConfig(
                cloud_id=cloud_id,
                project_key=project_key,
                base_url=base_url,
                email=email,
                api_token=api_token
            )
        except KeyError as e:
            raise ValueError(f"Missing required secret: {e}")
        except Exception as e:
            raise ValueError(f"Error loading secrets: {e}")
    
    def _load_env_vars(self) -> JiraConfig:
        """Load configuration from environment variables"""
        from dotenv import load_dotenv
        load_dotenv()
        
        cloud_id = os.getenv("JIRA_CLOUD_ID")
        project_key = os.getenv("JIRA_PROJECT_KEY")
        base_url = os.getenv("JIRA_BASE_URL")
        email = os.getenv("JIRA_EMAIL")
        api_token = os.getenv("JIRA_API_TOKEN")
        
        if not all([cloud_id, project_key, base_url]):
            missing_vars = []
            if not cloud_id: missing_vars.append("JIRA_CLOUD_ID")
            if not project_key: missing_vars.append("JIRA_PROJECT_KEY")
            if not base_url: missing_vars.append("JIRA_BASE_URL")
            
            raise ValueError(
                f"Missing required environment variables in .env file: {', '.join(missing_vars)}\n"
                f"Copy .env.example to .env and fill in your credentials."
            )
        
        # Narrow types for the type checker: these are guaranteed non-None due to the check above
        assert cloud_id is not None and project_key is not None and base_url is not None
        
        return JiraConfig(
            cloud_id=cloud_id,
            project_key=project_key,
            base_url=base_url,
            email=email,
            api_token=api_token
        )
    
    def get_config(self) -> JiraConfig:
        """Get current configuration"""
        if self.jira_config is None:
            self.jira_config = self.load_config()
        return self.jira_config


# Global config instance
config_manager = AppConfig()