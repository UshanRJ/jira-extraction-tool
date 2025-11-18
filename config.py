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
        self.jira_config: Optional[JiraConfig] = None
        
    def _has_streamlit_secrets(self) -> bool:
        """Check if Streamlit secrets are available"""
        try:
            # Check if we have access to st.secrets and it has content
            if not hasattr(st, 'secrets'):
                return False
            
            # Try to access secrets - if it raises an error, no secrets available
            try:
                _ = dict(st.secrets)
                return len(st.secrets) > 0
            except:
                return False
        except Exception:
            return False
    
    def load_config(self) -> JiraConfig:
        """
        Load configuration with priority:
        1. Streamlit secrets (if available) - for Streamlit Cloud
        2. Environment variables from .env - for local development only
        """
        try:
            # Try Streamlit secrets first (production/cloud deployment)
            if self._has_streamlit_secrets():
                logger.info("Loading configuration from Streamlit secrets")
                return self._load_streamlit_secrets()
            else:
                # Fall back to .env for local development
                logger.info("Loading configuration from .env file (local development)")
                return self._load_env_vars()
        except Exception as e:
            logger.error(f"Configuration loading failed: {str(e)}")
            raise
    
    def _load_streamlit_secrets(self) -> JiraConfig:
        """Load configuration from Streamlit secrets (Streamlit Cloud only)"""
        try:
            # Load from [jira] section in secrets.toml
            if "jira" not in st.secrets:
                raise ValueError(
                    "Missing [jira] section in Streamlit secrets.\n"
                    "Add your Jira configuration in Streamlit Cloud dashboard under Settings > Secrets."
                )
            
            jira_section = st.secrets["jira"]
            
            # Required fields
            cloud_id = jira_section.get("cloud_id")
            project_key = jira_section.get("project_key")
            base_url = jira_section.get("base_url")
            email = jira_section.get("email")
            api_token = jira_section.get("api_token")
            
            # Validate required fields
            missing_fields = []
            if not cloud_id: missing_fields.append("cloud_id")
            if not project_key: missing_fields.append("project_key")
            if not base_url: missing_fields.append("base_url")
            if not email: missing_fields.append("email")
            if not api_token: missing_fields.append("api_token")
            
            if missing_fields:
                raise ValueError(
                    f"Missing required fields in [jira] section: {', '.join(missing_fields)}\n"
                    f"Add these to your Streamlit Cloud secrets."
                )
            
            logger.info(f"Successfully loaded Streamlit secrets for project: {project_key}")
            
            return JiraConfig(
                cloud_id=cloud_id,
                project_key=project_key,
                base_url=base_url,
                email=email,
                api_token=api_token
            )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error reading Streamlit secrets: {str(e)}")
    
    def _load_env_vars(self) -> JiraConfig:
        """Load configuration from .env file (local development only)"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            cloud_id = os.getenv("JIRA_CLOUD_ID")
            project_key = os.getenv("JIRA_PROJECT_KEY")
            base_url = os.getenv("JIRA_BASE_URL")
            email = os.getenv("JIRA_EMAIL")
            api_token = os.getenv("JIRA_API_TOKEN")
            
            # Validate required fields
            missing_vars = []
            if not cloud_id: missing_vars.append("JIRA_CLOUD_ID")
            if not project_key: missing_vars.append("JIRA_PROJECT_KEY")
            if not base_url: missing_vars.append("JIRA_BASE_URL")
            if not email: missing_vars.append("JIRA_EMAIL")
            if not api_token: missing_vars.append("JIRA_API_TOKEN")
            
            if missing_vars:
                raise ValueError(
                    f"Missing required environment variables in .env file:\n"
                    f"  - {chr(10).join(missing_vars)}\n\n"
                    f"📝 Copy .env.example to .env and fill in your Jira credentials.\n"
                    f"📖 See CONFIGURATION_GUIDE.md for setup instructions."
                )
            
            # Type assertion: these are guaranteed non-None after validation
            assert cloud_id is not None
            assert project_key is not None
            assert base_url is not None
            assert email is not None
            assert api_token is not None
            
            logger.info(f"Successfully loaded .env configuration for project: {project_key}")
            
            return JiraConfig(
                cloud_id=cloud_id,
                project_key=project_key,
                base_url=base_url,
                email=email,
                api_token=api_token
            )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error loading .env file: {str(e)}")
    
    def get_config(self) -> JiraConfig:
        """Get current configuration"""
        if self.jira_config is None:
            self.jira_config = self.load_config()
        return self.jira_config


# Global config instance
config_manager = AppConfig()