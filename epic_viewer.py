"""
Epic Hierarchy Viewer Module
Handles display and filtering of Jira epics with their linked issues and subtasks
"""

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from jira_client import JiraClient, JiraAPIError

logger = logging.getLogger(__name__)


def flatten_epic_data(epic_hierarchy: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Flatten the nested epic hierarchy into a DataFrame for easier filtering and display.
    
    Args:
        epic_hierarchy: List of epic dictionaries with nested issues and subtasks
    
    Returns:
        DataFrame with columns: Epic, Epic_Key, Epic_Priority, Epic_Status, 
                               Issue, Issue_Key, Issue_Type, Issue_Priority, Issue_Status, Issue_Assignee,
                               Subtask, Subtask_Key, Subtask_Priority, Subtask_Status, Subtask_Assignee
    """
    rows = []
    
    for epic in epic_hierarchy:
        if not epic.get('linked_issues'):
            # Epic with no linked issues
            rows.append({
                'Epic': epic['summary'],
                'Epic_Key': epic['key'],
                'Epic_Priority': epic['priority'],
                'Epic_Status': epic['status'],
                'Epic_Assignee': epic['assignee'],
                'Issue': None,
                'Issue_Key': None,
                'Issue_Type': None,
                'Issue_Priority': None,
                'Issue_Status': None,
                'Issue_Assignee': None,
                'Subtask': None,
                'Subtask_Key': None,
                'Subtask_Priority': None,
                'Subtask_Status': None,
                'Subtask_Assignee': None,
                'Level': 'Epic'
            })
        else:
            for issue in epic['linked_issues']:
                if not issue.get('subtasks'):
                    # Issue with no subtasks
                    rows.append({
                        'Epic': epic['summary'],
                        'Epic_Key': epic['key'],
                        'Epic_Priority': epic['priority'],
                        'Epic_Status': epic['status'],
                        'Epic_Assignee': epic['assignee'],
                        'Issue': issue['summary'],
                        'Issue_Key': issue['key'],
                        'Issue_Type': issue['type'],
                        'Issue_Priority': issue['priority'],
                        'Issue_Status': issue['status'],
                        'Issue_Assignee': issue['assignee'],
                        'Subtask': None,
                        'Subtask_Key': None,
                        'Subtask_Priority': None,
                        'Subtask_Status': None,
                        'Subtask_Assignee': None,
                        'Level': 'Issue'
                    })
                else:
                    for subtask in issue['subtasks']:
                        rows.append({
                            'Epic': epic['summary'],
                            'Epic_Key': epic['key'],
                            'Epic_Priority': epic['priority'],
                            'Epic_Status': epic['status'],
                            'Epic_Assignee': epic['assignee'],
                            'Issue': issue['summary'],
                            'Issue_Key': issue['key'],
                            'Issue_Type': issue['type'],
                            'Issue_Priority': issue['priority'],
                            'Issue_Status': issue['status'],
                            'Issue_Assignee': issue['assignee'],
                            'Subtask': subtask['summary'],
                            'Subtask_Key': subtask['key'],
                            'Subtask_Priority': subtask['priority'],
                            'Subtask_Status': subtask['status'],
                            'Subtask_Assignee': subtask['assignee'],
                            'Level': 'Subtask'
                        })
    
    df = pd.DataFrame(rows)
    return df


def render_epic_filters(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Render filtering controls for epic data.
    
    Args:
        df: DataFrame containing flattened epic data
    
    Returns:
        Dictionary of selected filters
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        available_epics = sorted(df['Epic'].dropna().unique())
        selected_epics = st.multiselect(
            "📚 Filter by Epic",
            options=available_epics,
            help="Select one or more epics"
        )
    
    with col2:
        available_priorities = sorted(df['Epic_Priority'].dropna().unique(), 
                                     key=lambda x: (x.startswith('P'), x))
        selected_priorities = st.multiselect(
            "⚡ Filter by Priority",
            options=available_priorities,
            default=available_priorities,
            help="Select one or more priorities"
        )
    
    with col3:
        available_assignees = sorted(df['Issue_Assignee'].dropna().unique())
        selected_assignees = st.multiselect(
            "👤 Filter by Assignee",
            options=available_assignees,
            help="Select one or more assignees"
        )
    
    with col4:
        available_statuses = sorted(df['Issue_Status'].dropna().unique())
        selected_statuses = st.multiselect(
            "🎯 Filter by Status",
            options=available_statuses,
            help="Select one or more statuses"
        )
    
    return {
        'epics': selected_epics,
        'priorities': selected_priorities,
        'assignees': selected_assignees,
        'statuses': selected_statuses
    }


def apply_epic_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply selected filters to the epic data.
    
    Args:
        df: DataFrame containing flattened epic data
        filters: Dictionary of selected filters
    
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    # Apply epic filter
    if filters['epics']:
        filtered_df = filtered_df[
            (filtered_df['Epic'].isin(filters['epics'])) | 
            (filtered_df['Epic'].isna())
        ]
    
    # Apply priority filter (check both epic and issue priorities)
    if filters['priorities']:
        filtered_df = filtered_df[
            (filtered_df['Epic_Priority'].isin(filters['priorities'])) |
            (filtered_df['Issue_Priority'].isin(filters['priorities'])) |
            (filtered_df['Subtask_Priority'].isin(filters['priorities']))
        ]
    
    # Apply assignee filter
    if filters['assignees']:
        filtered_df = filtered_df[
            (filtered_df['Issue_Assignee'].isin(filters['assignees'])) |
            (filtered_df['Subtask_Assignee'].isin(filters['assignees']))
        ]
    
    # Apply status filter
    if filters['statuses']:
        filtered_df = filtered_df[
            (filtered_df['Issue_Status'].isin(filters['statuses'])) |
            (filtered_df['Subtask_Status'].isin(filters['statuses']))
        ]
    
    return filtered_df


def render_epic_table(df: pd.DataFrame, base_url: str) -> None:
    """
    Render the epic hierarchy as an interactive table with links to Jira.
    
    Args:
        df: Filtered DataFrame containing epic data
        base_url: Base URL of the Jira instance
    """
    if df.empty:
        st.warning("⚠️ No epics found matching the filters")
        return
    
    st.subheader(f"📊 Epic Hierarchy ({len(df)} items)")
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        unique_epics = df['Epic'].dropna().nunique()
        st.metric("📚 Epics", unique_epics)
    with col2:
        unique_issues = df['Issue_Key'].dropna().nunique()
        st.metric("📋 Issues/Stories", unique_issues)
    with col3:
        unique_subtasks = df['Subtask_Key'].dropna().nunique()
        st.metric("✅ Subtasks", unique_subtasks)
    with col4:
        total_items = len(df)
        st.metric("🔢 Total Items", total_items)
    
    st.divider()
    
    # Prepare display columns with Jira links
    display_df = df.copy()
    
    # Create clickable links
    display_df['Epic_Link'] = display_df.apply(
        lambda row: f"[{row['Epic_Key']}]({base_url}/browse/{row['Epic_Key']})" if pd.notna(row['Epic_Key']) else "",
        axis=1
    )
    display_df['Issue_Link'] = display_df.apply(
        lambda row: f"[{row['Issue_Key']}]({base_url}/browse/{row['Issue_Key']})" if pd.notna(row['Issue_Key']) else "",
        axis=1
    )
    display_df['Subtask_Link'] = display_df.apply(
        lambda row: f"[{row['Subtask_Key']}]({base_url}/browse/{row['Subtask_Key']})" if pd.notna(row['Subtask_Key']) else "",
        axis=1
    )
    
    # Select columns to display
    columns_to_show = [
        'Epic', 'Epic_Link', 'Epic_Priority', 'Epic_Status',
        'Issue', 'Issue_Link', 'Issue_Type', 'Issue_Priority', 'Issue_Status', 'Issue_Assignee',
        'Subtask', 'Subtask_Link', 'Subtask_Priority', 'Subtask_Status', 'Subtask_Assignee'
    ]
    
    display_columns = {
        'Epic': 'Epic Summary',
        'Epic_Link': 'Epic Key',
        'Epic_Priority': 'Epic Priority',
        'Epic_Status': 'Epic Status',
        'Issue': 'Issue/Story Summary',
        'Issue_Link': 'Issue Key',
        'Issue_Type': 'Type',
        'Issue_Priority': 'Priority',
        'Issue_Status': 'Status',
        'Issue_Assignee': 'Assignee',
        'Subtask': 'Subtask Summary',
        'Subtask_Link': 'Subtask Key',
        'Subtask_Priority': 'Priority',
        'Subtask_Status': 'Status',
        'Subtask_Assignee': 'Assignee'
    }
    
    table_df = display_df[columns_to_show].rename(columns=display_columns)
    
    # Display as markdown table for clickable links
    st.markdown(table_df.to_markdown(index=False), unsafe_allow_html=True)
    
    # Also provide downloadable CSV
    st.divider()
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name="epic_hierarchy.csv",
        mime="text/csv"
    )


def render_epic_viewer(jira_client: JiraClient, base_url: str) -> None:
    """
    Main epic viewer interface.
    
    Args:
        jira_client: Initialized Jira client
        base_url: Base URL of the Jira instance
    """
    st.subheader("🏛️ Epic Hierarchy View")
    
    # Fetch epic hierarchy
    if st.button("🔄 Load Epic Hierarchy", type="primary", use_container_width=True):
        try:
            with st.spinner("📡 Fetching epic hierarchy from Jira..."):
                epic_hierarchy = jira_client.get_epic_hierarchy()
                st.session_state.epic_hierarchy = epic_hierarchy
                st.success(f"✅ Loaded {len(epic_hierarchy)} epics")
        except JiraAPIError as e:
            st.error(f"❌ Jira API Error: {str(e)}")
            logger.error(f"Jira API error: {str(e)}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            logger.error(f"Error: {str(e)}", exc_info=True)
    
    # Display epic data if available
    if 'epic_hierarchy' in st.session_state and st.session_state.epic_hierarchy:
        st.divider()
        
        # Flatten data for display and filtering
        df = flatten_epic_data(st.session_state.epic_hierarchy)
        
        # Render filters
        st.subheader("🔍 Filters")
        filters = render_epic_filters(df)
        
        # Apply filters
        filtered_df = apply_epic_filters(df, filters)
        
        st.divider()
        
        # Render table
        render_epic_table(filtered_df, base_url)
    else:
        st.info("💡 Click 'Load Epic Hierarchy' to fetch epics and their related issues from Jira")
