"""
Jira API Client Module
Handles secure communication with Atlassian Jira API
"""

import requests
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import time
import base64

logger = logging.getLogger(__name__)


class JiraAPIError(Exception):
    """Custom exception for Jira API errors"""
    pass


class JiraClient:
    """Secure Jira API Client with rate limiting and error handling"""
    
    def __init__(self, cloud_id: str, project_key: str, base_url: str, email: Optional[str] = None, api_token: Optional[str] = None):
        self.cloud_id = cloud_id
        self.project_key = project_key
        # Use the direct Jira instance URL, not the api.atlassian.com endpoint
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.rate_limit_delay = 0.5  # seconds between requests
        self.last_request_time = 0
        
        # Setup authentication if credentials provided
        if email and api_token:
            auth_string = f"{email}:{api_token}"
            b64_auth = base64.b64encode(auth_string.encode()).decode()
            self.session.headers.update({
                'Authorization': f'Basic {b64_auth}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            logger.info("Initialized Jira client with API token authentication")
        else:
            logger.warning("Initialized Jira client without authentication - API calls may fail")
        
        logger.info(f"Initialized Jira client for project: {project_key} at {self.base_url}")
    
    def _rate_limit(self):
        """Implement rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response with proper error handling"""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            if response.status_code == 401:
                raise JiraAPIError("Authentication failed. Check your credentials.")
            elif response.status_code == 403:
                raise JiraAPIError("Access forbidden. Check permissions.")
            elif response.status_code == 404:
                raise JiraAPIError("Resource not found.")
            else:
                raise JiraAPIError(f"HTTP {response.status_code}: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise JiraAPIError(f"Network error: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise JiraAPIError("Invalid response from Jira API")
    
    def search_issues(
        self,
        issue_types: List[str],
        statuses: List[str],
        priorities: List[str],
        include_sprint_filter: bool = False,
        filter_clarifications: bool = False,
        summary_search: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search Jira issues with filters
        
        Args:
            issue_types: List of issue types (e.g., ['Bug', 'Task'])
            statuses: List of statuses (e.g., ['To Do', 'Ready for Dev'])
            priorities: List of priorities (e.g., ['P0', 'P1', 'P2'])
            include_sprint_filter: If True, filter for issues without sprint
            filter_clarifications: If True, filter for tasks with clarification in summary
            summary_search: Optional text to search in issue summaries
            max_results: Maximum number of results to return
        
        Returns:
            List of issues
        """
        try:
            # Build JQL query
            jql_parts = [f'project = {self.project_key}']
            
            # Add issue type filter
            if issue_types:
                if len(issue_types) == 1:
                    jql_parts.append(f'type = "{issue_types[0]}"')
                else:
                    types_str = ', '.join([f'"{t}"' for t in issue_types])
                    jql_parts.append(f'type IN ({types_str})')
            
            # Add status filter
            if statuses:
                # Expand "To Do" to include both "01_To Do" and "To Do"
                expanded_statuses = []
                for status in statuses:
                    if status == "To Do":
                        # Add both variants for To Do
                        expanded_statuses.extend(["01_To Do", "To Do"])
                    else:
                        expanded_statuses.append(status)
                
                if len(expanded_statuses) == 1:
                    jql_parts.append(f'status = "{expanded_statuses[0]}"')
                else:
                    statuses_str = ', '.join([f'"{s}"' for s in expanded_statuses])
                    jql_parts.append(f'status IN ({statuses_str})')
            
            # Add priority filter
            if priorities:
                if len(priorities) == 1:
                    jql_parts.append(f'priority = "{priorities[0]}"')
                else:
                    priorities_str = ', '.join([f'"{p}"' for p in priorities])
                    jql_parts.append(f'priority IN ({priorities_str})')
            
            # Add sprint filter
            if include_sprint_filter:
                jql_parts.append('sprint is EMPTY')
            
            # Add custom summary search filter
            if summary_search:
                # Use JQL text search operator (~) for case-insensitive search
                jql_parts.append(f'summary ~ "{summary_search}"')
            
            # Add clarification filter - overrides statuses and types with specific logic
            if filter_clarifications:
                # Remove previous status and type filters
                jql_parts = [part for part in jql_parts if not (part.startswith('status') or part.startswith('type'))]
                # Add specific clarification filter logic
                jql_parts.append('status IN ("01_To Do", "To Do", "Ready For Dev")')
                jql_parts.append('type = Task')
                jql_parts.append('summary ~ "clarification"')
            
            jql = ' AND '.join(jql_parts) + ' ORDER BY ' + ('rank' if filter_clarifications else 'priority ASC, created DESC')
            
            logger.info(f"Executing JQL: {jql}")
            
            # Note: In production with Claude's Atlassian integration,
            # the actual API calls would go through the Atlassian tools
            # This is a reference implementation
            
            return self._execute_jql_search(jql, max_results)
            
        except Exception as e:
            logger.error(f"Issue search failed: {str(e)}")
            raise JiraAPIError(f"Failed to search issues: {str(e)}")
    
    def _execute_jql_search(self, jql: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Execute JQL search using the /rest/api/3/search/jql endpoint
        """
        self._rate_limit()
        
        # Use the /rest/api/3/search/jql endpoint with minimal payload
        url = f"{self.base_url}/rest/api/3/search/jql"
        
        payload = {
            'jql': jql,
            'maxResults': max_results,
            'fields': ['summary', 'status', 'priority', 'reporter', 'parent', 'created']
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            data = self._handle_response(response)
            
            issues = data.get('issues', [])
            logger.info(f"Retrieved {len(issues)} issues from Jira")
            return issues
            
        except Exception as e:
            logger.error(f"JQL search failed: {str(e)}")
            raise
    
    def get_issue_types(self) -> List[str]:
        """Get available issue types for the project"""
        try:
            self._rate_limit()
            
            url = f"{self.base_url}/rest/api/3/project/{self.project_key}"
            response = self.session.get(url, timeout=30)
            data = self._handle_response(response)
            
            issue_types = [it['name'] for it in data.get('issueTypes', [])]
            logger.info(f"Retrieved {len(issue_types)} issue types")
            return issue_types
            
        except Exception as e:
            logger.warning(f"Failed to get issue types from API: {str(e)}")
            # Return default fallback
            return ['Bug', 'Task', 'Story', 'Epic']
    
    def get_statuses(self) -> List[str]:
        """Get available statuses"""
        # Common Jira statuses - can be enhanced to fetch from API
        return [
            'To Do',
            'Ready for Dev',
            'In Progress',
            'Dev in Progress',
            'In Review',
            'Ready for QA',
            'In QA',
            'QA Blocked',
            'Ready for UAT',
            'Done',
            'Closed'
        ]
    
    def get_priorities(self) -> List[str]:
        """Get available priorities"""
        # Common priorities - can be enhanced to fetch from API
        return ['P0', 'P1', 'P2', 'P3', 'P4', 'None']
    
    def get_project_users(self) -> List[str]:
        """Get all users with access to the project by fetching reporters from recent issues"""
        try:
            self._rate_limit()
            
            # Instead of using user/search which has parameter issues,
            # we'll fetch recent issues and extract unique reporters
            # This gives us actual active users on the project
            url = f"{self.base_url}/rest/api/3/search/jql"
            
            payload = {
                'jql': f'project = {self.project_key} ORDER BY created DESC',
                'maxResults': 1000,  # Fetch many issues to get diverse reporters
                'fields': ['reporter']
            }
            
            response = self.session.post(url, json=payload, timeout=30)
            data = self._handle_response(response)
            
            issues = data.get('issues', [])
            
            # Extract unique reporter names
            user_names = set()
            for issue in issues:
                fields = issue.get('fields', {})
                reporter = fields.get('reporter')
                if reporter:
                    display_name = reporter.get('displayName') or reporter.get('name', 'Unknown')
                    if display_name and display_name != 'Unknown':
                        user_names.add(display_name)
            
            # Convert to sorted list
            user_list = sorted(user_names)
            
            # Log the retrieved users for debugging
            logger.info(f"Retrieved {len(user_list)} unique reporters for project {self.project_key}")
            if user_list:
                logger.debug(f"Reporter list: {', '.join(user_list)}")
            
            return user_list if user_list else self._get_default_qa_team()
            
        except Exception as e:
            logger.warning(f"Failed to get project users from API: {str(e)}")
            return self._get_default_qa_team()
    
    def _get_default_qa_team(self) -> List[str]:
        """Return default QA team as fallback"""
        return [
            "Chinthaka Somarathna",
            "Madushika Deshappriya",
            "Pasindu Hashara Liyanage",
            "Rukshani Jayathilaka",
            "Ushan Jayakody"
        ]