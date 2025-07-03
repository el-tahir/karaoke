"""
YouTube Cookies Helper for Karaoke App

This module provides utilities and instructions for extracting YouTube cookies
to bypass bot detection when downloading videos.

IMPORTANT: Never share your cookies publicly as they contain your authentication tokens.
"""

import os
from pathlib import Path


def get_cookie_instructions() -> str:
    """Return detailed instructions for extracting YouTube cookies."""
    return """
🍪 HOW TO EXTRACT YOUTUBE COOKIES FOR KARAOKE APP

1. **Chrome/Edge Browser Method:**
   a) Go to youtube.com and make sure you're logged in
   b) Press F12 to open Developer Tools
   c) Go to Application tab → Storage → Cookies → https://www.youtube.com
   d) Look for these important cookies: 
      - __Secure-3PSID
      - __Secure-3PAPISID  
      - HSID
      - SSID
      - APISID
      - SAPISID
   e) Right-click any cookie → "Copy all as Netscape format"

2. **Firefox Browser Method:**
   a) Install "cookies.txt" browser extension
   b) Go to youtube.com (make sure you're logged in)
   c) Click the extension icon
   d) Click "Export" to get cookies in Netscape format

3. **Using the Cookies:**

   **Method A - Environment Variable (Recommended for Cloud Run):**
   Set the YOUTUBE_COOKIES environment variable with your cookie content.

   **Method B - API Parameter:**
   Pass cookies directly in the request (not recommended for production).

   **Method C - Local Development:**
   Save cookies to a file and set YOUTUBE_COOKIES to the file path.

⚠️  SECURITY WARNINGS:
- Never commit cookies to version control
- Don't share cookies in public channels
- Cookies expire and may need refreshing
- Use environment variables for production deployment

💡 CLOUD RUN DEPLOYMENT:
1. Go to Cloud Run console
2. Select your karaoke-backend service  
3. Click "Edit & Deploy New Revision"
4. Under "Variables & Secrets" → "Environment Variables"
5. Add: Name=YOUTUBE_COOKIES, Value=[your cookie content]
6. Deploy the new revision

🔄 TESTING:
Once configured, the app will automatically use cookies for YouTube downloads.
No additional changes needed in your requests.
"""


def validate_cookies(cookies_content: str) -> bool:
    """Validate if the cookies content looks correct."""
    if not cookies_content:
        return False
    
    # Check for Netscape format header
    if cookies_content.startswith("# Netscape HTTP Cookie File"):
        return True
    
    # Check for tab-separated values (cookie format)
    lines = cookies_content.strip().split('\n')
    for line in lines:
        if line.startswith('#'):
            continue
        if line.strip() and '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 6:  # Basic cookie format validation
                return True
    
    return False


def setup_cookies_for_cloud_run() -> str:
    """Return instructions specific to Cloud Run deployment."""
    return """
🚀 CLOUD RUN COOKIE SETUP:

1. Extract cookies using the browser method above
2. In Google Cloud Console:
   - Go to Cloud Run
   - Select "karaoke-backend" service
   - Click "Edit & Deploy New Revision"
   - Scroll to "Variables & Secrets"
   - Click "Add Variable"
   - Name: YOUTUBE_COOKIES
   - Value: [paste your entire cookie content]
   - Click "Deploy"

3. Test the deployment:
   - Try a YouTube URL that was previously blocked
   - Check logs for successful download

The cookies will be automatically used for all YouTube requests.
"""


if __name__ == "__main__":
    print(get_cookie_instructions()) 