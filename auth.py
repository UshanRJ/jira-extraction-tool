"""
Authentication Module
Handles user login and session management
"""

import streamlit as st
import hashlib
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages user authentication and sessions"""
    
    def __init__(self):
        self.session_timeout = 3600  # 1 hour in seconds
        
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def get_users(self) -> dict:
        """
        Get all valid users and their password hashes
        Returns dict with username as key and password_hash as value
        """
        users = {}
        
        try:
            if hasattr(st, 'secrets') and 'users' in st.secrets:
                # Multiple users from secrets (Streamlit Cloud)
                users = dict(st.secrets['users'])
            elif hasattr(st, 'secrets') and 'auth' in st.secrets:
                # Single user from old format (backward compatibility)
                username = st.secrets['auth'].get('username', 'admin')
                password_hash = st.secrets['auth'].get('password_hash', self.hash_password('admin'))
                users[username] = password_hash
            else:
                # Load from environment file
                from dotenv import load_dotenv
                load_dotenv()
                
                # Try loading multiple users from USER_1, USER_2, etc.
                user_index = 1
                while True:
                    username_key = f'APP_USER_{user_index}_USERNAME'
                    password_key = f'APP_USER_{user_index}_PASSWORD_HASH'
                    
                    username = os.getenv(username_key)
                    password_hash = os.getenv(password_key)
                    
                    if username and password_hash:
                        users[username] = password_hash
                        user_index += 1
                    else:
                        break
                
                # If no users found with new format, try old single-user format (backward compatibility)
                if not users:
                    username = os.getenv('APP_USERNAME', 'admin')
                    password_hash = os.getenv('APP_PASSWORD_HASH', self.hash_password('admin'))
                    users[username] = password_hash
                    
        except Exception as e:
            logger.error(f"Error loading users: {str(e)}")
            # Fallback to default admin user
            users['admin'] = self.hash_password('admin')
        
        return users
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """
        Verify user credentials against stored users
        Supports multiple users from environment or secrets
        """
        try:
            users = self.get_users()
            password_hash = self.hash_password(password)
            
            # Check if username exists and password matches
            if username in users and users[username] == password_hash:
                logger.info(f"Successful login for user: {username}")
                return True
            else:
                logger.warning(f"Failed login attempt for user: {username}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated and session is valid"""
        if 'authenticated' not in st.session_state:
            return False
        
        if not st.session_state.authenticated:
            return False
        
        # Check session timeout
        if 'login_time' in st.session_state:
            elapsed = (datetime.now() - st.session_state.login_time).total_seconds()
            if elapsed > self.session_timeout:
                logger.info("Session timeout - logging out")
                self.logout()
                return False
        
        return True
    
    def login(self, username: str):
        """Set user as authenticated"""
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.login_time = datetime.now()
        logger.info(f"User logged in: {username}")
    
    def logout(self):
        """Clear authentication state"""
        if 'username' in st.session_state:
            logger.info(f"User logged out: {st.session_state.username}")
        
        st.session_state.authenticated = False
        if 'username' in st.session_state:
            del st.session_state.username
        if 'login_time' in st.session_state:
            del st.session_state.login_time
        if 'data' in st.session_state:
            del st.session_state.data
        if 'filtered_data' in st.session_state:
            del st.session_state.filtered_data
    
    def render_login_page(self):
        """Render the login page"""
        st.markdown('<div class="main-header">🔐 Jira Data Extraction Tool</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Secure Login Required</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div style='background-color: #F4F5F7; padding: 2rem; border-radius: 10px; margin-top: 2rem;'>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                st.subheader("Login")
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    submit = st.form_submit_button("🔓 Login", use_container_width=True, type="primary")
                
                if submit:
                    if not username or not password:
                        st.error("⚠️ Please enter both username and password")
                    elif self.verify_credentials(username, password):
                        self.login(username)
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                        logger.warning(f"Failed login attempt for username: {username}")
            
            with st.expander("ℹ️ First Time Setup"):
                st.markdown("""
                **Default Credentials (Change in Production!):**
                - Username: `admin`
                - Password: `admin`
                
                **To Add Multiple Users:**
                
                Update `.env` file with numbered users:
                ```env
                # User 1
                APP_USER_1_USERNAME=admin
                APP_USER_1_PASSWORD_HASH=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
                
                # User 2
                APP_USER_2_USERNAME=john
                APP_USER_2_PASSWORD_HASH=your_hash_here
                
                # User 3
                APP_USER_3_USERNAME=jane
                APP_USER_3_PASSWORD_HASH=your_hash_here
                ```
                
                **Generate Password Hash:**
                ```bash
                python -c "import hashlib; print(hashlib.sha256(input('Enter password: ').encode()).hexdigest())"
                ```
                
                **For Streamlit Cloud (Multiple Users):**
                ```toml
                [users]
                admin = "hash_for_admin"
                john = "hash_for_john"
                jane = "hash_for_jane"
                ```
                
                **Note:** The old single-user format is still supported for backward compatibility.
                """)


# Global auth manager instance
auth_manager = AuthManager()
