"""
Configuration management for Mo Scraper application.
"""

import os
from dataclasses import dataclass
from typing import List, Optional
import streamlit as st


@dataclass
class APIConfig:
    """API configuration settings."""
    groq_api_key: Optional[str] = None
    groq_api_url: str = "https://api.groq.com/openai/v1/chat/completions"
    groq_models: List[str] = None
    groq_model_default: str = "llama-3.3-70b-versatile"
    openai_api_key: Optional[str] = None
    openai_api_url: str = "https://api.openai.com/v1/chat/completions"
    
    def __post_init__(self):
        if self.groq_models is None:
            self.groq_models = [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
                "mixtral-8x7b-32768"
            ]


@dataclass
class SMTPConfig:
    """SMTP configuration settings."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: Optional[str] = None
    sender_password: Optional[str] = None
    sender_name: str = "Tanzeel from Moshi Moshi"


@dataclass
class ScrapingConfig:
    """Scraping configuration settings."""
    max_parallel_browsers: int = 2
    default_delay: float = 2.0
    max_delay: float = 10.0
    headless_mode: bool = False
    user_agents: List[str] = None
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            ]


@dataclass
class AppConfig:
    """Main application configuration."""
    app_name: str = "Mo Scraper"
    version: str = "2.0.0"
    debug_mode: bool = False
    max_debug_log_length: int = 5000
    cookies_file: str = "linkedin_cookies.pkl"
    
    # Sub-configurations
    api: APIConfig = None
    smtp: SMTPConfig = None
    scraping: ScrapingConfig = None
    
    def __post_init__(self):
        if self.api is None:
            self.api = APIConfig()
        if self.smtp is None:
            self.smtp = SMTPConfig()
        if self.scraping is None:
            self.scraping = ScrapingConfig()


class ConfigManager:
    """Manages application configuration with Streamlit session state integration."""
    
    def __init__(self):
        self.config = AppConfig()
        self._load_from_session_state()
    
    def _load_from_session_state(self):
        """Load configuration from Streamlit session state."""
        # API Configuration
        self.config.api.groq_api_key = st.session_state.get("groq_api_key")
        self.config.api.openai_api_key = st.session_state.get("openai_api_key")
        
        # SMTP Configuration
        self.config.smtp.sender_email = st.session_state.get("smtp_email")
        self.config.smtp.sender_password = st.session_state.get("smtp_password")
        
        # Other settings
        self.config.debug_mode = st.session_state.get("debug_mode", False)
    
    def save_to_session_state(self):
        """Save configuration to Streamlit session state."""
        if self.config.api.groq_api_key:
            st.session_state["groq_api_key"] = self.config.api.groq_api_key
        if self.config.api.openai_api_key:
            st.session_state["openai_api_key"] = self.config.api.openai_api_key
        if self.config.smtp.sender_email:
            st.session_state["smtp_email"] = self.config.smtp.sender_email
        if self.config.smtp.sender_password:
            st.session_state["smtp_password"] = self.config.smtp.sender_password
    
    def is_api_configured(self, provider: str = "groq") -> bool:
        """Check if API is properly configured."""
        if provider.lower() == "groq":
            return bool(self.config.api.groq_api_key)
        elif provider.lower() == "openai":
            return bool(self.config.api.openai_api_key)
        return False
    
    def is_smtp_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(self.config.smtp.sender_email and self.config.smtp.sender_password)
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration."""
        return self.config.api
    
    def get_smtp_config(self) -> SMTPConfig:
        """Get SMTP configuration."""
        return self.config.smtp
    
    def get_scraping_config(self) -> ScrapingConfig:
        """Get scraping configuration."""
        return self.config.scraping


# Global configuration instance
config_manager = ConfigManager()
