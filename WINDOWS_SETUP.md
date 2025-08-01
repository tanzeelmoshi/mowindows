# 🚀 MoScraper Windows Setup Guide

## 📥 Files to Copy to Windows

Copy these **exact files** from your Mac to your Windows machine:

### Essential Files (Required):
- `app.py` - Main application
- `config.py` - Configuration file
- `requirements.windows.txt` - Windows-optimized dependencies
- `start.bat` - Windows launcher
- `setup.bat` - Windows setup script
- `🚀 Launch MoScraper.bat` - One-click launcher
- `README.md` - Documentation

### Optional Files (Recommended):
- `logo.png` / `logo2.png` - App logos
- `.env` - Environment variables (if you have custom settings)

### Folders to Copy:
- `data/` - For storing scraped data
- `logs/` - For application logs
- `temp/` - For temporary files

## 🔧 Windows Installation Steps

### Step 1: Install Python
1. Download Python 3.8+ from https://python.org
2. **IMPORTANT**: Check "Add Python to PATH" during installation
3. Verify: Open Command Prompt and type `python --version`

### Step 2: Install Google Chrome
1. Download from https://chrome.google.com
2. Install normally (required for web scraping)

### Step 3: Setup MoScraper
1. Copy all files to a folder (e.g., `C:\MoScraper\`)
2. **Double-click** `🚀 Launch MoScraper.bat`
3. Wait for automatic setup to complete
4. Application will open in your browser

## 🚀 Quick Start (One-Click)

**Simply double-click: `🚀 Launch MoScraper.bat`**

That's it! The launcher will:
- ✅ Check Python installation
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Start the application
- ✅ Open your browser automatically

## 🔧 Manual Setup (If Needed)

If the one-click launcher doesn't work:

1. Open Command Prompt as Administrator
2. Navigate to your MoScraper folder:
   ```cmd
   cd C:\path\to\your\MoScraper\folder
   ```
3. Run setup:
   ```cmd
   setup.bat
   ```
4. Start application:
   ```cmd
   start.bat
   ```

## 🌐 Accessing the Application

After successful start, open your browser and go to:
- **Primary**: http://localhost:8501
- **Backup**: http://localhost:8502

## 🛠️ Windows-Specific Optimizations

### Chrome Options:
- ✅ Automatic Chrome profile management
- ✅ Windows user data directory handling
- ✅ Process conflict resolution

### Performance:
- ✅ Windows-specific Chrome flags
- ✅ Optimized memory usage
- ✅ Better antivirus compatibility

### Dependencies:
- ✅ `pywin32` for Windows system integration
- ✅ `psutil` for better process management
- ✅ Windows-specific ChromeDriver handling

## 🐛 Troubleshooting

### Python Issues:
```cmd
# If Python not found
where python
# Should show path like: C:\Python311\python.exe

# If pip issues
python -m pip install --upgrade pip
```

### Chrome Issues:
- Make sure Chrome is installed
- Try running as Administrator
- Check Windows Defender isn't blocking

### Permission Issues:
- Run Command Prompt as Administrator
- Check antivirus software settings
- Ensure Windows Defender allows the application

### Port Issues:
```cmd
# If port 8501 is busy, the app will try 8502 automatically
# Or manually specify port:
streamlit run app.py --server.port=8503
```

## 📱 Windows-Specific Features

### Process Management:
- Automatic Chrome process cleanup
- Windows Task Manager integration
- Better memory management

### File Handling:
- Windows path compatibility
- AppData folder support
- Proper file permissions

### Security:
- Windows Defender compatibility
- UAC (User Account Control) support
- Antivirus software compatibility

## 🚀 Performance Tips for Windows

1. **Run as Administrator** for best performance
2. **Add to Windows Defender exclusions** to prevent scanning delays
3. **Close unnecessary Chrome tabs** before scraping
4. **Use SSD storage** for better file I/O performance

## 📧 Support

If you encounter issues:
1. Check the Windows Event Viewer for errors
2. Run `setup.bat` again to reinstall dependencies
3. Try running as Administrator
4. Check antivirus logs for blocked files

---

## 🎯 TL;DR for Windows Users

1. **Copy files** listed above to Windows
2. **Double-click** `🚀 Launch MoScraper.bat`
3. **Wait** for automatic setup
4. **Open browser** to http://localhost:8501
5. **Start scraping!** 🚀
