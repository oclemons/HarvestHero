# Harvest Hero - Client Device Setup Guide

Quick setup instructions for deploying to client/destination devices.

---

## ⚡ Quick Start (5 minutes)

### Prerequisites
- Python 3.9 or higher
- Git (or ability to download ZIP)
- Internet connection
- ~500MB disk space

### Installation Steps

#### **On Mac/Linux:**

```bash
# 1. Clone the repository
git clone https://github.com/oclemons/HarvestHero.git
cd HarvestHero

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

#### **On Windows:**

```cmd
# 1. Clone the repository
git clone https://github.com/oclemons/HarvestHero.git
cd HarvestHero

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

#### **Or use the automated script:**

**Mac/Linux:**
```bash
chmod +x deploy.sh
./deploy.sh client
```

**Windows:**
```cmd
deploy.bat client
```

---

## 📋 Detailed Setup

### Step 1: Install Python

**Mac:**
```bash
# Using Homebrew
brew install python3

# Verify installation
python3 --version
```

**Windows:**
1. Download from https://www.python.org/downloads/
2. Run installer
3. ✅ Check "Add Python to PATH"
4. Click "Install Now"

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip

# Verify
python3 --version
```

### Step 2: Install Git (Optional)

**Mac:**
```bash
brew install git
```

**Windows:**
Download from https://git-scm.com/download/win

**Linux:**
```bash
sudo apt-get install git
```

### Step 3: Clone the Repository

```bash
git clone https://github.com/oclemons/HarvestHero.git
cd HarvestHero
```

**Alternative (if no Git):**
1. Go to https://github.com/oclemons/HarvestHero
2. Click "Code" → "Download ZIP"
3. Extract the ZIP file
4. Open terminal in the extracted folder

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

If you get permission errors:
```bash
pip install --user -r requirements.txt
```

### Step 5: Run the Application

```bash
python main.py
```

Or on some systems:
```bash
python3 main.py
```

---

## 🔐 First Login

**Default Admin Account:**
- Username: `admin`
- Password: Will be shown on first run (or check documentation)

**First Steps:**
1. Login with admin account
2. Create staff accounts in Admin → Users
3. Configure settings (optional)
4. Start using the application!

---

## 🔄 Keeping Updated

The application has a built-in update system!

### Automatic Updates:
1. When you start the app, it checks GitHub for updates
2. If an update is available, you'll see a notification
3. Click "Update" to download and install
4. App restarts automatically with new version

### Manual Updates:
```bash
cd HarvestHero
git pull origin main
pip install -r requirements.txt
python main.py
```

---

## ⚙️ Configuration (Optional)

### OpenAI Integration (for AI features)

Create `OpenAI.env` in the application folder:
```
OPENAI_API_KEY=sk-your-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### Email Configuration (for password reset)

Create `~/.config/harvest_hero/email_config.json`:

**Mac/Linux:**
```bash
mkdir -p ~/.config/harvest_hero
```

**File contents:**
```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "sender_email": "your-email@gmail.com",
  "sender_password": "your-app-password",
  "organization_name": "Your Pantry Name"
}
```

---

## 🐛 Troubleshooting

### "Python not found"
```bash
# Try python3 instead
python3 main.py
```

### "Module not found" errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### "Permission denied" on Mac/Linux
```bash
# Make script executable
chmod +x deploy.sh
./deploy.sh client
```

### Database errors
- Database auto-initializes on first run
- If issues persist, delete `data/inventory.db` and restart
- Application will recreate the database

### Can't connect to GitHub (for updates)
- Check internet connection
- Verify GitHub is accessible
- Updates are optional; app still works offline

### Port already in use
- Close other instances of the application
- Or change the port in settings

---

## 📊 Features Available

✅ Inventory management
✅ Client/student tracking
✅ Barcode scanning
✅ Weight/pounds tracking
✅ Shopping list auto-population
✅ Admin dashboard with statistics
✅ Multi-user support with roles
✅ Automatic low-stock detection
✅ Shelf management
✅ Reports and exports
✅ Automatic update system
✅ AI-powered insights (if configured)

---

## 🆘 Getting Help

1. **Check the logs**: Look for error messages in the console
2. **Review documentation**: Check BUILD_GUIDE.md
3. **GitHub Issues**: https://github.com/oclemons/HarvestHero/issues
4. **Check internet**: Verify connection for updates and AI features

---

## 📱 System Requirements

**Minimum:**
- Python 3.9+
- 500MB disk space
- 2GB RAM
- Internet connection (for updates)

**Recommended:**
- Python 3.11+
- 1GB disk space
- 4GB+ RAM
- Stable internet connection

**Supported Platforms:**
- ✅ macOS 10.14+
- ✅ Windows 10+
- ✅ Linux (Ubuntu 18.04+)

---

## ✨ Tips for Success

1. **Keep updated**: Accept updates when prompted
2. **Regular backups**: Backup the `data` folder periodically
3. **Test first**: Try on one device before rolling out to many
4. **Document settings**: Keep notes on any custom configurations
5. **Monitor logs**: Check console output for any warnings

---

## 🚀 Ready to Deploy?

1. ✅ Install Python
2. ✅ Clone repository
3. ✅ Install dependencies
4. ✅ Run application
5. ✅ Login and start using!

**That's it!** The application is ready to use.

---

**Questions?** Check the GitHub repository or review the BUILD_GUIDE.md for more detailed information.
