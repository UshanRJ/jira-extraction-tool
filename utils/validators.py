"""
Input Validation Module
Provides secure input validation functions
"""

import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error"""
    pass


class InputValidator:
    """Secure input validation"""
    
    # Regex patterns
    PROJECT_KEY_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]{1,9}$')
    ISSUE_KEY_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]+-\d+$')
    
    @staticmethod
    def validate_project_key(project_key: str) -> bool:
        """
        Validate Jira project key format
        
        Args:
            project_key: Project key to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If invalid
        """
        if not project_key:
            raise ValidationError("Project key cannot be empty")
        
        if not InputValidator.PROJECT_KEY_PATTERN.match(project_key):
            raise ValidationError(
                "Invalid project key format. Must be 2-10 uppercase alphanumeric characters."
            )
        
        return True
    
    @staticmethod
    def validate_issue_key(issue_key: str) -> bool:
        """
        Validate Jira issue key format
        
        Args:
            issue_key: Issue key to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If invalid
        """
        if not issue_key:
            raise ValidationError("Issue key cannot be empty")
        
        if not InputValidator.ISSUE_KEY_PATTERN.match(issue_key):
            raise ValidationError(
                "Invalid issue key format. Must be PROJECT-123 format."
            )
        
        return True
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """
        Sanitize text input
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = text.strip()
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            logger.warning(f"Text truncated to {max_length} characters")
        
        return sanitized
    
    @staticmethod
    def validate_list_input(
        items: List[str],
        allowed_values: Optional[List[str]] = None,
        min_items: int = 0,
        max_items: int = 100
    ) -> bool:
        """
        Validate list of values
        
        Args:
            items: List to validate
            allowed_values: List of allowed values (if None, all values allowed)
            min_items: Minimum number of items required
            max_items: Maximum number of items allowed
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If invalid
        """
        if not isinstance(items, list):
            raise ValidationError("Input must be a list")
        
        if len(items) < min_items:
            raise ValidationError(f"At least {min_items} items required")
        
        if len(items) > max_items:
            raise ValidationError(f"Maximum {max_items} items allowed")
        
        if allowed_values:
            invalid_items = [item for item in items if item not in allowed_values]
            if invalid_items:
                raise ValidationError(f"Invalid items: {', '.join(invalid_items)}")
        
        return True
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """
        Validate filename for security
        
        Args:
            filename: Filename to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If invalid
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            raise ValidationError("Invalid filename: path traversal detected")
        
        # Check for allowed extensions
        allowed_extensions = ['.xlsx', '.csv']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            raise ValidationError(f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}")
        
        # Check length
        if len(filename) > 255:
            raise ValidationError("Filename too long")
        
        return True