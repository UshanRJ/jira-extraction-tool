"""
Test script to check what users are retrieved from Jira
"""

import sys
import os

# Load environment
from dotenv import load_dotenv
load_dotenv()

from jira_client import JiraClient

def test_user_retrieval():
    """Test retrieving users from Jira"""
    
    print("=" * 70)
    print("  Testing Jira User Retrieval")
    print("=" * 70)
    print()
    
    # Get config from environment
    cloud_id = os.getenv("JIRA_CLOUD_ID")
    project_key = os.getenv("JIRA_PROJECT_KEY", "IBNU")
    base_url = os.getenv("JIRA_BASE_URL")
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    
    if not all([cloud_id, project_key, base_url, email, api_token]):
        print("❌ Missing Jira configuration in .env file")
        return False
    
    print(f"📡 Connecting to Jira project: {project_key}")
    print(f"🔗 Base URL: {base_url}")
    print()
    
    try:
        # Initialize client
        client = JiraClient(
            cloud_id=cloud_id,
            project_key=project_key,
            base_url=base_url,
            email=email,
            api_token=api_token
        )
        
        print("🔍 Fetching project users...")
        print()
        
        users = client.get_project_users()
        
        print(f"✅ Retrieved {len(users)} unique reporters:")
        print()
        
        for i, user in enumerate(users, 1):
            print(f"   {i:2d}. {user}")
        
        print()
        print("=" * 70)
        
        # Check for specific users
        print()
        print("🔍 Checking for specific QA team members:")
        print()
        
        qa_team = [
            "Chinthaka Somarathna",
            "Madushika Deshappriya",
            "Pasindu Hashara Liyanage",
            "Pasindu Liyanage",
            "Rukshani Jayathilaka",
            "Ushan Jayakody"
        ]
        
        for member in qa_team:
            found = member in users
            status = "✅" if found else "❌"
            print(f"   {status} {member}")
        
        print()
        print("=" * 70)
        
        # Check for variations of Pasindu
        print()
        print("🔍 Looking for Pasindu variations:")
        print()
        
        pasindu_variations = [u for u in users if 'pasindu' in u.lower()]
        
        if pasindu_variations:
            print(f"   Found {len(pasindu_variations)} variation(s):")
            for name in pasindu_variations:
                print(f"   ✅ '{name}'")
        else:
            print("   ❌ No Pasindu found in user list")
        
        print()
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_user_retrieval()
    sys.exit(0 if success else 1)
