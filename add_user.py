"""
User Management Utility
Add new users to the Jira Extraction Tool
"""

import hashlib
import os
from pathlib import Path


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_next_user_number(env_content: str) -> int:
    """Find the next available user number"""
    user_num = 1
    while f'APP_USER_{user_num}_USERNAME' in env_content:
        user_num += 1
    return user_num


def add_user_to_env(username: str, password: str):
    """Add a new user to the .env file"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("⚠️  .env file not found. Creating from .env.example...")
        example_path = Path('.env.example')
        if example_path.exists():
            with open(example_path, 'r') as f:
                env_content = f.read()
            with open(env_path, 'w') as f:
                f.write(env_content)
        else:
            print("❌ .env.example not found. Please create .env file manually.")
            return False
    
    # Read current .env content
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Check if username already exists
    if f'USERNAME={username}' in env_content:
        print(f"⚠️  Username '{username}' already exists in .env file!")
        overwrite = input("Do you want to update the password? (yes/no): ").lower()
        if overwrite != 'yes':
            print("❌ User addition cancelled.")
            return False
    
    # Generate password hash
    password_hash = hash_password(password)
    
    # Get next user number
    user_num = get_next_user_number(env_content)
    
    # Add new user to .env file
    new_user_entry = f"""
# User {user_num}
APP_USER_{user_num}_USERNAME={username}
APP_USER_{user_num}_PASSWORD_HASH={password_hash}
"""
    
    with open(env_path, 'a') as f:
        f.write(new_user_entry)
    
    print(f"✅ User '{username}' added successfully!")
    print(f"   User Number: {user_num}")
    print(f"   Password Hash: {password_hash}")
    print("\n⚠️  Please restart the application for changes to take effect.")
    
    return True


def add_user_to_secrets(username: str, password: str):
    """Add a new user to secrets.toml for Streamlit Cloud"""
    secrets_dir = Path('.streamlit')
    secrets_path = secrets_dir / 'secrets.toml'
    
    # Create .streamlit directory if it doesn't exist
    secrets_dir.mkdir(exist_ok=True)
    
    # Generate password hash
    password_hash = hash_password(password)
    
    # Read or create secrets.toml
    if secrets_path.exists():
        with open(secrets_path, 'r') as f:
            content = f.read()
    else:
        content = ""
    
    # Check if [users] section exists
    if '[users]' not in content:
        content += "\n[users]\n"
    
    # Add user entry
    user_entry = f'{username} = "{password_hash}"\n'
    
    # Insert after [users] section
    lines = content.split('\n')
    new_lines = []
    in_users_section = False
    user_added = False
    
    for line in lines:
        if line.strip() == '[users]':
            in_users_section = True
            new_lines.append(line)
        elif in_users_section and line.startswith('['):
            # New section starting, add user before it
            if not user_added:
                new_lines.append(user_entry)
                user_added = True
            in_users_section = False
            new_lines.append(line)
        elif in_users_section and f'{username} =' in line:
            # User already exists, replace
            new_lines.append(user_entry.strip())
            user_added = True
        else:
            new_lines.append(line)
    
    # If still in users section at end of file, add user
    if in_users_section and not user_added:
        new_lines.append(user_entry.strip())
    
    # Write back to file
    with open(secrets_path, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f"✅ User '{username}' added to secrets.toml!")
    print(f"   Password Hash: {password_hash}")
    
    return True


def main():
    print("=" * 60)
    print("  Jira Extraction Tool - User Management")
    print("=" * 60)
    print()
    
    # Get user input
    username = input("Enter username: ").strip()
    if not username:
        print("❌ Username cannot be empty!")
        return
    
    password = input("Enter password: ").strip()
    if not password:
        print("❌ Password cannot be empty!")
        return
    
    confirm_password = input("Confirm password: ").strip()
    if password != confirm_password:
        print("❌ Passwords do not match!")
        return
    
    print()
    print("Select configuration type:")
    print("1. Local (.env file)")
    print("2. Streamlit Cloud (secrets.toml)")
    print("3. Both")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    print()
    
    if choice == '1':
        add_user_to_env(username, password)
    elif choice == '2':
        add_user_to_secrets(username, password)
    elif choice == '3':
        add_user_to_env(username, password)
        add_user_to_secrets(username, password)
    else:
        print("❌ Invalid choice!")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
