"""
Data Processing Module
Transforms Jira API responses into structured dataframes
"""

import pandas as pd
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DataProcessor:
    """Process and transform Jira data"""
    
    @staticmethod
    def issues_to_dataframe(issues: List[Dict[str, Any]], base_url: str = "") -> pd.DataFrame:
        """
        Convert Jira issues to pandas DataFrame
        
        Args:
            issues: List of Jira issues from API
            
        Returns:
            Formatted DataFrame
        """
        if not issues:
            logger.warning("No issues provided for processing")
            return pd.DataFrame()
        
        processed_data = []
        
        for issue in issues:
            try:
                fields = issue.get('fields', {})
                
                # Extract parent information
                parent = fields.get('parent')
                parent_key = parent.get('key', '') if parent else ''
                parent_summary = parent.get('fields', {}).get('summary', '') if parent else ''
                
                # Extract reporter information
                reporter = fields.get('reporter', {})
                reporter_name = reporter.get('displayName', 'Unknown') if reporter else 'Unknown'
                
                # Extract priority
                priority = fields.get('priority', {})
                priority_name = priority.get('name', 'None') if priority else 'None'
                
                # Extract status
                status = fields.get('status', {})
                status_name = status.get('name', 'Unknown') if status else 'Unknown'
                
                # Extract created date
                created = fields.get('created', '')
                created_date = ''
                if created:
                    try:
                        # Parse ISO format date
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        created_date = dt.strftime('%Y-%m-%d')
                    except:
                        created_date = created[:10] if len(created) >= 10 else ''
                
                # Build Jira URL
                issue_key = issue.get('key', '')
                jira_url = f"{base_url}/browse/{issue_key}" if base_url and issue_key else ''
                
                # Build Epic/Story URL
                epic_url = f"{base_url}/browse/{parent_key}" if base_url and parent_key else ''
                
                processed_data.append({
                    'Epic/Story': parent_key,
                    'Epic URL': epic_url,
                    'Issue key': issue_key,
                    'Issue URL': jira_url,
                    'Summary': fields.get('summary', ''),
                    'Reporter': reporter_name,
                    'Priority': priority_name,
                    'QA Status': status_name,
                    'Created Date': created_date,
                    'Comments': ''
                })
                
            except Exception as e:
                logger.error(f"Error processing issue {issue.get('key', 'unknown')}: {str(e)}")
                continue
        
        if not processed_data:
            logger.warning("No data was successfully processed")
            return pd.DataFrame()
        
        df = pd.DataFrame(processed_data)
        
        # Sort by priority
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3, 'P4': 4, 'None': 5}
        df['priority_sort'] = df['Priority'].map(priority_order).fillna(5)
        df = df.sort_values('priority_sort').drop('priority_sort', axis=1)
        
        logger.info(f"Successfully processed {len(df)} issues")
        return df
    
    @staticmethod
    def get_summary_stats(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics from DataFrame
        
        Args:
            df: Processed DataFrame
            
        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {
                'total_issues': 0,
                'by_priority': {},
                'by_status': {},
                'by_reporter': {}
            }
        
        return {
            'total_issues': len(df),
            'by_priority': df['Priority'].value_counts().to_dict(),
            'by_status': df['QA Status'].value_counts().to_dict(),
            'by_reporter': df['Reporter'].value_counts().to_dict()
        }
    
    @staticmethod
    def filter_dataframe(
        df: pd.DataFrame,
        search_term: Optional[str] = None,
        priorities: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        reporters: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Filter DataFrame based on criteria
        
        Args:
            df: Source DataFrame
            search_term: Text to search in summary
            priorities: List of priorities to include
            statuses: List of statuses to include
            reporters: List of reporters to include
            start_date: Filter issues created on or after this date (YYYY-MM-DD)
            end_date: Filter issues created on or before this date (YYYY-MM-DD)
            
        Returns:
            Filtered DataFrame
        """
        filtered_df = df.copy()
        
        if search_term:
            mask = (
                filtered_df['Summary'].str.contains(search_term, case=False, na=False) |
                filtered_df['Issue key'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        if priorities:
            filtered_df = filtered_df[filtered_df['Priority'].isin(priorities)]
        
        if statuses:
            filtered_df = filtered_df[filtered_df['QA Status'].isin(statuses)]
        
        if reporters:
            filtered_df = filtered_df[filtered_df['Reporter'].isin(reporters)]
        
        # Date filtering
        if start_date and 'Created Date' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Created Date'] >= start_date]
        
        if end_date and 'Created Date' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Created Date'] <= end_date]
        
        return filtered_df
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> bool:
        """
        Validate DataFrame structure
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = [
            'Epic/Story', 'Issue key', 'Summary',
            'Reporter', 'Priority', 'QA Status', 'Comments'
        ]
        
        if df.empty:
            logger.warning("DataFrame is empty")
            return False
        
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        return True