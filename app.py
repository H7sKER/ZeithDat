# telegram_api.py - Improved Version with Better Data Extraction

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import os
import time
import warnings
warnings.filterwarnings("ignore")

app = Flask(__name__)
CORS(app)

# ==================== ENCRYPTION CONFIG ====================
VALID_KEY = "HACKER"
SECRET_KEY = hashlib.sha256(VALID_KEY.encode()).digest()

class EncryptionManager:
    @staticmethod
    def encrypt_data(data):
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            iv = os.urandom(16)
            cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
            combined = iv + encrypted
            return base64.b64encode(combined).decode('utf-8')
        except:
            return None

class TelegramUserInfo:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def extract_username(self, user_input):
        """Extract username from various formats"""
        user_input = str(user_input).strip()
        
        if user_input.startswith('@'):
            user_input = user_input[1:]
        
        user_input = user_input.replace(' ', '')
        
        if 't.me/' in user_input:
            user_input = user_input.split('t.me/')[-1]
        if 'telegram.me/' in user_input:
            user_input = user_input.split('telegram.me/')[-1]
        
        user_input = re.sub(r'[^a-zA-Z0-9_]', '', user_input)
        
        return user_input
    
    def fetch_by_username(self, username):
        """Fetch user info by username with improved extraction"""
        try:
            url = f"https://t.me/{username}"
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code != 200:
                return {"success": False, "error": "User not found"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result = {
                "success": True,
                "username": username,
                "full_name": None,
                "first_name": None,
                "last_name": None,
                "bio": None,
                "phone_number": None,
                "profile_pic": None,
                "verified": False,
                "scam": False,
                "fake": False,
                "restricted": False,
                "type": "user",
                "members_count": None,
                "last_seen": None,
                "url": f"https://t.me/{username}",
                "website": None,
                "location": None,
                "id": None,
                "join_date": None,
                "online_status": None
            }
            
            # Get username
            username_elem = soup.find('div', {'class': 'tgme_page_extra'})
            if username_elem:
                username_text = username_elem.text.strip()
                if username_text:
                    result['username'] = username_text.replace('@', '')
            
            # Get full name (improved)
            name_elem = soup.find('div', {'class': 'tgme_page_title'})
            if name_elem:
                name_text = name_elem.text.strip()
                if name_text:
                    result['full_name'] = name_text
                    # Try to split name
                    name_parts = name_text.split()
                    if name_parts:
                        result['first_name'] = name_parts[0]
                        if len(name_parts) > 1:
                            result['last_name'] = ' '.join(name_parts[1:])
            
            # Get bio (improved)
            bio_elem = soup.find('div', {'class': 'tgme_page_description'})
            if bio_elem:
                bio_text = bio_elem.text.strip()
                if bio_text:
                    result['bio'] = bio_text
            
            # Get profile picture
            img_elem = soup.find('img', {'class': 'tgme_page_photo_image'})
            if img_elem and img_elem.get('src'):
                result['profile_pic'] = img_elem.get('src')
            
            # Check verified
            if soup.find('span', {'class': 'verified'}):
                result['verified'] = True
            
            # Check scam
            if soup.find('span', {'class': 'scam'}):
                result['scam'] = True
            
            # Check fake
            if soup.find('span', {'class': 'fake'}):
                result['fake'] = True
            
            # Check if channel
            if soup.find('div', {'class': 'tgme_channel_info'}):
                result['type'] = 'channel'
                members_elem = soup.find('div', {'class': 'tgme_channel_info_members'})
                if members_elem:
                    members_text = members_elem.text.strip()
                    numbers = re.findall(r'\d+', members_text)
                    if numbers:
                        result['members_count'] = int(numbers[0])
            
            # IMPROVED: Get last seen / online status
            page_text = response.text
            if "online" in page_text.lower():
                result['last_seen'] = "Online"
                result['online_status'] = "online"
            elif "last seen" in page_text.lower():
                # Extract last seen
                match = re.search(r'last seen (.+?)[<\.]', page_text, re.IGNORECASE)
                if match:
                    result['last_seen'] = match.group(1).strip()
                    result['online_status'] = "offline"
                else:
                    # Try different pattern
                    match = re.search(r'Last seen (.+?)(?:<|\.|\n)', page_text, re.IGNORECASE)
                    if match:
                        result['last_seen'] = match.group(1).strip()
                        result['online_status'] = "offline"
            elif "last seen" not in page_text and "online" not in page_text.lower():
                result['last_seen'] = "Hidden/Private"
                result['online_status'] = "hidden"
            
            # IMPROVED: Try to get user ID from multiple sources
            # Method 1: From page source
            id_match = re.search(r'"user_id":(\d+)', page_text)
            if id_match:
                result['id'] = int(id_match.group(1))
            else:
                # Method 2: From other patterns
                id_match = re.search(r'user_id["\s:=]+(\d+)', page_text)
                if id_match:
                    result['id'] = int(id_match.group(1))
                else:
                    # Method 3: From channel/group ID
                    id_match = re.search(r'channel_id["\s:=]+(\d+)', page_text)
                    if id_match:
                        result['id'] = int(id_match.group(1))
            
            # IMPROVED: Try to get phone number (rarely available)
            # Check if phone number is in bio
            if result['bio']:
                # Look for phone number patterns in bio
                phone_patterns = [
                    r'\+?\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
                    r'\+\d{10,15}',
                    r'\d{4}[\s\-]?\d{3}[\s\-]?\d{4}',
                    r'\d{11,15}'
                ]
                
                for pattern in phone_patterns:
                    phone_match = re.search(pattern, result['bio'])
                    if phone_match:
                        result['phone_number'] = phone_match.group(0)
                        break
            
            # IMPROVED: Get join date / creation info
            date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', page_text)
            if date_match:
                result['join_date'] = date_match.group(1)
            
            # Get website if available
            website_elem = soup.find('a', {'class': 'tgme_page_website'})
            if website_elem:
                website_text = website_elem.text.strip()
                if website_text:
                    result['website'] = website_text
            
            # Get location if available
            location_elem = soup.find('div', {'class': 'tgme_page_location'})
            if location_elem:
                location_text = location_elem.text.strip()
                if location_text:
                    result['location'] = location_text
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def fetch_by_id(self, user_id):
        """Fetch user info by Telegram ID"""
        try:
            # Search for username from ID
            search_url = f"https://www.google.com/search?q=telegram+{user_id}"
            try:
                response = self.session.get(search_url, timeout=5)
                if response.status_code == 200:
                    # Look for username patterns
                    username_patterns = [
                        r't\.me/([a-zA-Z0-9_]+)',
                        r'telegram\.me/([a-zA-Z0-9_]+)',
                        r'@([a-zA-Z0-9_]+)'
                    ]
                    
                    for pattern in username_patterns:
                        matches = re.findall(pattern, response.text)
                        if matches:
                            username = matches[0]
                            result = self.fetch_by_username(username)
                            if result.get('success'):
                                result['id'] = user_id
                                return result
            except:
                pass
            
            return {
                "success": False,
                "error": f"Could not find user with ID: {user_id}",
                "id": user_id
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def fetch_user_info(self, user_input):
        """Main function to fetch user info"""
        user_input = str(user_input).strip()
        
        if user_input.isdigit() and len(user_input) >= 5:
            return self.fetch_by_id(user_input)
        
        username = self.extract_username(user_input)
        if not username:
            return {
                "success": False,
                "error": "Invalid username format",
                "input": user_input
            }
        
        return self.fetch_by_username(username)

# Initialize API
api = TelegramUserInfo()

@app.route('/')
def home():
    return jsonify({
        "service": "Telegram User Info API",
        "version": "2.0.0",
        "status": "active",
        "encryption": "AES-256-CBC",
        "key_required": "HACKER",
        "endpoints": {
            "/info": "GET - /info?telegram=USERNAME&key=HACKER",
            "/info": "GET - /info?telegram=USER_ID&key=HACKER",
        }
    })

@app.route('/info')
def get_telegram_info():
    telegram_input = request.args.get('telegram')
    user_key = request.args.get('key')
    
    if not user_key:
        return jsonify({
            "success": False,
            "error": "KEY IS MISSING!",
            "required_key": "HACKER",
            "usage": "/info?telegram=username&key=HACKER",
            "timestamp": datetime.now().isoformat()
        }), 401
    
    if user_key != VALID_KEY:
        return jsonify({
            "success": False,
            "error": "INVALID KEY! ACCESS DENIED",
            "timestamp": datetime.now().isoformat()
        }), 403
    
    if not telegram_input:
        return jsonify({
            "success": False,
            "error": "Missing telegram parameter",
            "usage": "/info?telegram=username&key=HACKER",
            "timestamp": datetime.now().isoformat()
        }), 400
    
    try:
        result = api.fetch_user_info(telegram_input)
        
        if not result.get('success'):
            return jsonify({
                "success": False,
                "error": result.get('error', 'User not found'),
                "input": telegram_input,
                "timestamp": datetime.now().isoformat()
            }), 404
        
        result['timestamp'] = datetime.now().isoformat()
        result['encrypted'] = True
        
        encrypted_response = EncryptionManager.encrypt_data(result)
        
        if encrypted_response:
            return jsonify({
                "success": True,
                "encrypted": True,
                "data": encrypted_response,
                "message": "Response encrypted with key: HACKER",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify(result)
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# Vercel handler
def handler(request):
    return app(request)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
