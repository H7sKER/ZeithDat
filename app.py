# telegram_api.py - Complete Telegram API with ID Support & Encryption Key

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
    
    @staticmethod
    def decrypt_data(encrypted_data):
        try:
            combined = base64.b64decode(encrypted_data)
            iv = combined[:16]
            encrypted = combined[16:]
            cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
            return json.loads(decrypted.decode('utf-8'))
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
        
        # Remove @ if present
        if user_input.startswith('@'):
            user_input = user_input[1:]
        
        # Remove spaces
        user_input = user_input.replace(' ', '')
        
        # Remove t.me/ if present
        if 't.me/' in user_input:
            user_input = user_input.split('t.me/')[-1]
        if 'telegram.me/' in user_input:
            user_input = user_input.split('telegram.me/')[-1]
        
        # Clean username
        user_input = re.sub(r'[^a-zA-Z0-9_]', '', user_input)
        
        return user_input
    
    def fetch_by_username(self, username):
        """Fetch user info by username"""
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
                "id": None
            }
            
            # Get username
            username_elem = soup.find('div', {'class': 'tgme_page_extra'})
            if username_elem:
                username_text = username_elem.text.strip()
                if username_text:
                    result['username'] = username_text.replace('@', '')
            
            # Get full name
            name_elem = soup.find('div', {'class': 'tgme_page_title'})
            if name_elem:
                name_text = name_elem.text.strip()
                if name_text:
                    result['full_name'] = name_text
                    name_parts = name_text.split()
                    if name_parts:
                        result['first_name'] = name_parts[0]
                        if len(name_parts) > 1:
                            result['last_name'] = ' '.join(name_parts[1:])
            
            # Get bio
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
            
            # Get last seen
            if "last seen" in response.text:
                match = re.search(r'last seen (.+?)[<\.]', response.text)
                if match:
                    result['last_seen'] = match.group(1)
            elif "online" in response.text.lower():
                result['last_seen'] = "Online"
            
            # Try to get user ID from page
            id_match = re.search(r'"user_id":(\d+)', response.text)
            if id_match:
                result['id'] = int(id_match.group(1))
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def fetch_by_id(self, user_id):
        """Fetch user info by Telegram ID"""
        try:
            # Method 1: Try to find username from public groups/channels
            # Search for the ID in Google
            search_url = f"https://www.google.com/search?q=telegram+user+id+{user_id}"
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
            
            # Method 2: Try using Telegram's internal API (unofficial)
            # Note: This is an estimation, actual ID lookup requires official API
            # Try to get from t.me links with numeric IDs
            test_urls = [
                f"https://t.me/{user_id}",
                f"https://t.me/+{user_id}",
                f"https://t.me/c/{user_id}"
            ]
            
            for url in test_urls:
                try:
                    response = self.session.get(url, timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Check if it's a valid page
                        if "tgme_page" in response.text:
                            # Try to extract username
                            username_elem = soup.find('div', {'class': 'tgme_page_extra'})
                            if username_elem:
                                username_text = username_elem.text.strip()
                                if username_text:
                                    username = username_text.replace('@', '')
                                    result = self.fetch_by_username(username)
                                    if result.get('success'):
                                        result['id'] = user_id
                                        return result
                except:
                    continue
            
            # Method 3: Check if it's a channel/group ID
            try:
                # Some channel IDs are accessible
                url = f"https://t.me/c/{user_id}"
                response = self.session.get(url, timeout=5)
                if response.status_code == 200 and "Channel" in response.text:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title_elem = soup.find('div', {'class': 'tgme_page_title'})
                    if title_elem:
                        return {
                            "success": True,
                            "id": user_id,
                            "type": "channel",
                            "full_name": title_elem.text.strip(),
                            "username": None,
                            "url": url
                        }
            except:
                pass
            
            return {
                "success": False,
                "error": f"Could not find user with ID: {user_id}",
                "id": user_id,
                "note": "Telegram IDs are not publicly searchable without username"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def fetch_user_info(self, user_input):
        """Main function to fetch user info by username or ID"""
        user_input = str(user_input).strip()
        
        # Check if it's a numeric ID
        if user_input.isdigit() and len(user_input) >= 5:
            return self.fetch_by_id(user_input)
        
        # Otherwise treat as username
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

# ==================== API ENDPOINTS ====================

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
        },
        "examples": {
            "by_username": "/info?telegram=durov&key=HACKER",
            "by_id": "/info?telegram=6762399638&key=HACKER",
            "with_at": "/info?telegram=@durov&key=HACKER",
        }
    })

@app.route('/info')
def get_telegram_info():
    # Get parameters
    telegram_input = request.args.get('telegram')
    user_key = request.args.get('key')
    
    # Check if key is provided
    if not user_key:
        return jsonify({
            "success": False,
            "error": "KEY IS MISSING!",
            "message": "You need to provide encryption key",
            "required_key": "HACKER",
            "usage": "/info?telegram=username&key=HACKER",
            "timestamp": datetime.now().isoformat()
        }), 401
    
    # Check if key is valid
    if user_key != VALID_KEY:
        return jsonify({
            "success": False,
            "error": "INVALID KEY! ACCESS DENIED",
            "message": "Wrong encryption key provided",
            "timestamp": datetime.now().isoformat()
        }), 403
    
    # Check if telegram parameter is provided
    if not telegram_input:
        return jsonify({
            "success": False,
            "error": "Missing telegram parameter",
            "message": "Please provide username or ID",
            "usage": "/info?telegram=username&key=HACKER",
            "examples": {
                "by_username": "/info?telegram=durov&key=HACKER",
                "by_id": "/info?telegram=6762399638&key=HACKER"
            },
            "timestamp": datetime.now().isoformat()
        }), 400
    
    try:
        # Fetch user info
        result = api.fetch_user_info(telegram_input)
        
        if not result.get('success'):
            return jsonify({
                "success": False,
                "error": result.get('error', 'User not found'),
                "input": telegram_input,
                "timestamp": datetime.now().isoformat()
            }), 404
        
        # Add timestamp
        result['timestamp'] = datetime.now().isoformat()
        result['encrypted'] = True
        
        # Encrypt the response
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
            # If encryption fails, return raw (should not happen)
            return jsonify(result)
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/decrypt')
def decrypt_data():
    """Endpoint to decrypt data (for testing)"""
    encrypted_data = request.args.get('data')
    user_key = request.args.get('key')
    
    if not user_key:
        return jsonify({
            "success": False,
            "error": "KEY IS MISSING!",
            "required_key": "HACKER"
        }), 401
    
    if user_key != VALID_KEY:
        return jsonify({
            "success": False,
            "error": "INVALID KEY!"
        }), 403
    
    if not encrypted_data:
        return jsonify({
            "success": False,
            "error": "Missing data parameter"
        }), 400
    
    decrypted = EncryptionManager.decrypt_data(encrypted_data)
    
    if decrypted:
        return jsonify({
            "success": True,
            "decrypted_data": decrypted
        })
    else:
        return jsonify({
            "success": False,
            "error": "Decryption failed"
        }), 400

@app.route('/validate')
def validate_input():
    """Validate if input is username or ID"""
    input_value = request.args.get('input')
    user_key = request.args.get('key')
    
    if not user_key:
        return jsonify({
            "success": False,
            "error": "KEY IS MISSING!",
            "required_key": "HACKER"
        }), 401
    
    if user_key != VALID_KEY:
        return jsonify({
            "success": False,
            "error": "INVALID KEY!"
        }), 403
    
    if not input_value:
        return jsonify({
            "success": False,
            "error": "Missing input parameter"
        }), 400
    
    is_id = input_value.isdigit() and len(input_value) >= 5
    is_username = bool(re.match(r'^[a-zA-Z0-9_]{5,}$', input_value))
    
    return jsonify({
        "success": True,
        "input": input_value,
        "type": "id" if is_id else "username" if is_username else "unknown",
        "is_id": is_id,
        "is_username": is_username
    })

# Vercel handler
def handler(request):
    return app(request)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
