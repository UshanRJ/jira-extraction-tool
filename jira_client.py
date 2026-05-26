"""
Jira API Client Module
Handles secure communication with Atlassian Jira API
"""

import requests
from typing import List, Dict, Any, Optional
import logging
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

    @staticmethod
    def _escape_jql_value(value: str) -> str:
        """Escape a string for safe insertion into a quoted JQL value."""
        return value.replace('\\', '\\\\').replace('"', '\\"')

    def _append_equals_clause(self, jql_parts: List[str], field_name: str, values: List[str]) -> None:
        """Append a JQL equality or IN clause for a list of values."""
        escaped_values = [self._escape_jql_value(value) for value in values]
        if len(escaped_values) == 1:
            jql_parts.append(f'{field_name} = "{escaped_values[0]}"')
        else:
            values_str = ', '.join([f'"{value}"' for value in escaped_values])
            jql_parts.append(f'{field_name} IN ({values_str})')

    def _append_date_clause(self, jql_parts: List[str], start_date: Optional[str], end_date: Optional[str]) -> None:
        """Append created date bounds to the JQL query."""
        if start_date:
            jql_parts.append(f'created >= "{start_date}"')
        if end_date:
            jql_parts.append(f'created <= "{end_date}"')
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response with proper error handling"""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            error_body = response.text.strip()
            if error_body:
                logger.error(f"Jira error response body: {error_body}")
            if response.status_code == 401:
                raise JiraAPIError("Authentication failed. Check your credentials.")
            elif response.status_code == 403:
                raise JiraAPIError("Access forbidden. Check permissions.")
            elif response.status_code == 404:
                raise JiraAPIError("Resource not found.")
            else:
                detail = error_body if error_body else str(e)
                raise JiraAPIError(f"HTTP {response.status_code}: {detail}")
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
        max_results: int = 100,
        reporters: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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
            reporters: Optional list of reporter display names
            start_date: Optional created date lower bound (YYYY-MM-DD)
            end_date: Optional created date upper bound (YYYY-MM-DD)
        
        Returns:
            List of issues
        """
        try:
            # Build JQL query
            jql_parts = [f'project = {self.project_key}']
            
            # Add issue type filter
            if issue_types:
                self._append_equals_clause(jql_parts, 'type', issue_types)
            
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

                self._append_equals_clause(jql_parts, 'status', expanded_statuses)
            
            # Add priority filter
            if priorities:
                self._append_equals_clause(jql_parts, 'priority', priorities)
            
            # Add reporter filter in JQL so it is applied before max_results cap
            if reporters:
                self._append_equals_clause(jql_parts, 'reporter', reporters)

            # Add sprint filter
            if include_sprint_filter:
                jql_parts.append('sprint is EMPTY')

            # Add created date bounds directly to JQL so the API returns the full matching set
            self._append_date_clause(jql_parts, start_date, end_date)
            
            # Add custom summary search filter
            if summary_search:
                # Use JQL text search operator (~) for case-insensitive search
                jql_parts.append(f'summary ~ "{self._escape_jql_value(summary_search)}"')
            
            # Add clarification filter - overrides statuses, types, and summary with specific logic
            if filter_clarifications:
                # Remove previous status, type, and summary filters to avoid conflicting conditions
                jql_parts = [part for part in jql_parts if not (
                    part.startswith('status') or
                    part.startswith('type') or
                    part.startswith('summary')
                )]
                # Add specific clarification filter logic
                jql_parts.append('status IN ("01_To Do", "To Do", "Ready for Dev", "Ready For Dev")')
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
    
    def _execute_jql_search(self, jql: str, max_results: Optional[int] = None, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Execute JQL search using the /rest/api/3/search/jql endpoint with query parameters
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        selected_fields = fields or ['summary', 'status', 'priority', 'reporter', 'parent', 'created']
        collected_issues: List[Dict[str, Any]] = []
        page_size = 100
        start_at = 0

        try:
            while max_results is None or len(collected_issues) < max_results:
                self._rate_limit()

                params = {
                    'jql': jql,
                    'startAt': start_at,
                    'maxResults': page_size,
                    'fields': ','.join(selected_fields)
                }

                response = self.session.get(url, params=params, timeout=30)
                data = self._handle_response(response)

                issues = data.get('issues', [])
                collected_issues.extend(issues)

                total = data.get('total')
                logger.info(
                    f"Retrieved {len(issues)} issues from Jira (startAt={start_at}, total={total if total is not None else 'unknown'})"
                )

                if not issues:
                    break

                if len(issues) < page_size:
                    break

                start_at += len(issues)

            if max_results is not None and len(collected_issues) > max_results:
                collected_issues = collected_issues[:max_results]

            logger.info(f"Retrieved {len(collected_issues)} issues from Jira in total")
            return collected_issues
            
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
        try:
            self._rate_limit()

            url = f"{self.base_url}/rest/api/3/project/{self.project_key}/statuses"
            response = self.session.get(url, timeout=30)
            data = self._handle_response(response)

            status_names = []
            for issue_type_entry in data:
                for status in issue_type_entry.get('statuses', []):
                    name = status.get('name')
                    if name and name not in status_names:
                        status_names.append(name)

            if status_names:
                logger.info(f"Retrieved {len(status_names)} project statuses")
                return status_names

        except Exception as e:
            logger.warning(f"Failed to get statuses from API: {str(e)}")

        # Common Jira statuses as fallback
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
        """Get all users with access to the project using the project members endpoint"""
        try:
            # First, try fetching from project members endpoint (most reliable)
            url = f"{self.base_url}/rest/api/3/project/{self.project_key}/members"
            all_members = []
            start_at = 0
            page_size = 100
            
            while True:
                self._rate_limit()
                params = {
                    'startAt': start_at,
                    'maxResults': page_size
                }
                response = self.session.get(url, params=params, timeout=30)
                
                try:
                    data = self._handle_response(response)
                except Exception as e:
                    logger.warning(f"Failed to fetch project members from members endpoint: {str(e)}")
                    # Fall back to fetching reporters from issues
                    return self._get_reporters_from_issues()
                
                members = data.get('values', [])
                all_members.extend(members)
                
                if len(members) < page_size:
                    break
                
                start_at += page_size
            
            # Extract user display names
            user_names = set()
            for member in all_members:
                displayName = member.get('displayName')
                if displayName:
                    user_names.add(displayName)
            
            user_list = sorted(user_names)
            logger.info(f"Retrieved {len(user_list)} project members for {self.project_key}")
            
            return user_list if user_list else self._get_default_qa_team()
            
        except Exception as e:
            logger.warning(f"Failed to get project members: {str(e)}")
            # Fall back to fetching reporters from issues
            return self._get_reporters_from_issues()
    
    def _get_reporters_from_issues(self) -> List[str]:
        """Fallback: Get all unique reporters from all project issues"""
        try:
            logger.info("Falling back to fetching reporters from project issues...")
            # Fetch all issues with reporter field to get unique reporters
            issues = self._execute_jql_search(
                f'project = {self.project_key} ORDER BY created DESC',
                max_results=None,
                fields=['reporter']
            )
            
            # Extract unique reporter names
            user_names = set()
            for issue in issues:
                fields = issue.get('fields', {})
                reporter = fields.get('reporter')
                if reporter:
                    display_name = reporter.get('displayName') or reporter.get('name', 'Unknown')
                    if display_name and display_name != 'Unknown':
                        user_names.add(display_name)
            
            user_list = sorted(user_names)
            logger.info(f"Retrieved {len(user_list)} unique reporters from project issues")
            
            return user_list if user_list else self._get_default_qa_team()
            
        except Exception as e:
            logger.warning(f"Failed to get reporters from issues: {str(e)}")
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