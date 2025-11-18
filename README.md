# 📊 Jira Data Extraction Tool

Extract, filter, and export Jira issues with clickable Excel links. Simple, secure, and production-ready.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.51-red)](https://streamlit.io/)

---

## ✨ What It Does

- 🔐 **Secure login** with password protection (supports multiple users)
- 🔍 **Filter issues** by type, status, priority, reporter, and date
- 📊 **View statistics** with breakdowns and summaries
- 📥 **Export to Excel** with clickable Jira links
- 👥 **Team filtering** for specific reporters
- 📅 **Date range** filtering for created dates

---

## 🚀 Quick Start

### 1. Install

```bash
# Clone and navigate
cd jira-extraction-tool

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy example config
copy .env.example .env

# Edit .env with your details
```

Required in `.env`:
```env
JIRA_PROJECT_KEY=your-jira-project-key
JIRA_BASE_URL=your-jira-base-url
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token

APP_USERNAME=your-app-username
APP_PASSWORD_HASH=your-app-password-hash
```

**Get your Jira API token**: [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

### 3. Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

**Default login**: `admin` / `admin` ⚠️ **Change this immediately!**

---

## 📖 How to Use

### Step 1: Login
- Use `admin`/`admin` (change password after first login)

### Step 2: Apply Filters
**Sidebar options:**
- Issue Type (Bug, Task, etc.)
- Status (To Do, Ready for Dev, etc.)
- Priority (P0, P1, P2, etc.)
- Reporter (All, QA Team, or Custom)
- Date Range (optional)
- Sprint filter (issues without sprint)

### Step 3: Fetch Data
- Click **"Fetch Data"** button
- View summary statistics
- Browse results in table
- Search by issue key or summary

### Step 4: Export
- **Excel** - Clickable links on Issue keys and Epic/Story
- **CSV** - Plain text format

---

## 🔑 User Management

### Add Multiple Users

The application supports multiple user accounts. You can add users in two ways:

#### Method 1: Using the Helper Script (Easiest)

```bash
python add_user.py
```

Follow the prompts to:
1. Enter username
2. Enter password
3. Choose configuration type (local/.env or Streamlit Cloud)

#### Method 2: Manual Configuration

**For Local (.env file):**
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

**For Streamlit Cloud (secrets.toml):**
```toml
[users]
admin = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
john = "your_hash_here"
jane = "your_hash_here"
```

### Generate Password Hash

```bash
python -c "import hashlib; print(hashlib.sha256(input('Enter password: ').encode()).hexdigest())"
```

**Note:** The old single-user format (`APP_USERNAME` and `APP_PASSWORD_HASH`) is still supported for backward compatibility.

---

## 📁 Project Files

```
jira-extraction-tool/
├── app.py              # Main application
├── auth.py             # Login system
├── jira_client.py      # Jira API connection
├── data_processor.py   # Data transformation
├── config.py           # Configuration
├── .env                # Your credentials (don't commit!)
├── .env.example        # Template
├── requirements.txt    # Dependencies
└── utils/
    ├── exporters.py    # Excel/CSV export
    ├── logger.py       # Logging
    └── validators.py   # Input validation
```

---

## 🔒 Security

- ✅ SHA-256 password hashing
- ✅ Session management
- ✅ No hardcoded credentials
- ✅ Input validation
- ✅ HTTPS only
- ✅ Rate limiting

---

## 💡 Key Features Explained

### Multiple User Support
- Add unlimited users with unique usernames and passwords
- Each user has their own login credentials
- Session management tracks individual user sessions
- Use the `add_user.py` script for easy user management

### Clickable Excel Links
Both **Issue keys** and **Epic/Story** keys in Excel are clickable - click to open in Jira.

### Reporter Filtering
- **All Reporters** - No filter
- **QA Team Only** - Predefined QA team (5 members)
- **Custom Selection** - Choose from all project users

### Date Filtering
Filter issues created between two dates. Default: Last 30 days.

### Smart Presets
- "Bugs Only" - Quick bug filter
- "Need Clarification" - Tasks needing clarification
- Custom selection for other combinations

---

## 🛠️ Troubleshooting

**Can't login?**
- For multiple users: Check `APP_USER_X_USERNAME` and `APP_USER_X_PASSWORD_HASH` in `.env`
- For single user: Check `APP_USERNAME` and `APP_PASSWORD_HASH` in `.env`
- Regenerate password hash using the command above
- Ensure username matches exactly (case-sensitive)

**No data returned?**
- Verify Jira credentials in `.env`
- Check API token is valid
- Try broader filters

**Excel links don't work?**
- Open in Microsoft Excel (not Google Sheets)
- Check `JIRA_BASE_URL` is correct

**API errors?**
- Verify `JIRA_EMAIL` and `JIRA_API_TOKEN`
- Check project key is correct
- Ensure you have project access

---

## 🎯 Common Use Cases

**Morning standup prep:**
```
Priority: P0, P1
Status: To Do
Sprint: No sprint
→ Export to Excel
```

**QA team review:**
```
Reporter: QA Team Only
Date: Last 7 days
Status: Ready for QA
→ View statistics
```

**Bug triage:**
```
Type: Bug
Priority: P0-P2
Date: Last 14 days
→ Export and share
```

---

## ⚙️ Configuration Reference

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `JIRA_PROJECT_KEY` | Yes | Project key | `IBNU` |
| `JIRA_BASE_URL` | Yes | Jira instance URL | `https://yourcompany.atlassian.net` |
| `JIRA_EMAIL` | Yes | Your Jira email | `user@example.com` |
| `JIRA_API_TOKEN` | Yes | API token | `your-token-here` |
| `APP_USER_1_USERNAME` | Yes* | Username for user 1 | `admin` |
| `APP_USER_1_PASSWORD_HASH` | Yes* | Password hash for user 1 | `8c6976e5...` |
| `APP_USER_2_USERNAME` | No | Username for user 2 | `john` |
| `APP_USER_2_PASSWORD_HASH` | No | Password hash for user 2 | `hash...` |
| `APP_USERNAME` | Yes* | Legacy single-user username | `admin` |
| `APP_PASSWORD_HASH` | Yes* | Legacy single-user password hash | `8c6976e5...` |
| `LOG_LEVEL` | No | Logging level | `INFO` |

**Note:** Use either the new multi-user format (`APP_USER_X_*`) or legacy single-user format (`APP_USERNAME/APP_PASSWORD_HASH`).

---

## 🚀 Deploy to Streamlit Cloud

1. Push to GitHub (exclude `.env`)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Add secrets in dashboard
5. Deploy

**Secrets format (Multiple Users):**
```toml
[jira]
project_key = "IBNU"
base_url = "https://mydigitaloffice.atlassian.net"
email = "your-email@example.com"
api_token = "your-api-token"

[users]
admin = "hash_for_admin"
john = "hash_for_john"
jane = "hash_for_jane"
```

**Secrets format (Single User - Legacy):**
```toml
[jira]
project_key = "IBNU"
base_url = "https://mydigitaloffice.atlassian.net"
email = "your-email@example.com"
api_token = "your-api-token"

[auth]
username = "admin"
password_hash = "your-hash"
```

---

## 📊 What's New in v2.2

- ✅ **Multiple user support** - Add unlimited users with individual credentials
- ✅ Easy user management with `add_user.py` script
- ✅ Backward compatible with single-user configuration
- ✅ Enhanced security with per-user sessions

### Previous Updates (v2.1)
- Epic/Story column now clickable in Excel
- Reporter filter shows all project users
- Improved Excel hyperlink accuracy
- Better error handling

---

## 🤝 Support

- Check documentation in `PRODUCTION_GUIDE.md`
- Review logs in `logs/` directory
- Create an issue on GitHub

---

**Version**: 2.2  
**Last Updated**: November 2025  
**License**: MIT
