# telegram_api.py - Enhanced with Phone Number Detection

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time
import warnings
warnings.filterwarnings("ignore")

app = Flask(__name__)
CORS(app)

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
    
    def find_phone_number(self, username, page_text, soup):
        """Multiple methods to find phone number"""
        phone_number = None
        
        # Method 1: Check bio for phone number
        bio_elem = soup.find('div', {'class': 'tgme_page_description'})
        if bio_elem:
            bio_text = bio_elem.text.strip()
            if bio_text:
                # Phone number patterns
                phone_patterns = [
                    r'\+?\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
                    r'\+?\d{1,3}[\s\-]?\d{4,5}[\s\-]?\d{4,5}',
                    r'\+?\d{10,15}',
                    r'\d{4}[\s\-]?\d{3}[\s\-]?\d{4}',
                    r'\d{3}[\s\-]?\d{3}[\s\-]?\d{4}',
                    r'\d{11,15}'
                ]
                
                for pattern in phone_patterns:
                    phone_match = re.search(pattern, bio_text)
                    if phone_match:
                        phone_number = phone_match.group(0)
                        break
        
        # Method 2: Check username if it contains number
        if not phone_number:
            # Some users put phone in username
            username_pattern = r'\+?\d{10,15}'
            phone_match = re.search(username_pattern, username)
            if phone_match:
                phone_number = phone_match.group(0)
        
        # Method 3: Check page text for phone number
        if not phone_number:
            phone_patterns = [
                r'\+?\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
                r'\+?\d{10,15}'
            ]
            for pattern in phone_patterns:
                phone_match = re.search(pattern, page_text)
                if phone_match:
                    phone_number = phone_match.group(0)
                    break
        
        # Method 4: Search Google for phone number
        if not phone_number:
            try:
                search_url = f"https://www.google.com/search?q={username}+telegram+phone+number"
                response = self.session.get(search_url, timeout=5)
                if response.status_code == 200:
                    phone_patterns = [
                        r'\+?\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
                        r'\+?\d{10,15}'
                    ]
                    for pattern in phone_patterns:
                        phone_match = re.search(pattern, response.text)
                        if phone_match:
                            phone_number = phone_match.group(0)
                            break
            except:
                pass
        
        # Method 5: Check if phone is in display name
        if not phone_number:
            name_elem = soup.find('div', {'class': 'tgme_page_title'})
            if name_elem:
                name_text = name_elem.text.strip()
                if name_text:
                    phone_patterns = [
                        r'\+?\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
                        r'\+?\d{10,15}'
                    ]
                    for pattern in phone_patterns:
                        phone_match = re.search(pattern, name_text)
                        if phone_match:
                            phone_number = phone_match.group(0)
                            break
        
        return phone_number
    
    def fetch_by_username(self, username):
        """Fetch user info by username"""
        try:
            url = f"https://t.me/{username}"
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code != 200:
                return {"success": False, "error": "User not found"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = response.text
            
            result = {
                "success": True,
                "username": username,
                "full_name": None,
                "first_name": None,
                "last_name": None,
                "bio": None,
                "phone_number": None,
                "phone_found": False,
                "profile_pic": None,
                "verified": False,
                "scam": False,
                "fake": False,
                "restricted": False,
                "type": "user",
                "members_count": None,
                "last_seen": None,
                "online_status": None,
                "url": f"https://t.me/{username}",
                "website": None,
                "location": None,
                "id": None,
                "join_date": None,
                "phone_method": None
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
            
            # FIND PHONE NUMBER - Enhanced
            phone_data = self.find_phone_number(username, page_text, soup)
            if phone_data:
                result['phone_number'] = phone_data
                result['phone_found'] = True
                # Determine how phone was found
                if phone_data in str(result.get('bio', '')):
                    result['phone_method'] = "Found in bio"
                elif phone_data in username:
                    result['phone_method'] = "Found in username"
                elif phone_data in str(result.get('full_name', '')):
                    result['phone_method'] = "Found in display name"
                else:
                    result['phone_method'] = "Found in page source"
            
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
            
            # Get last seen / online status
            if "online" in page_text.lower():
                result['last_seen'] = "Online"
                result['online_status'] = "online"
            elif "last seen" in page_text.lower():
                match = re.search(r'last seen (.+?)[<\.]', page_text, re.IGNORECASE)
                if match:
                    result['last_seen'] = match.group(1).strip()
                    result['online_status'] = "offline"
            else:
                result['last_seen'] = "Hidden/Private"
                result['online_status'] = "hidden"
            
            # Try to get user ID
            id_match = re.search(r'"user_id":(\d+)', page_text)
            if id_match:
                result['id'] = int(id_match.group(1))
            
            # Get website
            website_elem = soup.find('a', {'class': 'tgme_page_website'})
            if website_elem:
                website_text = website_elem.text.strip()
                if website_text:
                    result['website'] = website_text
            
            # Get location
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
            search_url = f"https://www.google.com/search?q=telegram+user+id+{user_id}"
            try:
                response = self.session.get(search_url, timeout=5)
                if response.status_code == 200:
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
        "version": "3.0.0",
        "status": "active",
        "features": {
            "phone_number": "Auto-detects phone numbers from bio, username, display name, and page source",
            "username": "Support for @username, username, t.me/username",
            "id": "Support for Telegram IDs"
        },
        "endpoints": {
            "/info": "GET - /info?telegram=USERNAME",
            "/info": "GET - /info?telegram=USER_ID",
            "/phone": "GET - /phone?telegram=USERNAME - Only phone number"
        },
        "examples": {
            "by_username": "/info?telegram=durov",
            "by_id": "/info?telegram=6762399638"
        }
    })

@app.route('/info')
def get_telegram_info():
    telegram_input = request.args.get('telegram')
    
    if not telegram_input:
        return jsonify({
            "success": False,
            "error": "Missing telegram parameter",
            "usage": "/info?telegram=username",
            "examples": {
                "by_username": "/info?telegram=durov",
                "by_id": "/info?telegram=6762399638"
            },
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
        return jsonify(result)
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/phone')
def get_phone_only():
    """Only get phone number"""
    telegram_input = request.args.get('telegram')
    
    if not telegram_input:
        return jsonify({
            "success": False,
            "error": "Missing telegram parameter",
            "usage": "/phone?telegram=username"
        }), 400
    
    try:
        result = api.fetch_user_info(telegram_input)
        
        if not result.get('success'):
            return jsonify({
                "success": False,
                "error": result.get('error', 'User not found')
            }), 404
        
        return jsonify({
            "success": True,
            "username": result.get('username'),
            "phone_number": result.get('phone_number'),
            "phone_found": result.get('phone_found', False),
            "phone_method": result.get('phone_method'),
            "timestamp": datetime.now().isoformat()
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Vercel handler
def handler(request):
    return app(request)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
