# Harvest Hero - Build & Deployment Guide

## Quick Start for Client Deployment

This guide explains how to build and deploy Harvest Hero to client devices.

---

## Option 1: Direct Python Installation (Recommended for Development)

### On Client Device:

```bash
# 1. Clone from GitHub
git clone https://github.com/oclemons/HarvestHero.git
cd HarvestHero

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

**Advantages:**
- ✅ Easy to update (just `git pull`)
- ✅ Automatic update system built-in
- ✅ Smallest download size
- ✅ Works on any OS with Python

**Requirements:**
- Python 3.9+
- pip package manager
- Git (optional, can download ZIP)

---

## Option 2: Standalone Executable (Windows/Mac)

### Build on Development Machine:

```bash
# 1. Install PyInstaller
pip install pyinstaller

# 2. Create standalone executable
pyinstaller --onefile --windowed \
  --name "Harvest Hero" \
  --icon=assets/HarvestHeroIcon.png \
  main.py

# 3. The executable will be in: dist/Harvest Hero.exe (Windows) or dist/Harvest Hero (Mac)
```

### Deploy to Client:

1. Copy the `dist/Harvest Hero` executable to client device
2. Create a `data` folder next to the executable
3. Run the executable

**Advantages:**
- ✅ No Python installation needed
- ✅ Single executable file
- ✅ Professional appearance

**Disadvantages:**
- ❌ Larger file size (~100-200MB)
- ❌ Harder to update
- ❌ Platform-specific builds needed

---

## Option 3: Docker Container (Enterprise)

### Build Docker Image:

```bash
# Create Dockerfile in project root
docker build -t harvest-hero:latest .

# Run container
docker run -p 8000:8000 harvest-hero:latest
```

**Advantages:**
- ✅ Consistent across all devices
- ✅ Easy scaling
- ✅ Automatic updates

**Disadvantages:**
- ❌ Requires Docker installation
- ❌ More complex setup

---

## Recommended Deployment Strategy

### For Small Deployments (1-5 devices):
**Use Option 1 (Direct Python)**
- Simplest setup
- Easiest to maintain
- Built-in auto-update system

### For Medium Deployments (5-20 devices):
**Use Option 1 + GitHub Releases**
- Clone from GitHub
- Use built-in update system
- Centralized version control

### For Large Deployments (20+ devices):
**Use Option 2 (Standalone) + Custom Update Server**
- Build once, deploy many
- Custom update mechanism
- More control

---

## Deployment Checklist

### Before Deployment:

- [ ] All code committed to GitHub
- [ ] VERSION.json updated
- [ ] Requirements.txt up to date
- [ ] Database migrations tested
- [ ] OpenAI.env configured (if using AI)
- [ ] Email config set up (if using password reset)

### On Client Device:

- [ ] Python 3.9+ installed (if using Option 1)
- [ ] Git installed (if using Option 1)
- [ ] Network connectivity verified
- [ ] Sufficient disk space (500MB+)
- [ ] Database initialized

### Post-Deployment:

- [ ] Application launches successfully
- [ ] Login works with test account
- [ ] Database accessible
- [ ] Update system functional
- [ ] AI features working (if configured)

---

## Current Build Status

**Latest Version**: 2.0.0
**Last Updated**: January 15, 2024
**GitHub Repository**: https://github.com/oclemons/HarvestHero

### Included Features:
✅ Inventory management
✅ Client tracking
✅ Weight/pounds tracking
✅ Barcode scanning
✅ Shopping list auto-population
✅ Admin dashboard with statistics
✅ Password management with email reset
✅ Automatic low-stock detection
✅ Shelf management
✅ Multi-user support with roles
✅ Automatic update system

---

## Troubleshooting

### "Module not found" errors:
```bash
pip install -r requirements.txt --upgrade
```

### "Python not found":
```bash
python3 main.py  # Use python3 instead
```

### Database errors:
```bash
# Database will auto-initialize on first run
# If issues persist, delete data/inventory.db and restart
```

### Update system not working:
- Check internet connectivity
- Verify GitHub repository is accessible
- Check VERSION.json format

---

## Support

For issues or questions:
1. Check GitHub Issues: https://github.com/oclemons/HarvestHero/issues
2. Review documentation in repository
3. Check console output for error messages

---

## Next Steps

1. **Choose deployment option** (Option 1 recommended)
2. **Prepare client devices** (install Python if needed)
3. **Deploy application** (clone or copy files)
4. **Configure settings** (OpenAI, email, LDAP if needed)
5. **Test thoroughly** (login, inventory, updates)
6. **Train users** (provide user documentation)

---

**Ready to deploy? Start with Option 1 for fastest results!**
