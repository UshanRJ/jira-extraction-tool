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


def flatten_epic_data_with_issues(selected_epics: List[str], epic_issues_map: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
    """
    Flatten the epic and issue data into a DataFrame for easier filtering and display.
    
    Args:
        selected_epics: List of selected epic keys
        epic_issues_map: Dictionary mapping epic keys to their linked issues
    
    Returns:
        DataFrame with flattened hierarchy
    """
    rows = []
    
    for epic_key in selected_epics:
        if epic_key not in epic_issues_map:
            continue
            
        issues = epic_issues_map[epic_key]
        
        if not issues:
            # Epic with no linked issues
            rows.append({
                'Epic_Key': epic_key,
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
            for issue in issues:
                if not issue.get('subtasks'):
                    # Issue with no subtasks
                    rows.append({
                        'Epic_Key': epic_key,
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
                            'Epic_Key': epic_key,
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
    col1, col2, col3 = st.columns(3)
    
    with col1:
        available_priorities = sorted(df['Issue_Priority'].dropna().unique(), 
                                     key=lambda x: (x.startswith('P'), x))
        selected_priorities = st.multiselect(
            "⚡ Filter by Priority",
            options=available_priorities,
            default=available_priorities,
            help="Select one or more priorities"
        )
    
    with col2:
        available_assignees = sorted(df['Issue_Assignee'].dropna().unique())
        selected_assignees = st.multiselect(
            "👤 Filter by Assignee",
            options=available_assignees,
            help="Select one or more assignees"
        )
    
    with col3:
        available_statuses = sorted(df['Issue_Status'].dropna().unique())
        selected_statuses = st.multiselect(
            "🎯 Filter by Status",
            options=available_statuses,
            help="Select one or more statuses"
        )
    
    return {
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
    
    # Apply priority filter
    if filters['priorities']:
        filtered_df = filtered_df[
            (filtered_df['Issue_Priority'].isin(filters['priorities'])) |
            (filtered_df['Subtask_Priority'].isin(filters['priorities'])) |
            (filtered_df['Issue_Priority'].isna())
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
        st.warning("⚠️ No issues found matching the filters")
        return
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        unique_epics = df['Epic_Key'].dropna().nunique()
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
        'Epic_Link', 'Issue_Link', 'Issue_Type', 'Issue_Priority', 'Issue_Status', 'Issue_Assignee',
        'Subtask', 'Subtask_Link', 'Subtask_Priority', 'Subtask_Status', 'Subtask_Assignee'
    ]
    
    display_columns = {
        'Epic_Link': 'Epic',
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
    
    # Use pandas to_html instead of to_markdown (which requires tabulate)
    # Wrap in a custom styled div for better UI/UX
    html_table = table_df.to_html(
        index=False,
        escape=False, # Important for retaining our HTML links
        justify='left',
        classes=['jira-table']
    )
    
    # Custom CSS for a calming, modern, pleasing theme
    st.markdown("""
        <style>
        .jira-table-container {
            overflow-x: auto;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        table.jira-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 0.9em;
            background-color: #ffffff;
            color: #333333;
        }
        table.jira-table thead th {
            background-color: #f4f6f8;
            color: #2c3e50;
            padding: 12px 15px;
            text-align: left;
            border-bottom: 2px solid #e0e6ed;
            font-weight: 600;
        }
        table.jira-table tbody tr {
            border-bottom: 1px solid #e0e6ed;
            transition: background-color 0.2s ease;
        }
        table.jira-table tbody tr:nth-of-type(even) {
            background-color: #fbfcfd;
        }
        table.jira-table tbody tr:hover {
            background-color: #f0f4f8;
        }
        table.jira-table td {
            padding: 10px 15px;
            vertical-align: middle;
        }
        table.jira-table a {
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
        }
        table.jira-table a:hover {
            text-decoration: underline;
            color: #2980b9;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Render the styled table
    st.markdown(f'<div class="jira-table-container">{html_table}</div>', unsafe_allow_html=True)
    
    # Also provide downloadable CSV
    st.divider()
    csv = display_df[['Epic_Key', 'Issue', 'Issue_Key', 'Issue_Type', 'Issue_Priority', 'Issue_Status', 'Issue_Assignee', 'Subtask', 'Subtask_Key', 'Subtask_Priority', 'Subtask_Status', 'Subtask_Assignee']].to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name="epic_hierarchy.csv",
        mime="text/csv"
    )


def render_epic_viewer(jira_client: JiraClient, base_url: str) -> None:
    """
    Main epic viewer interface with two-step workflow: 1) Load epics 2) Select epics and fetch issues.
    
    Args:
        jira_client: Initialized Jira client
        base_url: Base URL of the Jira instance
    """
    st.subheader("🏛️ Epic Hierarchy View")
    
    # Step 1: Load epics if not already loaded
    if 'epics_list' not in st.session_state:
        st.session_state.epics_list = []
        st.session_state.epic_issues_map = {}
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Step 1: Load Epics**")
    with col2:
        if st.button("🔄 Load Epics", type="primary", use_container_width=True):
            try:
                with st.spinner("📡 Fetching epics from Jira..."):
                    epics = jira_client.get_epics()
                    st.session_state.epics_list = epics
                    st.session_state.epic_issues_map = {}
                    st.success(f"✅ Loaded {len(epics)} epics")
            except JiraAPIError as e:
                st.error(f"❌ Jira API Error: {str(e)}")
                logger.error(f"Jira API error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                logger.error(f"Error: {str(e)}", exc_info=True)
    
    st.divider()
    
    # Step 2: Select epics and fetch linked issues
    if st.session_state.epics_list:
        epic_options = {epic['key']: f"{epic['key']} - {epic['summary']}" for epic in st.session_state.epics_list}
        
        st.markdown("**Step 2: Select Epics**")
        selected_epic_keys = st.multiselect(
            "Choose one or more epics to view their issues",
            options=list(epic_options.keys()),
            format_func=lambda x: epic_options[x],
            help="Select epics to load their linked issues, stories, tasks, and subtasks"
        )
        
        if selected_epic_keys:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**Step 3: View Issues** ({len(selected_epic_keys)} epic(s) selected)")
            with col2:
                if st.button("📥 Fetch Issues for Selected Epics", type="primary", use_container_width=True):
                    try:
                        with st.spinner(f"📡 Fetching issues for {len(selected_epic_keys)} epic(s)..."):
                            issues_result = jira_client.get_epic_linked_issues(selected_epic_keys)
                            
                            # Reorganize result into map
                            epic_issues_map = {}
                            for item in issues_result:
                                epic_issues_map[item['epic_key']] = item['issues']
                            
                            st.session_state.epic_issues_map = epic_issues_map
                            
                            total_issues = sum(len(issues) for issues in epic_issues_map.values())
                            st.success(f"✅ Fetched {total_issues} issues for {len(selected_epic_keys)} epic(s)")
                    except JiraAPIError as e:
                        st.error(f"❌ Jira API Error: {str(e)}")
                        logger.error(f"Jira API error: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        logger.error(f"Error: {str(e)}", exc_info=True)
            
            st.divider()
            
            # Display issues if they have been fetched
            if st.session_state.epic_issues_map:
                # Flatten data for display and filtering
                df = flatten_epic_data_with_issues(selected_epic_keys, st.session_state.epic_issues_map)
                
                if not df.empty:
                    # Render filters
                    st.subheader("🔍 Filters")
                    filters = render_epic_filters(df)
                    
                    # Apply filters
                    filtered_df = apply_epic_filters(df, filters)
                    
                    st.divider()
                    
                    # Render table
                    st.subheader(f"📊 Epic Hierarchy ({len(filtered_df)} items)")
                    render_epic_table(filtered_df, base_url)
                else:
                    st.info("💡 No issues found for the selected epics")
        else:
            st.info("💡 Select one or more epics to fetch their issues")
    else:
        st.info("💡 Click 'Load Epics' to fetch epics from Jira")
