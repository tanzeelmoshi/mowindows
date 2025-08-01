# 🚀 MoScraper by Moshi Moshi

A powerful LinkedIn lead scraping tool that helps you find potential clients who are actively looking for services.

## ✨ Features

- **🎯 Smart Lead Detection**: Automatically finds LinkedIn posts from users seeking services
- **📧 Email Extraction**: Extracts contact information from posts and profiles  
- **🤖 AI-Powered Outreach**: Generates personalized email content using Groq/OpenAI
- **📬 SMTP Integration**: Send emails directly from the application
- **🔐 Session Persistence**: Maintains LinkedIn login sessions
- **🖥️ Local Browser Control**: Runs Chrome on your local machine for better session management

## � One-Click Setup & Launch

### 🍎 **macOS/Linux**
1. **Double-click:** `🚀 Launch MoScraper.command`
   - Automatically installs dependencies on first run
   - Launches application immediately

### 🪟 **Windows**  
1. **Double-click:** `start.bat`
   - Automatically installs dependencies on first run
   - Launches application immediately

### 🔧 **Manual Setup (if needed)**
- **macOS/Linux:** `./setup.sh` then `./start.sh`
- **Windows:** `setup.bat` then `start.bat`

## 📋 Prerequisites
- ✅ Python 3.8+ 
- ✅ Google Chrome browser
- ✅ LinkedIn account

## 🎯 How to Use

1. **🚀 Launch** using one of the methods above
2. **🌐 Open browser** - automatically opens to `http://localhost:8501`
3. **🔑 Login to LinkedIn** with your credentials
4. **⚙️ Configure scraping:**
   - Choose: Posts/Keywords or Email Lead mode
   - Set keywords: "looking for designer", "need developer", etc.
   - Adjust limits and delays
5. **▶️ Start scraping** and watch real-time results
6. **💾 Export to CSV** when complete

## 🔧 Advanced Configuration

### 🤖 **AI APIs (Optional)**
- **Groq API**: Fast, cost-effective email generation
- **OpenAI API**: Alternative AI provider

### 📧 **Email Setup (Optional)**  
- **Gmail SMTP**: Send personalized emails directly from app
- Requires Gmail App Password (not regular password)

### ⚡ **Performance Options**
- **Fast Mode**: Reduces delays for quicker scraping
- **Parallel Mode**: Multiple browser instances for speed
- **Debug Mode**: Raw post content for troubleshooting

## 🛠️ File Structure

```
moscrapper-main/
├── 🚀 Launch MoScraper.command    # macOS one-click launcher
├── start.bat                      # Windows one-click launcher  
├── start.sh                       # Cross-platform launcher
├── setup.sh                       # macOS/Linux setup
├── setup.bat                      # Windows setup
├── app.py                         # Main application
├── requirements.txt               # Python dependencies
├── browser-extension/             # Chrome extension (optional)
├── client_scraper.py             # WebSocket client (advanced)
├── websocket_server.py           # WebSocket server (advanced)
└── MoScraper.app/                # macOS app bundle
```

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| 🚫 Chrome driver issues | Click "Clear ChromeDriver Cache" in sidebar |
| 🔑 Login problems | Disable headless mode, check credentials |
| ⚠️ Permission errors | Run `chmod +x *.sh` on macOS/Linux |
| 🐍 Python not found | Install Python 3.8+ from python.org |
| 🌐 Chrome not found | Install Google Chrome browser |

## 📊 Multiple Deployment Options

1. **🖥️ Desktop App**: One-click launchers (recommended)
2. **🔌 Browser Extension**: Direct LinkedIn integration
3. **🌐 WebSocket Mode**: Client-server architecture
4. **☁️ Cloud Deploy**: Docker containers for server deployment

## ⚖️ Legal & Ethics

✅ **Use Responsibly:**
- Comply with LinkedIn Terms of Service
- Respect rate limits and avoid aggressive scraping  
- Only contact leads with relevant, valuable content
- Follow data protection laws (GDPR, CCPA, etc.)

This tool is for legitimate business development and educational purposes only.

---

**🎯 Ready to find your next clients? Just double-click and start scraping!**
# moscraper
# moscraper
# moscrapper
# moscrapper-main
