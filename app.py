"""
Jira Data Extraction Tool - Enhanced Production-Ready Application
Professional Streamlit application with authentication and advanced filtering
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging

# Local imports
from auth import auth_manager
from config import config_manager
from jira_client import JiraClient, JiraAPIError
from data_processor import DataProcessor
from utils import setup_logging, InputValidator, ValidationError, DataExporter, ExportError

# Setup logging
setup_logging(log_level="INFO", log_to_file=True)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Jira Data Extraction Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0052CC;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #5E6C84;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F4F5F7;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #0052CC;
        margin-bottom: 1rem;
    }
    .success-message {
        background-color: #E3FCEF;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #00875A;
    }
    .error-message {
        background-color: #FFEBE6;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #DE350B;
    }
    .info-box {
        background-color: #DEEBFF;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #0052CC;
        margin-bottom: 1rem;
    }
    /* Improved button styling */
    .stButton>button {
        font-weight: 600;
    }
    /* Header styling */
    header[data-testid="stHeader"] {
        background-color: #0052CC;
    }
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #F4F5F7;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state"""
    if 'data' not in st.session_state:
        st.session_state.data = None
    if 'filtered_data' not in st.session_state:
        st.session_state.filtered_data = None
    if 'config_loaded' not in st.session_state:
        st.session_state.config_loaded = False


def load_configuration():
    """Load application configuration, cached per session to avoid shared singleton state"""
    if 'jira_config' in st.session_state:
        return st.session_state.jira_config
    try:
        # Call load_config() directly to bypass the module-level cache, so each
        # session gets its own config and stale cached values can't leak across logouts.
        config = config_manager.load_config()
        st.session_state.jira_config = config
        st.session_state.config_loaded = True
        return config
    except ValueError as e:
        error_msg = str(e)
        st.error(f"⚠️ Configuration Error")
        
        # Check if we have Streamlit secrets available
        has_secrets = hasattr(st, 'secrets') and len(st.secrets) > 0
        
        with st.expander("📖 Configuration Help", expanded=True):
            st.error(error_msg)
            st.markdown("---")
            
            if has_secrets:
                # Running on Streamlit Cloud but secrets are incomplete
                st.markdown("""
                ### 🌐 Streamlit Cloud Configuration Issue
                
                Your app is running on Streamlit Cloud but some required secrets are missing.
                
                **How to Fix:**
                
                1. Go to your app settings on [Streamlit Cloud](https://share.streamlit.io)
                2. Navigate to **Settings → Secrets**
                3. Add the following configuration:
                
                ```toml
                [jira]
                cloud_id = "your-atlassian-cloud-id"
                project_key = "IBNU"
                base_url = "https://yourcompany.atlassian.net"
                email = "your-email@example.com"
                api_token = "your-jira-api-token"
                
                [users]
                admin = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
                ```
                
                4. Click **Save** (app will restart automatically)
                
                **Getting Credentials:**
                - 📖 See [API_SETUP.md](https://github.com/UshanRJ/jira-extraction-tool/blob/master/API_SETUP.md)
                - 🔑 [Get Jira API Token](https://id.atlassian.com/manage-profile/security/api-tokens)
                
                **Note:** `.env` files are NOT used on Streamlit Cloud - only Secrets!
                """)
            else:
                # Running locally
                st.markdown("""
                ### 💻 Local Development Configuration
                
                **How to Fix:**
                
                1. Create a `.env` file by copying the example:
                   ```bash
                   copy .env.example .env
                   ```
                
                2. Edit `.env` and fill in your Jira credentials:
                   ```env
                   JIRA_CLOUD_ID=your-cloud-id
                   JIRA_PROJECT_KEY=IBNU
                   JIRA_BASE_URL=https://yourcompany.atlassian.net
                   JIRA_EMAIL=your-email@example.com
                   JIRA_API_TOKEN=your-api-token
                   
                   # User credentials
                   APP_USER_1_USERNAME=admin
                   APP_USER_1_PASSWORD_HASH=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
                   ```
                
                3. Restart the application:
                   ```bash
                   streamlit run app.py
                   ```
                
                **Getting Credentials:**
                - 📖 See `CONFIGURATION_GUIDE.md` for detailed setup
                - 📖 See `API_SETUP.md` for getting Jira credentials
                - 🔑 [Get Jira API Token](https://id.atlassian.com/manage-profile/security/api-tokens)
                
                **Note:** For production deployment, use Streamlit Cloud Secrets instead of `.env` files!
                """)
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Unexpected Configuration Error: {str(e)}")
        logger.error(f"Configuration error: {str(e)}", exc_info=True)
        st.stop()


def resolve_default_options(options, preferred_values):
    """Return preferred values matched against the available options when possible."""
    normalized_options = {str(option).strip().casefold(): option for option in options}
    resolved = []

    for value in preferred_values:
        matched = normalized_options.get(str(value).strip().casefold())
        if matched is not None and matched not in resolved:
            resolved.append(matched)

    return resolved or list(preferred_values)


def render_header():
    """Render application header with user info"""
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown('<div class="main-header">📊 Jira Data Extraction Tool</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Professional QA Issue Analytics & Export</div>', unsafe_allow_html=True)
    
    with col2:
        if 'username' in st.session_state:
            st.info(f"👤 **{st.session_state.username}**")
    
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            auth_manager.logout()
            st.rerun()
    
    st.divider()


def render_sidebar(jira_client: JiraClient):
    """Render enhanced sidebar with all filters"""
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Fetch dynamic project members
        if 'available_reporters' not in st.session_state:
            st.session_state.available_reporters = jira_client.get_project_users()
        available_reporters = st.session_state.available_reporters
        
        # Predefined QA reporters (fallback if not found in Jira)
        QA_REPORTERS = [
            "Chinthaka Somarathna",
            "Madushika Deshappriya",
            "Pasindu Hashara Liyanage",
            "Rukshani Jayathilaka",
            "Ushan Jayakody"
        ]
        
        # Issue Type Selection
        st.subheader("📋 Issue Type" + (" *(overridden)*" if 'filter_clarifications_cb' in st.session_state and st.session_state.filter_clarifications_cb else ""))
        if 'available_issue_types' not in st.session_state:
            st.session_state.available_issue_types = jira_client.get_issue_types()
        available_issue_types = st.session_state.available_issue_types
        
        preset_options = {
            "🐛 Bugs Only": ["Bug"],
            "📝 Tasks with 'Clarification'": ["Task"],
            "📊 All Types": available_issue_types,
            "🎯 Custom Selection": []
        }
        
        preset = st.selectbox(
            "Quick Select",
            options=list(preset_options.keys()),
            help="Choose a preset or select Custom"
        )
        
        if preset == "🎯 Custom Selection":
            selected_issue_types = st.multiselect(
                "Select Issue Types",
                options=available_issue_types,
                default=["Bug", "Task"]
            )
        else:
            selected_issue_types = preset_options[preset]
            st.info(f"✓ {', '.join(selected_issue_types)}")

        # Auto-enable clarification filter when the matching preset is chosen
        if preset == "📝 Tasks with 'Clarification'":
            st.session_state['filter_clarifications_cb'] = True

        # Special filter to include only clarification tasks
        filter_clarifications = st.checkbox(
            "📌 Filter: Title contains 'Clarification'",
            key='filter_clarifications_cb',
            value=False,
            help="Apply special filter: status IN ('01_To Do', 'To Do', 'Ready for Dev', 'Ready For Dev') AND type = Task AND summary ~ 'clarification'"
        )

        if filter_clarifications:
            st.warning(
                "⚠️ **Clarification filter is active.** "
                "Issue Type, Status, and Summary Search selections below are ignored. "
                "Query is forced to: `type = Task AND status IN (To Do, Ready for Dev) AND summary ~ 'clarification'`"
            )

        st.divider()

        # Custom Summary Search (available for all presets)
        st.subheader("🔎 Summary Search" + (" *(overridden)*" if filter_clarifications else ""))
        summary_search_text = st.text_input(
            "Search in Summary",
            value="",
            placeholder="Enter text to search in issue summaries...",
            help="Search for issues containing this text in their summary (case-insensitive)"
        )
        
        st.divider()
        
        # Status Selection
        st.subheader("🎯 Status" + (" *(overridden)*" if filter_clarifications else ""))
        available_statuses = jira_client.get_statuses()
        default_statuses = resolve_default_options(available_statuses, ["To Do", "Ready for Dev"])
        selected_statuses = st.multiselect(
            "Select Statuses",
            options=available_statuses,
            default=default_statuses,
            help="Select one or more statuses"
        )
        
        st.divider()
        
        # Priority Selection
        st.subheader("⚡ Priority")
        available_priorities = jira_client.get_priorities()
        selected_priorities = st.multiselect(
            "Select Priorities",
            options=available_priorities,
            default=["P0", "P1", "P2"],
            help="Select one or more priorities"
        )
        
        st.divider()
        
        # Reporter Filter (NEW)
        st.subheader("👥 Reporter")
        reporter_filter_type = st.radio(
            "Reporter Filter",
            options=["All Reporters", "QA Team Only", "Custom Selection"],
            help="Filter by issue reporter"
        )
        
        if reporter_filter_type == "QA Team Only":
            selected_reporters = QA_REPORTERS
            st.success(f"✓ {len(QA_REPORTERS)} QA team members")
        elif reporter_filter_type == "Custom Selection":
            selected_reporters = st.multiselect(
                "Select Reporters",
                options=available_reporters,
                help="Select specific users who have access to the project"
            )
            if selected_reporters:
                st.info(f"✓ {len(selected_reporters)} reporter(s) selected")
        else:
            selected_reporters = None
            st.info(f"📊 All reporters ({len(available_reporters)} users)")
        
        st.divider()
        
        # Date Range Filter (NEW)
        st.subheader("📅 Created Date Range")
        use_date_filter = st.checkbox("Enable date filtering", value=False)
        
        start_date = None
        end_date = None
        
        if use_date_filter:
            col1, col2 = st.columns(2)
            with col1:
                start_date_input = st.date_input(
                    "From",
                    value=datetime.now() - timedelta(days=30),
                    help="Start date (inclusive)"
                )
                start_date = start_date_input.strftime('%Y-%m-%d')
            
            with col2:
                end_date_input = st.date_input(
                    "To",
                    value=datetime.now(),
                    help="End date (inclusive)"
                )
                end_date = end_date_input.strftime('%Y-%m-%d')
            
            st.caption(f"📆 {start_date} to {end_date}")
        
        st.divider()
        
        # Sprint Filter
        st.subheader("🏃 Sprint")
        filter_no_sprint = st.checkbox(
            "Only issues without Sprint",
            value=False,
            help="Filter issues that have no sprint assigned"
        )
        
        st.divider()
        
        # Max Results
        max_results = st.slider(
            "📊 Max Results",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="Maximum number of issues to retrieve"
        )
        
        st.divider()
        
        # Filter Summary
        with st.expander("📋 Filter Summary"):
            st.markdown(f"""
            - **Issue Types**: {len(selected_issue_types)}
            - **Statuses**: {len(selected_statuses)}
            - **Priorities**: {len(selected_priorities)}
            - **Reporters**: {len(selected_reporters) if selected_reporters else 'All'}
            - **Date Range**: {'Enabled' if use_date_filter else 'Disabled'}
            - **Sprint Filter**: {'Yes' if filter_no_sprint else 'No'}
            - **Summary Search**: {'Yes' if summary_search_text else 'No'}
            """)
        
        return {
            'issue_types': selected_issue_types,
            'statuses': selected_statuses,
            'priorities': selected_priorities,
            'reporters': selected_reporters,
            'start_date': start_date,
            'end_date': end_date,
            'filter_no_sprint': filter_no_sprint,
            'filter_clarifications': filter_clarifications,
            'summary_search': summary_search_text.strip() if summary_search_text else None,
            'max_results': max_results
        }


def fetch_data(jira_client: JiraClient, filters: dict, base_url: str):
    """Fetch data from Jira with enhanced progress tracking"""
    progress_bar = st.progress(0, text="Initializing...")
    
    try:
        progress_bar.progress(10, text="🔄 Connecting to Jira...")
        
        # Fetch issues — reporters filtered in JQL to avoid missing results beyond max_results
        issues = jira_client.search_issues(
            issue_types=filters['issue_types'],
            statuses=filters['statuses'],
            priorities=filters['priorities'],
            include_sprint_filter=filters['filter_no_sprint'],
            filter_clarifications=filters['filter_clarifications'],
            summary_search=filters.get('summary_search'),
            max_results=filters['max_results'],
            reporters=filters.get('reporters'),
            start_date=filters.get('start_date'),
            end_date=filters.get('end_date')
        )
        
        progress_bar.progress(50, text="📦 Processing data...")
        
        if not issues:
            progress_bar.empty()
            st.warning("⚠️ No issues found matching the criteria")
            st.info("💡 **Tip:** Try adjusting your filters or check if the project has issues matching your criteria.")
            return None
        
        # Process to DataFrame
        processor = DataProcessor()
        df = processor.issues_to_dataframe(issues, base_url=base_url)
        
        progress_bar.progress(75, text="🔍 Applying filters...")
        
        # Clarification, reporter, and date filters are applied at JQL level.
        
        if df.empty:
            progress_bar.empty()
            st.warning("⚠️ No issues found after applying filters")
            st.info("💡 **Tip:** The filters may be too restrictive. Try broadening them.")
            return None
        
        progress_bar.progress(100, text="✅ Complete!")
        
        st.session_state.data = df
        st.session_state.filtered_data = df
        
        st.success(f"✅ Successfully fetched **{len(df)}** issues")
        logger.info(f"Fetched {len(df)} issues from Jira")
        
        progress_bar.empty()
        return df
            
    except JiraAPIError as e:
        progress_bar.empty()
        st.error(f"❌ Jira API Error: {str(e)}")
        logger.error(f"Jira API error: {str(e)}")
        return None
    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ Unexpected Error: {str(e)}")
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return None


def render_summary_stats(df: pd.DataFrame):
    """Render enhanced summary statistics"""
    processor = DataProcessor()
    stats = processor.get_summary_stats(df)
    
    st.subheader("📈 Summary Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Issues", stats['total_issues'])
    
    with col2:
        if stats['by_priority']:
            top_priority = max(stats['by_priority'].items(), key=lambda x: x[1])
            st.metric("⚡ Top Priority", f"{top_priority[0]}", f"{top_priority[1]} issues")
    
    with col3:
        if stats['by_status']:
            top_status = max(stats['by_status'].items(), key=lambda x: x[1])
            st.metric("🎯 Top Status", f"{top_status[0]}", f"{top_status[1]} issues")
    
    with col4:
        if stats['by_reporter']:
            top_reporter = max(stats['by_reporter'].items(), key=lambda x: x[1])
            # Shorten name if too long
            reporter_name = top_reporter[0].split()[0] if ' ' in top_reporter[0] else top_reporter[0]
            st.metric("👤 Top Reporter", reporter_name, f"{top_reporter[1]} issues")
    
    # Detailed breakdown
    with st.expander("📊 Detailed Breakdown"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**By Priority:**")
            if stats['by_priority']:
                priority_df = pd.DataFrame(
                    list(stats['by_priority'].items()),
                    columns=['Priority', 'Count']
                ).sort_values('Count', ascending=False)
                st.dataframe(priority_df, hide_index=True, use_container_width=True)
        
        with col2:
            st.write("**By Status:**")
            if stats['by_status']:
                status_df = pd.DataFrame(
                    list(stats['by_status'].items()),
                    columns=['Status', 'Count']
                ).sort_values('Count', ascending=False)
                st.dataframe(status_df, hide_index=True, use_container_width=True)
        
        with col3:
            st.write("**By Reporter:**")
            if stats['by_reporter']:
                reporter_df = pd.DataFrame(
                    list(stats['by_reporter'].items()),
                    columns=['Reporter', 'Count']
                ).sort_values('Count', ascending=False).head(10)
                st.dataframe(reporter_df, hide_index=True, use_container_width=True)


def render_data_table(df: pd.DataFrame):
    """Render interactive data table"""
    st.subheader("📋 Issues")
    
    # Search functionality
    search_term = st.text_input(
        "🔍 Search",
        placeholder="Search by issue key or summary...",
        help="Search across issue keys and summaries"
    )
    
    if search_term:
        processor = DataProcessor()
        filtered_df = processor.filter_dataframe(df, search_term=search_term)
        st.info(f"Showing **{len(filtered_df)}** of **{len(df)}** issues")
    else:
        filtered_df = df
    
    st.session_state.filtered_data = filtered_df
    
    # Prepare display DataFrame (hide URL columns)
    display_df = filtered_df.copy()
    url_columns_to_hide = []
    if 'Issue URL' in display_df.columns:
        url_columns_to_hide.append('Issue URL')
    if 'Epic URL' in display_df.columns:
        url_columns_to_hide.append('Epic URL')
    
    if url_columns_to_hide:
        display_df = display_df.drop(columns=url_columns_to_hide)
    
    # Display dataframe with enhanced column config
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Epic/Story": st.column_config.TextColumn("Epic/Story", width="small"),
            "Issue key": st.column_config.TextColumn("Issue Key", width="small"),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
            "QA Status": st.column_config.TextColumn("Status", width="medium"),
            "Reporter": st.column_config.TextColumn("Reporter", width="medium"),
            "Created Date": st.column_config.TextColumn("Created", width="small"),
            "Summary": st.column_config.TextColumn("Summary", width="large"),
        }
    )


def render_export_section():
    """Render enhanced export functionality"""
    st.subheader("💾 Export Data")
    
    if st.session_state.filtered_data is None or st.session_state.filtered_data.empty:
        st.info("ℹ️ No data available to export. Please fetch data first.")
        return
    
    df = st.session_state.filtered_data
    
    st.markdown(f"**Ready to export {len(df)} issues**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Excel export with clickable links
        try:
            exporter = DataExporter()
            excel_buffer = exporter.to_excel(
                df,
                sheet_name=datetime.now().strftime('%Y-%m-%d'),
                include_timestamp=False
            )
            
            filename = exporter.get_filename(
                base_name="QA_Refinement_Session",
                extension=".xlsx",
                include_timestamp=True
            )
            
            st.download_button(
                label="📥 Download Excel (with clickable links)",
                data=excel_buffer,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
            st.caption("✨ Epic/Story and Issue keys are clickable Jira links")
        except ExportError as e:
            st.error(f"Export error: {str(e)}")
    
    with col2:
        # CSV export
        try:
            exporter = DataExporter()
            # Remove URL columns for CSV as it can't have hyperlinks
            csv_df = df.copy()
            url_columns = ['Issue URL', 'Epic URL']
            existing_url_columns = [col for col in url_columns if col in csv_df.columns]
            if existing_url_columns:
                csv_df = csv_df.drop(columns=existing_url_columns)
            csv_string = exporter.to_csv(csv_df)
            
            filename = exporter.get_filename(
                base_name="QA_Refinement_Session",
                extension=".csv",
                include_timestamp=True
            )
            
            st.download_button(
                label="📥 Download CSV",
                data=csv_string,
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )
            st.caption("📄 Plain text format")
        except ExportError as e:
            st.error(f"Export error: {str(e)}")


def main():
    """Main application function"""
    initialize_session_state()
    
    # Check authentication first
    if not auth_manager.is_authenticated():
        auth_manager.render_login_page()
        return
    
    # User is authenticated, show main app
    render_header()
    
    # Load configuration
    config = load_configuration()
    
    # Initialize Jira client once per session to reuse the HTTP connection pool
    if 'jira_client' not in st.session_state:
        st.session_state.jira_client = JiraClient(
            cloud_id=config.cloud_id,
            project_key=config.project_key,
            base_url=config.base_url,
            email=config.email,
            api_token=config.api_token
        )
    jira_client = st.session_state.jira_client
    
    # Sidebar filters
    filters = render_sidebar(jira_client)
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"📁 Project: Intellisight Plus ({config.project_key})")
    
    with col2:
        if st.button("🔄 Fetch Data", type="primary", use_container_width=True):
            df = fetch_data(jira_client, filters, config.base_url)
    
    # Display data if available
    if st.session_state.data is not None:
        st.divider()
        render_summary_stats(st.session_state.data)
        st.divider()
        render_data_table(st.session_state.data)
        st.divider()
        render_export_section()
    else:
        # Show helpful getting started info
        st.markdown("""
        <div class="info-box">
            <h3>👋 Getting Started</h3>
            <ol>
                <li>Configure your <strong>filters</strong> in the sidebar</li>
                <li>Click <strong>"🔄 Fetch Data"</strong> to retrieve issues</li>
                <li>Review the results and statistics</li>
                <li>Export to <strong>Excel</strong> (with clickable links) or <strong>CSV</strong></li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.caption("Built with ❤️ using Streamlit by @ushanjayakody | Jira Data Extraction Tool v2.0")
    with col2:
        st.caption(f"Session: {st.session_state.username}")
    with col3:
        if 'login_time' in st.session_state:
            elapsed = (datetime.now() - st.session_state.login_time).seconds // 60
            st.caption(f"⏱️ Active: {elapsed}min")


if __name__ == "__main__":
    main()
