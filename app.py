import streamlit as st
import pandas as pd
import time
import re
import pickle
import os
import shutil
import socket
import platform
import json
from datetime import datetime
import concurrent.futures
import random
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchWindowException, WebDriverException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# SMTP email imports
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import ssl

# Debug log area
if 'debug_log' not in st.session_state:
    st.session_state.debug_log = ''
def log_debug(msg):
    st.session_state.debug_log += str(msg) + '\n'
    if len(st.session_state.debug_log) > 5000:
        st.session_state.debug_log = st.session_state.debug_log[-5000:]

# --- Groq AI API config ---
GROQ_API_KEY = st.session_state.get("groq_api_key", "YOUR_GROQ_API_KEY_HERE")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"  # Correct Groq endpoint
# Supported Groq models
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    # Add more models here as Groq supports them
]
GROQ_MODEL_DEFAULT = "llama-3.3-70b-versatile"

def call_groq_api(email, content):
    # Structured, concise prompt for Moshi Moshi outreach, enforce brevity and JSON
    prompt = f"""
You are Tanzeel, a sales guy from Moshi Moshi, a branding and consultancy agency in Bangalore. Write a personalized outreach email in just 3 sentences based on the following full raw LinkedIn post content:
1. Appreciate their work/post.
2. Find the pain point of the person or company.
3. Prepare a call-to-action (CTA) for how Moshi Moshi can help them.

Respond ONLY in valid JSON with keys: subject, body.
- Subject: Max 10 words, catchy and relevant.
- Body: 3 sentences as above, friendly, direct, and actionable.
- Do NOT include any explanations, the word 'json', code blocks, or any extra text. Respond with ONLY the raw JSON object.

Full Raw LinkedIn Post Content:
{content}
"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    model = st.session_state.get("groq_model", GROQ_MODEL_DEFAULT)
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0.7
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        log_debug(f"[GROQ DEBUG] Status code: {response.status_code}")
        log_debug(f"[GROQ DEBUG] Response text: {response.text}")
        response.raise_for_status()
        try:
            result = response.json()
            import json as pyjson
            text = result['choices'][0]['message']['content']
            # Post-process: strip leading 'json', code block markers, and whitespace
            import re
            text = re.sub(r"^(```json|```|json)\\s*", "", text.strip(), flags=re.IGNORECASE)
            text = text.strip('`\n ')
            parsed = pyjson.loads(text)
            return parsed.get('subject', ''), parsed.get('body', '')
        except Exception as json_e:
            log_debug(f"[GROQ JSON ERROR] {json_e}")
            log_debug(f"[GROQ JSON ERROR] Raw response: {response.text}")
            log_debug(f"[GROQ JSON ERROR] Request payload: {data}")
            st.write("Groq raw response:", response.text)
            return "[Groq error]", "[Groq error]"
    except Exception as e:
        log_debug(f"[GROQ ERROR] {e}")
        try:
            if hasattr(e, 'response') and e.response is not None:
                log_debug(f"[GROQ ERROR RESPONSE] {e.response.text}")
        except Exception:
            pass
        log_debug(f"[GROQ ERROR] Request payload: {data}")
        st.write("Groq raw response:", getattr(e, 'response', None) and e.response.text or str(e))
        return "[Groq error]", "[Groq error]"

# --- SMTP Email Sending Module ---
def send_email_smtp(sender_email, sender_password, recipient_email, subject, body, sender_name="Tanzeel from Moshi Moshi"):
    """
    Send email using Gmail SMTP server
    
    Args:
        sender_email (str): Gmail address to send from
        sender_password (str): App password for Gmail (not regular password)
        recipient_email (str): Email address to send to
        subject (str): Email subject line
        body (str): Email body content
        sender_name (str): Display name for sender
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'plain'))
        
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Create secure connection and send email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        log_debug(f"[EMAIL SUCCESS] Email sent to {recipient_email}")
        return True, f"Email sent successfully to {recipient_email}"
        
    except smtplib.SMTPAuthenticationError:
        error_msg = "Authentication failed. Please check your email and app password."
        log_debug(f"[EMAIL ERROR] {error_msg}")
        return False, error_msg
    except smtplib.SMTPRecipientsRefused:
        error_msg = f"Recipient email {recipient_email} was refused by the server."
        log_debug(f"[EMAIL ERROR] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        log_debug(f"[EMAIL ERROR] {error_msg}")
        return False, error_msg

def send_bulk_emails(sender_email, sender_password, email_data, delay_seconds=2.0, sender_name="Tanzeel from Moshi Moshi"):
    """
    Send multiple emails with progress tracking
    
    Args:
        sender_email (str): Gmail address to send from
        sender_password (str): App password for Gmail
        email_data (list): List of dicts with 'email', 'subject', 'body' keys
        delay_seconds (float): Delay between emails to avoid rate limiting
        sender_name (str): Display name for sender
    
    Returns:
        dict: Results with success/failure counts and details
    """
    results = {
        'total': len(email_data),
        'sent': 0,
        'failed': 0,
        'details': []
    }
    
    progress_bar = st.progress(0.0, text="Sending emails...")
    
    for i, email_info in enumerate(email_data):
        recipient = email_info.get('email', '')
        subject = email_info.get('subject', 'Hello from Moshi Moshi')
        body = email_info.get('body', 'Thank you for connecting!')
        
        if not recipient:
            results['failed'] += 1
            results['details'].append({
                'email': 'N/A',
                'status': 'failed',
                'message': 'No email address provided'
            })
            continue
        
        success, message = send_email_smtp(sender_email, sender_password, recipient, subject, body, sender_name)
        
        if success:
            results['sent'] += 1
            status = 'sent'
        else:
            results['failed'] += 1
            status = 'failed'
        
        results['details'].append({
            'email': recipient,
            'status': status,
            'message': message
        })
        
        # Update progress
        progress = (i + 1) / len(email_data)
        progress_bar.progress(progress, text=f"Sending emails... {i+1}/{len(email_data)}")
        
        # Add delay to avoid rate limiting
        if i < len(email_data) - 1:  # Don't delay after the last email
            time.sleep(delay_seconds)
    
    progress_bar.progress(1.0, text="Email sending complete!")
    return results

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/82.0.4017.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.132 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2784.106 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.112 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.143 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1880.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.146 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.6 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1597.12 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.76 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/25.0.1364.172 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/24.0.1307.160 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/23.0.1271.96 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/22.0.1202.4 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/21.0.1180.8 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/19.0.1102.4 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/18.0.1025.168 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/17.0.963.12 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/16.0.934.17 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/15.0.874.120 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/14.0.827.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/13.0.800.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/12.0.760.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/11.0.696.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/10.0.648.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/9.0.629.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/8.0.605.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/7.0.592.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/6.0.570.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/5.0.547.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/4.0.527.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/3.0.507.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/2.0.491.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1.0.477.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/0.0.469.0 Safari/537.36",
]

# Try to import Selenium and browser automation libraries
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from bs4 import BeautifulSoup
    
    # Try to import undetected-chromedriver as optional
    try:
        import undetected_chromedriver as uc
        UNDETECTED_CHROME_AVAILABLE = True
    except ImportError:
        UNDETECTED_CHROME_AVAILABLE = False
        st.warning("⚠️ undetected-chromedriver not available. Using standard Chrome driver.")
        
except ImportError as e:
    st.error(f"Missing required library: {e}. Please run 'pip install -r requirements.txt' and restart the app.")
    st.stop()

# Add this after imports, before any scraping logic

def is_running_locally():
    """Check if the app is running on local machine"""
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip.startswith('127.') or local_ip.startswith('192.168.') or local_ip.startswith('10.') or hostname == 'localhost'
    except:
        return False

def is_driver_alive(driver):
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False

def get_optimal_chrome_options(headless_mode=False, local_mode=True):
    """Get optimized Chrome options based on environment"""
    import uuid
    import time
    options = Options()
    
    if local_mode:
        # Local machine optimizations
        st.info("🏠 Running in local mode - optimized for your machine")
        
        # Create a unique user data directory to avoid conflicts
        import platform
        if platform.system() == "Darwin":  # macOS
            base_user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        elif platform.system() == "Windows":
            base_user_data_dir = os.path.expanduser("~/AppData/Local/Google/Chrome/User Data")
        else:  # Linux
            base_user_data_dir = os.path.expanduser("~/.config/google-chrome")
        
        # Create a unique profile for this session to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        timestamp = str(int(time.time()))
        scraping_profile = os.path.join(base_user_data_dir, f"MoScraper_{timestamp}_{unique_id}")
        os.makedirs(scraping_profile, exist_ok=True)
        
        options.add_argument(f"--user-data-dir={scraping_profile}")
        options.add_argument("--profile-directory=Default")
        
        # Add arguments to prevent Chrome from conflicting with existing instances
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-default-apps")
        options.add_argument("--remote-debugging-port=0")  # Use random port
        
        # Minimal restrictions for local use
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Windows-specific optimizations
        if platform.system() == "Windows":
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-features=TranslateUI")
            options.add_argument("--disable-ipc-flooding-protection")
            # Better Windows Defender compatibility
            options.add_argument("--disable-features=VizDisplayCompositor")
        
        if not headless_mode:
            options.add_argument("--start-maximized")
            # Keep browser open for user interaction
            options.add_experimental_option("detach", True)
    else:
        # Server/cloud optimizations (original code)
        st.info("☁️ Running in server mode - restricted for security")
        
        # Enhanced Chrome options for stability and stealth (minimal permissions)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Media and permission restrictions to prevent system access requests
        options.add_argument("--disable-media-stream")
        options.add_argument("--disable-media-session-api")
        options.add_argument("--disable-microphone")
        options.add_argument("--disable-camera")
        options.add_argument("--disable-audio-input")
        options.add_argument("--disable-audio-output")
        options.add_argument("--disable-web-rtc")
        options.add_argument("--disable-speech-api")
        options.add_argument("--disable-file-system-api")
        options.add_argument("--disable-permissions-api")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-geolocation")
        
        # Basic security settings (without triggering access requests)
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-ipc-flooding-protection")
    
    # Common settings
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    
    if headless_mode:
        options.add_argument("--headless=new")
    
    return options

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
# Regex for website URLs
URL_REGEX = re.compile(r'(https?://[\w\.-]+(?:/[\w\.-]*)*|www\.[\w\.-]+(?:/[\w\.-]*)*)', re.IGNORECASE)

st.set_page_config(page_title="MoScraper by Moshi Moshi", page_icon="🔍", layout="wide")
# Display logo and title using st.image for local compatibility
st.image("logo2.png", width=120)
st.markdown("<h1 style='text-align: center; margin-bottom: 0.2em;'>MoScraper by Moshi Moshi</h1>", unsafe_allow_html=True)
st.markdown("""
This tool helps you find LinkedIn users who are searching for services (e.g., "looking for designer").
**You must log in to LinkedIn to use this tool.**
""")

# Session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'driver' not in st.session_state:
    st.session_state.driver = None
if 'cookies_saved' not in st.session_state:
    st.session_state.cookies_saved = False
if 'results' not in st.session_state:
    st.session_state.results = pd.DataFrame()
if 'pause' not in st.session_state:
    st.session_state.pause = False

scraped_posts = []  # Always define at the top level so it exists for all code paths

# --- LinkedIn Login ---
st.header("1. Login to LinkedIn")
with st.form("login_form"):
    email = st.text_input("LinkedIn Email")
    password = st.text_input("LinkedIn Password", type="password")
    headless_mode = st.checkbox("Run browser in headless mode (faster, but less stable)", value=False)
    login_btn = st.form_submit_button("🔑 Login")

def close_driver():
    try:
        if st.session_state.driver:
            st.session_state.driver.quit()
    except Exception:
        pass
    st.session_state.driver = None
    st.session_state.logged_in = False

def cleanup_chrome_processes():
    """Kill any hanging Chrome processes that might interfere"""
    import subprocess
    import platform
    
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
            subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True)
        elif platform.system() == "Windows":
            subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True)
            subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], capture_output=True)
        else:  # Linux
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
            subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True)
    except Exception:
        pass  # Ignore errors if processes don't exist

from selenium.common.exceptions import NoSuchWindowException, WebDriverException, TimeoutException

def linkedin_login(email, password, headless_mode, retry=True):
    # If already logged in and driver is alive, do not relaunch or prompt
    if st.session_state.get('logged_in') and st.session_state.get('driver'):
        try:
            driver = st.session_state.driver
            # Check if session is still valid by looking for feed/profile
            driver.get("https://www.linkedin.com/feed/")
            try:
                WebDriverWait(driver, 5).until(lambda d: "feed" in d.current_url or d.find_elements(By.CSS_SELECTOR, "img.global-nav__me-photo"))
                st.success("Already logged in to LinkedIn!")
                return True
            except Exception:
                pass  # Session invalid, will retry login
        except Exception:
            pass  # Driver is dead, will retry login
    close_driver()
    
    # Clean up any hanging Chrome processes before starting
    cleanup_chrome_processes()
    
    st.info("Launching browser and logging in...")
    
    # Detect if running locally
    local_mode = is_running_locally()
    
    try:
        # Get optimized Chrome options based on environment
        chrome_options = get_optimal_chrome_options(headless_mode, local_mode)
        
        # Use webdriver-manager to get the correct binary for ARM64
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute basic anti-detection scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("window.chrome = { runtime: {} }")
        
        mode_text = "local machine" if local_mode else "server"
        st.info(f"Using optimized Chrome driver for {mode_text}")
        
        # Store driver in session state
        st.session_state.driver = driver
        
        # Try to load cookies if they exist
        cookies_loaded = False
        if os.path.exists("linkedin_cookies.pkl"):
            driver.get("https://www.linkedin.com")
            with open("linkedin_cookies.pkl", 'rb') as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    # Selenium cookie format fix
                    cookie_dict = {k: v for k, v in cookie.items() if k in ['name', 'value', 'domain', 'path', 'expiry', 'secure', 'httpOnly', 'sameSite']}
                    if 'expiry' in cookie_dict and cookie_dict['expiry'] is not None:
                        cookie_dict['expiry'] = int(cookie_dict['expiry'])
                    try:
                        driver.add_cookie(cookie_dict)
                    except Exception:
                        pass
            driver.refresh()
            # Check if logged in by looking for the feed or profile icon
            try:
                WebDriverWait(driver, 10).until(lambda d: "feed" in d.current_url or d.find_elements(By.CSS_SELECTOR, "img.global-nav__me-photo"))
                st.session_state.logged_in = True
                st.success("Logged in to LinkedIn using saved session!")
                return True
            except Exception:
                pass  # Not logged in, will proceed to manual login
        
        # If not logged in, do manual login
        st.info("🔐 Navigating to LinkedIn login page...")
        driver.get("https://www.linkedin.com/login")
        
        # Wait for login form and add some delay to appear more human-like
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))
        time.sleep(2)  # Human-like delay
        
        st.info("📝 Entering credentials...")
        username_field = driver.find_element(By.ID, "username")
        username_field.clear()
        username_field.send_keys(email)
        time.sleep(1)
        
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(1)
        
        st.info("🚀 Submitting login...")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # Wait for successful login with better error handling
        st.info("⏳ Waiting for LinkedIn to load...")
        try:
            WebDriverWait(driver, 20).until(
                lambda d: "feed" in d.current_url or 
                         "search" in d.current_url or
                         d.find_elements(By.CSS_SELECTOR, "img.global-nav__me-photo") or
                         d.find_elements(By.CSS_SELECTOR, "[data-view-name='nav-me-picture']")
            )
            st.success("✅ Successfully logged in to LinkedIn!")
        except TimeoutException:
            # Check for common login issues
            current_url = driver.current_url
            if "challenge" in current_url:
                st.warning("🔐 LinkedIn is asking for additional verification. Please complete it in the browser.")
                time.sleep(10)  # Give user time to complete verification
            elif "login" in current_url:
                st.error("❌ Login failed. Please check your credentials.")
                raise Exception("Login credentials may be incorrect")
            else:
                st.warning(f"⚠️ Unexpected page after login: {current_url}")
        
        st.session_state.logged_in = True
        # Save cookies for session reuse
        with open("linkedin_cookies.pkl", 'wb') as f:
            pickle.dump(driver.get_cookies(), f)
        st.session_state.cookies_saved = True
        st.success("Logged in successfully!")
        return True
        
    except (NoSuchWindowException, WebDriverException) as e:
        close_driver()
        if retry:
            st.warning("Browser window was closed or crashed. Retrying login...")
            return linkedin_login(email, password, headless_mode, retry=False)
        else:
            st.error("Login failed: Browser window was closed or crashed. Try disabling headless mode or restarting your computer.")
            return False
    except TimeoutException:
        close_driver()
        st.error("Login failed: Timed out waiting for LinkedIn to load. Check your internet connection or try again.")
        return False
    except Exception as e:
        close_driver()
        st.error(f"Login error: {e}")
        return False

if login_btn and email and password:
    linkedin_login(email, password, headless_mode)

if st.session_state.logged_in:
    st.success("You are logged in to LinkedIn.")
    if st.button("Logout"):
        close_driver()
        if os.path.exists("linkedin_cookies.pkl"):
            os.remove("linkedin_cookies.pkl")
        st.rerun()
else:
    st.info("Please log in to continue.")

# Add a sidebar button to clear undetected_chromedriver cache
with st.sidebar:
    st.markdown("### How to Use MoScraper")
    st.markdown("""
    1. Log in to LinkedIn with your credentials.
    2. Choose your scraping mode (posts or emails).
    3. Enter keywords and set your limits.
    4. (Optional) Set max parallel browsers (default: 2).
    5. Click start and watch the magic happen!
    6. Download your results when done.
    """)
    st.markdown("---")
    st.markdown("### LLM API Provider")
    api_provider = st.selectbox("Choose API Provider", ["Groq", "OpenAI"], index=st.session_state.get("api_provider_idx", 0))
    st.session_state["api_provider_idx"] = ["Groq", "OpenAI"].index(api_provider)
    st.session_state["api_provider"] = api_provider
    if api_provider == "Groq":
        groq_api_key = st.text_input("Groq API Key", type="password", value=st.session_state.get("groq_api_key", ""))
        st.markdown('<span style="font-size: 11px;">Get API <a href="https://console.groq.com/keys" target="_blank">here</a></span>', unsafe_allow_html=True)
        # Model selection for Groq
        groq_model = st.selectbox("Groq Model", GROQ_MODELS, index=GROQ_MODELS.index(st.session_state.get("groq_model", GROQ_MODEL_DEFAULT)) if st.session_state.get("groq_model", GROQ_MODEL_DEFAULT) in GROQ_MODELS else 0)
        st.session_state["groq_model"] = groq_model
        if groq_api_key:
            st.session_state["groq_api_key"] = groq_api_key
        if st.button("Check API Key"):
            import time as pytime
            start = pytime.time()
            try:
                headers = {
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": groq_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Say hello."}
                    ],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
                import requests
                resp = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=10)
                resp.raise_for_status()
                elapsed = pytime.time() - start
                st.success(f"Groq API key is valid! Response time: {elapsed:.2f} seconds.")
            except Exception as e:
                st.error(f"Groq API check failed: {e}")
    else:
        openai_api_key = st.text_input("OpenAI API Key", type="password", value=st.session_state.get("openai_api_key", ""))
        st.markdown('<span style="font-size: 11px;">Get API <a href="https://platform.openai.com/api-keys" target="_blank">here</a></span>', unsafe_allow_html=True)
        if openai_api_key:
            st.session_state["openai_api_key"] = openai_api_key
        if st.button("Check API Key"):
            import time as pytime
            start = pytime.time()
            try:
                headers = {
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Say hello."}
                    ],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
                import requests
                resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=10)
                resp.raise_for_status()
                elapsed = pytime.time() - start
                st.success(f"OpenAI API key is valid! Response time: {elapsed:.2f} seconds.")
            except Exception as e:
                st.error(f"OpenAI API check failed: {e}")
    
    st.markdown("---")
    st.markdown("### 📧 SMTP Email Configuration")
    st.markdown("Configure Gmail SMTP to send personalized emails directly from the app.")
    
    smtp_email = st.text_input("Gmail Address", 
                              value=st.session_state.get("smtp_email", ""), 
                              placeholder="your-email@gmail.com",
                              help="Your Gmail address for sending emails")
    
    smtp_password = st.text_input("Gmail App Password", 
                                 type="password", 
                                 value=st.session_state.get("smtp_password", ""),
                                 help="Use Gmail App Password, not your regular password")
    
    if smtp_email:
        st.session_state["smtp_email"] = smtp_email
    if smtp_password:
        st.session_state["smtp_password"] = smtp_password
    
    # Test SMTP connection
    if smtp_email and smtp_password:
        if st.button("🧪 Test SMTP Connection"):
            test_success, test_message = send_email_smtp(
                sender_email=smtp_email,
                sender_password=smtp_password,
                recipient_email=smtp_email,  # Send test email to self
                subject="MoScraper SMTP Test",
                body="This is a test email from MoScraper. Your SMTP configuration is working correctly!",
                sender_name="MoScraper Test"
            )
            
            if test_success:
                st.success("✅ SMTP connection successful! Test email sent.")
            else:
                st.error(f"❌ SMTP connection failed: {test_message}")
    
    # Instructions for Gmail App Password
    with st.expander("📖 How to get Gmail App Password"):
        st.markdown("""
        1. Go to your [Google Account settings](https://myaccount.google.com/)
        2. Navigate to **Security** → **2-Step Verification**
        3. Enable 2-Step Verification if not already enabled
        4. Go to **App passwords** and generate a new password
        5. Select **Mail** as the app and **Other** as the device
        6. Copy the generated 16-character password and paste it above
        
        ⚠️ **Important**: Use the App Password, not your regular Gmail password!
        """)
    
    st.markdown("---")
    st.markdown("### Maintenance")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Clear ChromeDriver Cache"):
            cache_path = os.path.expanduser("~/Library/Application Support/undetected_chromedriver")
            try:
                if os.path.exists(cache_path):
                    shutil.rmtree(cache_path)
                    st.success("ChromeDriver cache cleared! Restart the app to re-download the driver.")
                else:
                    st.info("No ChromeDriver cache found to clear.")
            except Exception as e:
                st.error(f"Failed to clear cache: {e}")
    
    with col2:
        if st.button("🔄 Cleanup Chrome Processes"):
            try:
                cleanup_chrome_processes()
                st.success("Chrome processes cleaned up!")
            except Exception as e:
                st.error(f"Failed to cleanup processes: {e}")

# Add an 'Advanced Options' toggle in the sidebar
with st.sidebar:
    advanced_mode = st.checkbox('Show Advanced Options (Parallel/Fast Mode)', value=False)
    st.markdown('---')
    st.info('You are logged in and ready to scrape!')
    st.caption('If you encounter login issues, try logging out and back in.')

# --- Keyword Search and Scraping ---
st.header("2. Search for Service Requests")
debug_mode = st.checkbox("Show debug info (raw post content)", value=False)
pause_col, resume_col = st.columns(2)
if pause_col.button("⏸️ Pause Scraping"):
    st.session_state.pause = True
if resume_col.button("▶️ Resume Scraping"):
    st.session_state.pause = False

scrape_mode = st.radio(
    "Choose scraping mode:",
    ["Scrape by Posts/Keywords", "Scrape by Emails (lead mode)"]
)

start_btn = False
if scrape_mode == "Scrape by Posts/Keywords":
    with st.form("scrape_form"):
        keywords = st.text_area("Enter keywords (one per line)",
            value="looking for designer\nneed developer\nseeking marketing help")
        max_posts = st.slider("Max posts to scrape", 10, 100, 30)
        delay = st.slider("Delay between actions (seconds)", 1, 10, 2)
        fast_mode = False
        parallel_fast_mode = False
        max_workers = 1
        batch_update = 5
        if advanced_mode:
            fast_mode = st.checkbox("⚡ Fast Mode (less waiting, more slaying)", value=False)
            parallel_fast_mode = st.checkbox("🤖 Parallel Fast Mode (one browser per keyword, max turbo)", value=False, disabled=not fast_mode)
            max_workers = st.number_input("Max parallel browsers", min_value=1, max_value=8, value=2)
            if max_workers > 4:
                st.warning("More than 4 browsers may crash your system!")
            batch_update = st.number_input("Batch UI update (posts/emails)", min_value=1, max_value=20, value=5)
        start_btn = st.form_submit_button("🔍 Start Scraping")
    if start_btn and keywords:
        # Check driver/session health
        driver = st.session_state.get('driver')
        if not driver or not is_driver_alive(driver):
            close_driver()
            st.session_state.logged_in = False
            st.error("Your LinkedIn session/browser was closed or crashed. Please log in again to continue scraping.")
            st.stop()
        keyword_list = [k.strip() for k in keywords.split('\n') if k.strip()]
        all_results = []
        progress = st.progress(0, text="Keyword Progress")
        status = st.empty()
        post_progress = st.progress(0, text="Post Progress")
        # Fast mode overrides
        if fast_mode:
            delay = 0.5  # Zoomies mode
            max_scrolls_global = 2
            max_per_page_global = 5
        else:
            max_scrolls_global = 5
            max_per_page_global = 10
        total_posts = len(keyword_list) * max_posts
        posts_done = 0
        results_placeholder = st.empty()

        def update_results_live():
            df = pd.DataFrame(all_results)
            st.session_state.results = df
            results_placeholder.dataframe(df, use_container_width=True)

        # Helper to copy cookies from main session to a new driver

        def copy_cookies_to_driver(main_driver, new_driver):
            try:
                cookies = main_driver.get_cookies()
                new_driver.get("https://www.linkedin.com")
                for cookie in cookies:
                    cookie_dict = {k: v for k, v in cookie.items() if k in ['name', 'value', 'domain', 'path', 'expiry', 'secure', 'httpOnly', 'sameSite']}
                    if 'expiry' in cookie_dict and cookie_dict['expiry'] is not None:
                        cookie_dict['expiry'] = int(cookie_dict['expiry'])
                    try:
                        new_driver.add_cookie(cookie_dict)
                    except Exception:
                        pass
                new_driver.refresh()
            except Exception:
                pass

        # In get_driver(), use the main session driver if available

        def get_driver(parallel=False):
            if not parallel and st.session_state.get('driver'):
                return st.session_state.driver
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            user_agent = random.choice(USER_AGENTS)
            options.add_argument(f'user-agent={user_agent}')
            
            # Use undetected Chrome if available, otherwise use regular Chrome
            if UNDETECTED_CHROME_AVAILABLE:
                driver = uc.Chrome(options=options)
            else:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                
            # For parallel scraping, try to copy cookies from main session
            if parallel and st.session_state.get('driver'):
                copy_cookies_to_driver(st.session_state.driver, driver)
            return driver

        # In all scraping logic, replace calls to get_driver() with get_driver(parallel=...) as appropriate
        # For single-browser scraping, use get_driver(parallel=False)
        # For parallel scraping, use get_driver(parallel=True) and show a warning

        # Only show parallel scraping warning if advanced_mode and parallel_fast_mode are enabled
        if advanced_mode and fast_mode and parallel_fast_mode:
            st.warning("Parallel scraping launches new browsers and attempts to copy your session, but LinkedIn may still require login in some tabs. For best results, use single-browser mode.")

        def scrape_keyword(kw, mode):
            local_driver = get_driver()
            try:
                posts_collected = 0
                seen_posts = set()
                max_scrolls = 20 if not fast_mode else 10
                search_url = f"https://www.linkedin.com/search/results/content/?keywords={kw.replace(' ', '%20')}&sortBy=date_posted"
                try:
                    local_driver.get(search_url)
                except NoSuchWindowException:
                    log_debug(f"[ERROR] Browser window closed for keyword: {kw}")
                    return
                time.sleep(delay)
                scrolls = 0
                last_first_ids = []
                stale_scrolls = 0
                while posts_collected < max_posts and scrolls < max_scrolls and not st.session_state.pause:
                    try:
                        # Random scroll height to mimic human behavior
                        scroll_height = random.randint(300, 1000) * (scrolls + 1)
                        local_driver.execute_script(f"window.scrollTo(0, {scroll_height});")
                    except NoSuchWindowException:
                        log_debug(f"[ERROR] Scroll failed for keyword: {kw}")
                        break
                    # Random delay between 0.8x and 1.2x the user-set delay
                    time.sleep(delay * random.uniform(0.8, 1.2))
                    try:
                        soup = BeautifulSoup(local_driver.page_source, 'html.parser')
                    except NoSuchWindowException:
                        log_debug(f"[ERROR] Soup failed for keyword: {kw}")
                        break
                    except Exception as e:
                        log_debug(f"[ERROR] Unexpected error during scroll/soup: {e}")
                        break
                    posts = soup.find_all('div', attrs={'data-urn': True})
                    if posts:
                        first_ids = [posts[i].get('data-urn') for i in range(min(3, len(posts)))]
                        log_debug(f"[DEBUG] Keyword: {kw}, Scroll: {scrolls+1}, First 3 post IDs: {first_ids}")
                        if first_ids == last_first_ids:
                            stale_scrolls += 1
                        else:
                            stale_scrolls = 0
                        last_first_ids = first_ids
                        if stale_scrolls >= 3:
                            log_debug(f"[INFO] Breaking scroll loop for {kw} due to repeated post IDs.")
                            break
                    for post in posts:
                        if st.session_state.pause:
                            break
                        post_id = post.get('data-urn')
                        if post_id and post_id in seen_posts:
                            continue
                        seen_posts.add(post_id)
                        # Try to click 'see more' button for this post using Selenium
                        try:
                            post_xpath = f"//div[@data-urn='{post_id}']"
                            post_elem = local_driver.find_element(By.XPATH, post_xpath)
                            see_more = None
                            try:
                                see_more = post_elem.find_element(By.XPATH, ".//button[contains(translate(., 'SEE MORE', 'see more') or contains(., 'more')]")
                            except Exception:
                                try:
                                    see_more = post_elem.find_element(By.XPATH, ".//span[contains(translate(., 'SEE MORE', 'see more') or contains(., 'more')]")
                                except Exception:
                                    pass
                            if see_more:
                                local_driver.execute_script("arguments[0].click();", see_more)
                                time.sleep(0.5)
                        except Exception:
                            pass
                        # Extract author name
                        try:
                            author_elem = post.find('span', class_=lambda x: x and 'actor__name' in x)
                            author = author_elem.get_text(strip=True) if author_elem else "Unknown"
                        except Exception:
                            author = "Unknown"
                        # Extract profile URL
                        profile_url = ''
                        try:
                            for a in post.find_all('a', href=True):
                                if '/in/' in a['href']:
                                    profile_url = a['href']
                                    if not profile_url.startswith('http'):
                                        profile_url = f"https://www.linkedin.com{profile_url}"
                                    break
                        except Exception:
                            profile_url = ''
                        # Extract post content using multiple selectors
                        content = ''
                        raw_content = ''
                        try:
                            selectors = [
                                lambda p: p.find('span', class_=lambda x: x and 'update-components-text' in x),
                                lambda p: p.find('div', class_=lambda x: x and 'feed-shared-text' in x),
                                lambda p: p.find('div', class_=lambda x: x and 'feed-shared-update-v2' in x),
                            ]
                            for sel in selectors:
                                elem = sel(post)
                                if elem and elem.get_text(strip=True):
                                    content = elem.get_text(strip=True)
                                    break
                            if not content:
                                content = post.get_text(separator=' ', strip=True)
                            raw_content = str(post)
                        except Exception:
                            content = ''
                            raw_content = ''
                        post_emails = ', '.join(set(EMAIL_REGEX.findall(content)))
                        websites = ', '.join(set(URL_REGEX.findall(content)))
                        all_page_posts.append({
                            'author': author,
                            'profile_url': profile_url,
                            'post_emails': post_emails,
                            'websites': websites,
                            'content': content,
                            'raw_content': raw_content if debug_mode else '',
                            'keyword': kw
                        })
                        posts_collected += 1
                        results.append(all_page_posts[-1])
                        all_results.append(all_page_posts[-1])
                        update_results_live()
                        if posts_collected >= max_posts:
                            break
                    scrolls += 1
                # Final update after all scrolls
                update_results_live()
            finally:
                try:
                    local_driver.quit()
                except Exception:
                    pass
            return results

        if fast_mode and parallel_fast_mode:
            max_workers = min(4, len(keyword_list))
            status.info(f"Parallel Fast Mode: Spinning up {max_workers} browsers!")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_kw = {executor.submit(scrape_keyword, kw, fast_mode): kw for kw in keyword_list}
                for i, future in enumerate(concurrent.futures.as_completed(future_to_kw)):
                    kw = future_to_kw[future]
                    try:
                        result = future.result()
                        all_results.extend(result)
                        update_results_live()
                    except Exception as exc:
                        st.error(f"Keyword '{kw}' generated an exception: {exc}")
                    progress.progress((i+1)/len(keyword_list), text=f"{i+1} / {len(keyword_list)} keywords done. Keep slayin'!")
            status.success("Scraping complete!")
            post_progress.progress(1.0, text="All posts scraped! 🥳")
        else:
            # Non-parallel: loop over keywords and call scrape_keyword for each
            for i, kw in enumerate(keyword_list):
                status.info(f"Searching for: {kw}")
                try:
                    result = scrape_keyword(kw, fast_mode)
                    all_results.extend(result)
                    update_results_live()
                except Exception as e:
                    st.error(f"Error scraping for '{kw}': {e}")
                    update_results_live()
                progress.progress((i+1)/len(keyword_list), text=f"{i+1} / {len(keyword_list)} keywords done. Keep slayin'!")
            status.success("Scraping complete!")
            post_progress.progress(1.0, text="All posts scraped! 🥳")
        df = pd.DataFrame(all_results)
        # Deduplicate posts by profile_url + content (for posts/keywords mode)
        if not df.empty:
            df = df.drop_duplicates(subset=[col for col in ['profile_url', 'content'] if col in df.columns])
        st.session_state.results = df
        st.success(f"Scraped {len(df)} unique posts.")

elif scrape_mode == "Scrape by Emails (lead mode)":
    with st.form("email_lead_form"):
        keywords = st.text_area("Enter keywords (one per line)",
            value="looking for designer\nneed developer\nseeking marketing help")
        num_emails = st.number_input("Number of unique emails to collect", min_value=1, max_value=1000, value=10)
        delay = st.slider("Delay between actions (seconds)", 1, 10, 2)
        time_limit = st.slider("Max scraping time (seconds)", min_value=10, max_value=1200, value=300, step=10)
        max_scrolls_per_keyword = st.slider("Max scrolls per keyword", min_value=3, max_value=30, value=10, step=1)
        fast_mode = False
        parallel_fast_mode = False
        max_workers = 1
        if advanced_mode:
            fast_mode = st.checkbox("⚡ Fast Mode (less waiting, more slaying)", value=False)
            parallel_fast_mode = st.checkbox("🤖 Parallel Fast Mode (one browser per keyword, max turbo)", value=False, disabled=not fast_mode)
            max_workers = st.number_input("Max parallel browsers", min_value=1, max_value=8, value=2)
            if max_workers > 4:
                st.warning("More than 4 browsers may crash your system!")
        start_btn = st.form_submit_button("🔍 Start Email Scraping")

# Time-driven scraping logic
import time as pytime
if start_btn and keywords:
    driver = st.session_state.get('driver')
    if not driver or not is_driver_alive(driver):
        close_driver()
        st.session_state.logged_in = False
        st.error("Your LinkedIn session/browser was closed or crashed. Please log in again to continue scraping.")
        st.stop()
    keyword_list = [k.strip() for k in keywords.split('\n') if k.strip()]
    email_results = []
    found_emails = set()
    scraped_posts = []  # Ensure this is always defined before the scraping loop
    start_time = pytime.time()
    posts_scraped = 0
    results_placeholder = st.empty()
    debug_placeholder = st.empty()
    progress_bar = st.progress(0.0, text="Scraping...")
    try:
        for kw in keyword_list:
            seen_posts = set()
            posts_scraped = 0
            scraped_posts = []
            driver.get(f"https://www.linkedin.com/search/results/content/?keywords={kw.replace(' ', '%20')}&sortBy=date_posted")
            time.sleep(delay)
            last_seen_count = 0
            no_new_posts_scrolls = 0
            max_no_new_scrolls = 3
            scroll_num = 0
            while (pytime.time() - start_time) < time_limit and len(found_emails) < num_emails and no_new_posts_scrolls < max_no_new_scrolls and scroll_num < max_scrolls_per_keyword:
                scroll_num += 1
                scroll_height = 1000 * scroll_num
                driver.execute_script(f"window.scrollTo(0, {scroll_height});")
                time.sleep(0.7)
                # Use Selenium to find all post elements after scrolling
                post_elems = driver.find_elements(By.XPATH, "//div[@data-urn]")
                new_posts_found = False
                for post_elem in post_elems:
                    try:
                        post_id = post_elem.get_attribute('data-urn')
                    except Exception:
                        post_id = None
                    if not post_id or post_id in seen_posts:
                        continue
                    seen_posts.add(post_id)
                    posts_scraped += 1
                    new_posts_found = True
                    post_text = ''
                    post_html = ''
                    see_more_clicked = False
                    see_more_found = False
                    see_more_error = ''
                    # Scroll post into view and try to click 'see more' robustly
                    try:
                        driver.execute_script("arguments[0].scrollIntoView();", post_elem)
                        time.sleep(0.2)
                        ActionChains(driver).move_to_element(post_elem).perform()
                        see_more = None
                        # Try multiple selectors for the button
                        see_more_selectors = [
                            ".//button[contains(translate(., 'SEE MORE', 'see more') or contains(., 'more')]",
                            ".//span[contains(translate(., 'SEE MORE', 'see more') or contains(., 'more')]",
                            ".//*[contains(text(), '...see more') or contains(text(), 'See more') or contains(text(), 'more') or contains(text(), 'More') or contains(text(), 'Show more')]"
                        ]
                        for selector in see_more_selectors:
                            try:
                                see_more = WebDriverWait(post_elem, 1).until(
                                    lambda el: el.find_element(By.XPATH, selector)
                                )
                                if see_more:
                                    see_more_found = True
                                    break
                            except Exception as e:
                                see_more_error = str(e)
                                continue
                        if see_more:
                            try:
                                ActionChains(driver).move_to_element(see_more).perform()
                                WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, './*')))
                                driver.execute_script("arguments[0].click();", see_more)
                                time.sleep(1.5)
                                see_more_clicked = True
                            except Exception as e:
                                see_more_error = f"Click error: {e}"
                        # After clicking, extract the post's text and innerHTML using Selenium
                        try:
                            post_text = post_elem.text
                        except Exception:
                            post_text = ''
                        try:
                            post_html = post_elem.get_attribute('innerHTML')
                        except Exception:
                            post_html = ''
                    except Exception as e:
                        post_text = ''
                        post_html = ''
                        see_more_error = f"Outer error: {e}"
                    # Extract emails from both text and innerHTML
                    emails_text = set(EMAIL_REGEX.findall(post_text))
                    emails_html = set(EMAIL_REGEX.findall(post_html))
                    all_emails = emails_text | emails_html
                    # Debug output for each post
                    log_debug(f"[POST] id={post_id} see_more_found={see_more_found} see_more_clicked={see_more_clicked} see_more_error={see_more_error} emails_text={list(emails_text)} emails_html={list(emails_html)} text_snippet={post_text[:80]}")
                    if not see_more_found:
                        log_debug(f"[POST_HTML] id={post_id} html_snippet={post_html[:200]}")
                    for email in all_emails:
                        if email not in found_emails:
                            found_emails.add(email)
                            email_results.append({
                                'email': email,
                                'content': post_text,
                                'html_snippet': post_html[:120],
                                'keyword': kw,
                                'post_id': post_id
                            })
                            if len(found_emails) >= num_emails or (pytime.time() - start_time) >= time_limit:
                                break
                    scraped_posts.append({'content': post_text, 'html_snippet': post_html[:120], 'keyword': kw, 'post_id': post_id})
                    if len(found_emails) >= num_emails or (pytime.time() - start_time) >= time_limit:
                        break
                # Show progress
                elapsed = pytime.time() - start_time
                progress_bar.progress(min(elapsed/time_limit, 1.0), text=f"{len(found_emails)}/{num_emails} emails | {posts_scraped} posts | {int(elapsed)}s elapsed")
                results_placeholder.dataframe(pd.DataFrame(email_results), use_container_width=True)
                debug_placeholder.write(pd.DataFrame(scraped_posts[:5]))
                if len(found_emails) >= num_emails or (pytime.time() - start_time) >= time_limit:
                    break
                # If no new posts found, increment counter, else reset
                if len(seen_posts) == last_seen_count:
                    no_new_posts_scrolls += 1
                else:
                    no_new_posts_scrolls = 0
                last_seen_count = len(seen_posts)
            if len(found_emails) >= num_emails or (pytime.time() - start_time) >= time_limit:
                break
    except Exception as scrape_e:
        st.error(f"Error during email extraction: {scrape_e}")
        import traceback
        st.text(traceback.format_exc())
    email_df = pd.DataFrame(email_results)
    st.session_state.results = email_df
    results_placeholder.dataframe(email_df, use_container_width=True)
    reason = None
    if len(found_emails) >= num_emails:
        reason = f"Stopped: Reached target of {num_emails} unique emails."
    elif (pytime.time() - start_time) >= time_limit:
        reason = f"Stopped: Hit time limit of {time_limit} seconds. Only found {len(found_emails)} unique emails."
    else:
        reason = f"Stopped: Ran out of posts to scrape. Only found {len(found_emails)} unique emails."
    if not email_df.empty:
        st.success(f"Collected {len(email_df)} unique emails! Mission accomplished.")
        st.info(reason)
        if len(email_df) < num_emails:
            st.warning(f"Only {len(email_df)} unique emails found. Try increasing the time limit or using broader keywords.")
    else:
        st.info("No emails found in the scraped posts.")
        st.info(reason)

# After scraping, show a table of all scraped post texts for inspection
if scraped_posts:
    st.markdown("### Sample of Scraped Post Texts (first 10)")
    st.dataframe(pd.DataFrame(scraped_posts[:10]), use_container_width=True)

# --- Results Table ---
st.header("3. Results")
df = st.session_state.results
# After scraping and deduplication, ensure all expected columns are present
EXPECTED_COLS = [
    'author', 'profile_url', 'post_emails', 'websites', 'content', 'raw_content', 'keyword'
]
if not df.empty:
    # Add any missing columns with empty string values
    for col in EXPECTED_COLS:
        if col not in df.columns:
            df[col] = ""
    if scrape_mode == "Scrape by Emails (lead mode)":
        display_cols = ['email'] + EXPECTED_COLS
        if debug_mode:
            display_cols.append('raw_content')
        # Guarantee 'email' column in results
        if 'email' not in df.columns:
            df['email'] = ""
        st.dataframe(df[display_cols], use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, file_name=f"linkedin_service_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", key="csv_emails")
        with col2:
            json_data = df.to_json(orient='records', indent=2)
            st.download_button("Download JSON", json_data, file_name=f"linkedin_service_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json", key="json_emails")
        # Add a test scrape button for demo/debug
        if st.button("Test Scrape (Demo)"):
            st.info("Running test scrape with keyword 'gmail' and target 1 email...")
            # Minimal scrape logic for demo
            test_keywords = "gmail"
            test_num_emails = 1
            st.warning("This feature requires the scraping logic to be refactored into a callable function. Please ask the AI to do this if you want a working demo button.")
        st.write("Columns in results:", df.columns.tolist())
        st.write("First few rows of results:", df.head())
    else:
        display_cols = EXPECTED_COLS
    if debug_mode:
        display_cols.append('raw_content')
    st.dataframe(df[display_cols], use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, file_name=f"linkedin_service_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", key="csv_posts")
    with col2:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button("Download JSON", json_data, file_name=f"linkedin_service_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json", key="json_posts")

    # --- LLM enrichment: generate subject/body for each row, only on button click ---
    st.markdown("---")
    llm_delay = st.slider("Delay between LLM requests (seconds)", min_value=0.0, max_value=30.0, value=5.0, step=0.5)

    def generate_email_with_retries(email, content, llm_func, max_retries=3, delay=1.0, cooldown_callback=None):
        retries = 0
        llm_error = ""
        consecutive_429s = 0
        while retries <= max_retries:
            subject, body = llm_func(email, content)
            if (subject == "[Groq error]" or body == "[Groq error]" or subject == "[OpenAI error]" or body == "[OpenAI error]"):
                last_log = st.session_state.debug_log.split('\n')[-2] if st.session_state.debug_log else ""
                if "429" in last_log or "Too Many Requests" in last_log:
                    llm_error = "429 Too Many Requests - Retrying..."
                    consecutive_429s += 1
                    import time as pytime
                    pytime.sleep(delay)
                    delay = min(delay * 2, 30)
                    retries += 1
                    if consecutive_429s >= 3:
                        if cooldown_callback:
                            cooldown_callback()
                        st.warning("Groq rate limit hit 3 times in a row. Cooling down for 60 seconds...")
                        pytime.sleep(60)
                        consecutive_429s = 0
                    continue
                else:
                    llm_error = last_log or "LLM error"
            else:
                llm_error = ""
                consecutive_429s = 0
            break
        return subject, body, llm_error

    if st.button("Generate Email"):
        st.markdown("#### Personalized Email CSV")
        personalized_rows = []
        progress_bar = st.progress(0.0, text="Generating emails...")
        if st.session_state.get("api_provider") == "Groq":
            llm_func = call_groq_api
        else:
            llm_func = lambda email, content: call_openai_api(email, content, st.session_state.get("openai_api_key", ""))
        total = len(df)
        def cooldown_callback():
            st.warning("Groq rate limit hit 3 times in a row. Cooling down for 60 seconds...")
        for i, row in df.iterrows():
            email = row.get('email', '') if 'email' in row else ''
            context_content = row.get('raw_content', '') or row.get('content', '')
            prompt_content = f"""
You are a sales representative from Moshi Moshi, a branding and consultancy agency in Bangalore. Write a personalized outreach email based on the following full raw LinkedIn post content.\n\nRespond ONLY in valid JSON with keys: subject, body.\n- Subject: Max 10 words, catchy and relevant.\n- Body: Max 40 words, friendly, direct, and actionable.\n- Do NOT include any explanations or extra text.\n\nFull Raw LinkedIn Post Content:\n{context_content}
"""
            subject, body, llm_error = generate_email_with_retries(email, prompt_content, llm_func, max_retries=3, delay=llm_delay, cooldown_callback=cooldown_callback)
            result_row = {
                'email': email,
                'subject': subject,
                'body': body,
                'llm_error': llm_error
            }
            for col in EXPECTED_COLS:
                if col in row:
                    result_row[col] = row[col]
            personalized_rows.append(result_row)
            progress_bar.progress((i+1)/total, text=f"{i+1}/{total} emails generated")
            st.session_state["personalized_results"] = pd.DataFrame(personalized_rows)
            st.dataframe(st.session_state["personalized_results"], use_container_width=True)
            import time as pytime
            pytime.sleep(llm_delay)
        st.success("All emails generated!")
        csv = st.session_state["personalized_results"].to_csv(index=False)
        st.download_button("Download Personalized CSV", csv, file_name=f"linkedin_personalized_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", key="csv_personalized")
        
        # --- SMTP Email Sending Section ---
        st.markdown("### 📧 Send Emails via SMTP")
        
        # Check if SMTP credentials are configured
        smtp_email = st.session_state.get("smtp_email", "")
        smtp_password = st.session_state.get("smtp_password", "")
        
        if not smtp_email or not smtp_password:
            st.warning("⚠️ Please configure your Gmail SMTP credentials in the sidebar to send emails.")
        else:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                sender_name = st.text_input("Sender Name", value="Tanzeel from Moshi Moshi", key="sender_name_personalized")
                email_delay = st.slider("Delay between emails (seconds)", min_value=1.0, max_value=10.0, value=2.0, step=0.5, key="email_delay_personalized")
            
            with col2:
                # Filter emails that have valid email addresses and generated content
                valid_emails = st.session_state["personalized_results"][
                    (st.session_state["personalized_results"]['email'].notna()) & 
                    (st.session_state["personalized_results"]['email'] != '') &
                    (st.session_state["personalized_results"]['subject'].notna()) &
                    (st.session_state["personalized_results"]['body'].notna())
                ]
                
                st.info(f"📊 {len(valid_emails)} emails ready to send out of {len(st.session_state['personalized_results'])} total")
            
            if len(valid_emails) > 0:
                if st.button("🚀 Send All Emails", key="send_emails_personalized"):
                    # Prepare email data
                    email_data = []
                    for _, row in valid_emails.iterrows():
                        email_data.append({
                            'email': row['email'],
                            'subject': row['subject'],
                            'body': row['body']
                        })
                    
                    # Send emails
                    st.markdown("#### Email Sending Progress")
                    results = send_bulk_emails(
                        sender_email=smtp_email,
                        sender_password=smtp_password,
                        email_data=email_data,
                        delay_seconds=email_delay,
                        sender_name=sender_name
                    )
                    
                    # Display results
                    st.markdown("#### Email Sending Results")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Emails", results['total'])
                    with col2:
                        st.metric("Successfully Sent", results['sent'], delta=f"+{results['sent']}")
                    with col3:
                        st.metric("Failed", results['failed'], delta=f"-{results['failed']}" if results['failed'] > 0 else None)
                    
                    # Show detailed results
                    if st.checkbox("Show detailed results", key="show_email_details_personalized"):
                        results_df = pd.DataFrame(results['details'])
                        st.dataframe(results_df, use_container_width=True)
            else:
                st.warning("No valid emails found to send. Make sure your data has valid email addresses and generated content.")
else:
    st.info("No results yet. Run a search to see results here.")

# --- Manual CSV Upload and LLM Email Generation Section ---
st.markdown("---")
st.header("2. Upload CSV and Generate Emails")

uploaded_csv = st.file_uploader("Upload your CSV file (with at least an 'email' or 'content' column)", type=["csv"])
if uploaded_csv is not None:
    user_df = pd.read_csv(uploaded_csv)
    st.write("Preview of uploaded data:")
    st.dataframe(user_df, use_container_width=True)
    # Check for required columns
    if not any(col in user_df.columns for col in ["content", "raw_content"]):
        st.error("Your CSV must have a 'content' or 'raw_content' column for LLM email generation.")
    else:
        llm_delay = st.slider("Delay between LLM requests (seconds)", min_value=0.0, max_value=30.0, value=2.0, step=0.5, key="llm_delay_upload")
        if st.button("Generate Emails for Uploaded CSV"):
            st.markdown("#### Personalized Email CSV (from upload)")
            personalized_rows = []
            progress_bar = st.progress(0.0, text="Generating emails...")
            if st.session_state.get("api_provider") == "Groq":
                llm_func = call_groq_api
            else:
                llm_func = lambda email, content: call_openai_api(email, content, st.session_state.get("openai_api_key", ""))
            total = len(user_df)
            for i, row in user_df.iterrows():
                email = row.get('email', '') if 'email' in row else ''
                context_content = row.get('raw_content', '') or row.get('content', '')
                prompt_content = f"""
You are a sales representative from Moshi Moshi, a branding and consultancy agency in Bangalore. Write a personalized outreach email based on the following full raw LinkedIn post content.\n\nRespond ONLY in valid JSON with keys: subject, body.\n- Subject: Max 10 words, catchy and relevant.\n- Body: Max 40 words, friendly, direct, and actionable.\n- Do NOT include any explanations or extra text.\n\nFull Raw LinkedIn Post Content:\n{context_content}
"""
                subject, body, llm_error = generate_email_with_retries(email, prompt_content, llm_func, max_retries=3, delay=llm_delay)
                result_row = dict(row)
                result_row['subject'] = subject
                result_row['body'] = body
                result_row['llm_error'] = llm_error
                personalized_rows.append(result_row)
                progress_bar.progress((i+1)/total, text=f"{i+1}/{total} emails generated")
                st.session_state["personalized_upload_results"] = pd.DataFrame(personalized_rows)
                st.dataframe(st.session_state["personalized_upload_results"], use_container_width=True)
                import time as pytime
                pytime.sleep(llm_delay)
            st.success("All emails generated for uploaded CSV!")
            csv = st.session_state["personalized_upload_results"].to_csv(index=False)
            st.download_button("Download Personalized CSV", csv, file_name=f"uploaded_personalized_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", key="csv_personalized_upload")
            
            # --- SMTP Email Sending Section for Uploaded CSV ---
            st.markdown("### 📧 Send Emails via SMTP (Uploaded CSV)")
            
            # Check if SMTP credentials are configured
            smtp_email = st.session_state.get("smtp_email", "")
            smtp_password = st.session_state.get("smtp_password", "")
            
            if not smtp_email or not smtp_password:
                st.warning("⚠️ Please configure your Gmail SMTP credentials in the sidebar to send emails.")
            else:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    sender_name = st.text_input("Sender Name", value="Tanzeel from Moshi Moshi", key="sender_name_upload")
                    email_delay = st.slider("Delay between emails (seconds)", min_value=1.0, max_value=10.0, value=2.0, step=0.5, key="email_delay_upload")
                
                with col2:
                    # Filter emails that have valid email addresses and generated content
                    valid_emails = st.session_state["personalized_upload_results"][
                        (st.session_state["personalized_upload_results"]['email'].notna()) & 
                        (st.session_state["personalized_upload_results"]['email'] != '') &
                        (st.session_state["personalized_upload_results"]['subject'].notna()) &
                        (st.session_state["personalized_upload_results"]['body'].notna())
                    ]
                    
                    st.info(f"📊 {len(valid_emails)} emails ready to send out of {len(st.session_state['personalized_upload_results'])} total")
                
                if len(valid_emails) > 0:
                    if st.button("🚀 Send All Emails", key="send_emails_upload"):
                        # Prepare email data
                        email_data = []
                        for _, row in valid_emails.iterrows():
                            email_data.append({
                                'email': row['email'],
                                'subject': row['subject'],
                                'body': row['body']
                            })
                        
                        # Send emails
                        st.markdown("#### Email Sending Progress")
                        results = send_bulk_emails(
                            sender_email=smtp_email,
                            sender_password=smtp_password,
                            email_data=email_data,
                            delay_seconds=email_delay,
                            sender_name=sender_name
                        )
                        
                        # Display results
                        st.markdown("#### Email Sending Results")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Emails", results['total'])
                        with col2:
                            st.metric("Successfully Sent", results['sent'], delta=f"+{results['sent']}")
                        with col3:
                            st.metric("Failed", results['failed'], delta=f"-{results['failed']}" if results['failed'] > 0 else None)
                        
                        # Show detailed results
                        if st.checkbox("Show detailed results", key="show_email_details_upload"):
                            results_df = pd.DataFrame(results['details'])
                            st.dataframe(results_df, use_container_width=True)
                else:
                    st.warning("No valid emails found to send. Make sure your data has valid email addresses and generated content.")

st.markdown("---")
st.header("3. 📧 Send Emails from CSV File")
st.markdown("Upload a CSV file with email data and send personalized emails directly.")

# CSV file uploader for email sending
email_csv = st.file_uploader("Upload CSV file for email sending", type=["csv"], key="email_csv_uploader")

if email_csv is not None:
    try:
        email_df = pd.read_csv(email_csv)
        st.write("Preview of email data:")
        st.dataframe(email_df.head(10), use_container_width=True)
        
        # Check for required columns
        required_cols = ['email']
        missing_cols = [col for col in required_cols if col not in email_df.columns]
        
        if missing_cols:
            st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
            st.info("Your CSV must have at least an 'email' column. Optional columns: 'subject', 'body', 'name'")
        else:
            # Check SMTP configuration
            smtp_email = st.session_state.get("smtp_email", "")
            smtp_password = st.session_state.get("smtp_password", "")
            
            if not smtp_email or not smtp_password:
                st.warning("⚠️ Please configure your Gmail SMTP credentials in the sidebar to send emails.")
            else:
                # Email sending configuration
                st.markdown("### Email Configuration")
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    sender_name_csv = st.text_input("Sender Name", value="Tanzeel from Moshi Moshi", key="sender_name_csv")
                    email_delay_csv = st.slider("Delay between emails (seconds)", min_value=1.0, max_value=10.0, value=2.0, step=0.5, key="email_delay_csv")
                
                with col2:
                    # Default subject and body if not in CSV
                    default_subject = st.text_input("Default Subject (if not in CSV)", value="Hello from Moshi Moshi", key="default_subject_csv")
                    default_body = st.text_area("Default Body (if not in CSV)", value="Thank you for connecting! We'd love to discuss how Moshi Moshi can help with your branding needs.", key="default_body_csv")
                
                # Filter valid emails
                valid_email_df = email_df[email_df['email'].notna() & (email_df['email'] != '')]
                
                st.info(f"📊 {len(valid_email_df)} valid emails found out of {len(email_df)} total rows")
                
                # Preview email data that will be sent
                if st.checkbox("Preview email data to be sent", key="preview_csv_emails"):
                    preview_data = []
                    for _, row in valid_email_df.head(5).iterrows():
                        preview_data.append({
                            'email': row['email'],
                            'subject': row.get('subject', default_subject),
                            'body': row.get('body', default_body)[:100] + '...' if len(str(row.get('body', default_body))) > 100 else row.get('body', default_body)
                        })
                    
                    st.dataframe(pd.DataFrame(preview_data), use_container_width=True)
                    if len(valid_email_df) > 5:
                        st.caption(f"Showing first 5 rows. Total: {len(valid_email_df)} emails will be sent.")
                
                # Send emails button
                if len(valid_email_df) > 0:
                    if st.button("🚀 Send All Emails from CSV", key="send_csv_emails"):
                        # Prepare email data
                        email_data = []
                        for _, row in valid_email_df.iterrows():
                            email_data.append({
                                'email': row['email'],
                                'subject': row.get('subject', default_subject),
                                'body': row.get('body', default_body)
                            })
                        
                        # Send emails
                        st.markdown("#### Email Sending Progress")
                        results = send_bulk_emails(
                            sender_email=smtp_email,
                            sender_password=smtp_password,
                            email_data=email_data,
                            delay_seconds=email_delay_csv,
                            sender_name=sender_name_csv
                        )
                        
                        # Display results
                        st.markdown("#### Email Sending Results")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Emails", results['total'])
                        with col2:
                            st.metric("Successfully Sent", results['sent'], delta=f"+{results['sent']}")
                        with col3:
                            st.metric("Failed", results['failed'], delta=f"-{results['failed']}" if results['failed'] > 0 else None)
                        
                        # Show detailed results
                        if st.checkbox("Show detailed sending results", key="show_csv_email_details"):
                            results_df = pd.DataFrame(results['details'])
                            st.dataframe(results_df, use_container_width=True)
                            
                            # Download results as CSV
                            results_csv = results_df.to_csv(index=False)
                            st.download_button(
                                "📥 Download Sending Results",
                                results_csv,
                                file_name=f"email_sending_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                key="download_csv_results"
                            )
                else:
                    st.warning("No valid emails found in the CSV file.")
                    
    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")
        st.info("Please make sure your CSV file is properly formatted and contains the required columns.")

# CSV format help
with st.expander("📋 CSV Format Requirements"):
    st.markdown("""
    **Required Column:**
    - `email`: Email addresses to send to
    
    **Optional Columns:**
    - `subject`: Custom subject line for each email
    - `body`: Custom email body for each email
    - `name`: Recipient name (can be used in email body)
    
    **Example CSV format:**
    ```
    email,subject,body,name
    john@example.com,"Hello John","Hi John, we'd love to connect!",John Doe
    jane@example.com,"Hello Jane","Hi Jane, let's discuss your project!",Jane Smith
    ```
    
    **Note:** If `subject` or `body` columns are missing, the default values you specify above will be used.
    """)

st.markdown("---")
st.markdown("<small>Use responsibly. This tool is for commercial purposes only. Comply with LinkedIn's Terms of Service.</small>", unsafe_allow_html=True)
