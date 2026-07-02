# telegram_api.py - Complete Telegram User Info API

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
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
        
        # Try to get info from multiple sources
        self.telegram_urls = [
            "https://t.me/{}",
            "https://telegram.me/{}",
            "https://t.me/s/{}",
            "https://telegram.dog/{}"
        ]
    
    def extract_username(self, user_input):
        """Extract username from various formats"""
        # Remove @ if present
        username = user_input.strip()
        if username.startswith('@'):
            username = username[1:]
        
        # Remove spaces
        username = username.replace(' ', '')
        
        # Remove t.me/ if present
        if 't.me/' in username:
            username = username.split('t.me/')[-1]
        if 'telegram.me/' in username:
            username = username.split('telegram.me/')[-1]
        if 'telegram.dog/' in username:
            username = username.split('telegram.dog/')[-1]
        
        # Only allow alphanumeric and underscore
        username = re.sub(r'[^a-zA-Z0-9_]', '', username)
        
        return username
    
    def fetch_user_info(self, username):
        """Fetch complete user info from Telegram"""
        clean_username = self.extract_username(username)
        
        if not clean_username:
            return {
                "success": False,
                "error": "Invalid username format"
            }
        
        result = {
            "success": False,
            "username": clean_username,
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
            "type": "user",  # user, channel, group, bot
            "members_count": None,
            "channel_title": None,
            "channel_description": None,
            "last_seen": None,
            "status": None,  # online, offline, recently, last seen
            "url": None,
            "website": None,
            "location": None,
            "groups_in_common": None,
            "created_date": None,
            "id": None
        }
        
        # Try all URL formats
        for url_template in self.telegram_urls:
            try:
                url = url_template.format(clean_username)
                response = self.session.get(url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check if it's a valid Telegram page
                    if "tgme_page" in response.text:
                        result = self._parse_tgme_page(soup, result, url)
                        if result['success']:
                            break
                    elif "telegram" in response.text.lower():
                        result = self._parse_telegram_page(soup, result, url)
                        if result['success']:
                            break
            except:
                continue
        
        # Try to find phone number if not found
        if not result.get('phone_number'):
            result['phone_number'] = self._find_phone_number(clean_username)
        
        # Try to get additional info
        if result['success']:
            result['url'] = f"https://t.me/{clean_username}"
            
            # Get user ID if possible
            result['id'] = self._get_user_id(clean_username)
            
            # Get last seen status
            result['last_seen'] = self._get_last_seen(clean_username)
            
            # Check if account is restricted
            result['restricted'] = self._check_restricted(clean_username)
        
        return result
    
    def _parse_tgme_page(self, soup, result, url):
        """Parse Telegram page (tgme_page)"""
        try:
            result['success'] = True
            result['url'] = url
            
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
                    # Check if it's a channel
                    if 'tgme_channel_info' in str(soup):
                        result['type'] = 'channel'
                        result['channel_title'] = name_text
                    else:
                        result['full_name'] = name_text
                        # Split into first and last name
                        name_parts = name_text.split()
                        if name_parts:
                            result['first_name'] = name_parts[0]
                            if len(name_parts) > 1:
                                result['last_name'] = ' '.join(name_parts[1:])
            
            # Get bio/description
            bio_elem = soup.find('div', {'class': 'tgme_page_description'})
            if bio_elem:
                bio_text = bio_elem.text.strip()
                if bio_text:
                    if result['type'] == 'channel':
                        result['channel_description'] = bio_text
                    else:
                        result['bio'] = bio_text
            
            # Get profile picture
            img_elem = soup.find('img', {'class': 'tgme_page_photo_image'})
            if img_elem and img_elem.get('src'):
                result['profile_pic'] = img_elem.get('src')
            
            # Check if verified
            verified_elem = soup.find('span', {'class': 'verified'})
            if verified_elem:
                result['verified'] = True
            
            # Check if scam/fake
            scam_elem = soup.find('span', {'class': 'scam'})
            if scam_elem:
                result['scam'] = True
            
            # Check if fake
            fake_elem = soup.find('span', {'class': 'fake'})
            if fake_elem:
                result['fake'] = True
            
            # Get members count for channels/groups
            members_elem = soup.find('div', {'class': 'tgme_channel_info_members'})
            if members_elem:
                members_text = members_elem.text.strip()
                if members_text:
                    # Extract numbers
                    numbers = re.findall(r'\d+', members_text)
                    if numbers:
                        result['members_count'] = int(numbers[0])
            
            # Get location (if available)
            location_elem = soup.find('div', {'class': 'tgme_page_location'})
            if location_elem:
                result['location'] = location_elem.text.strip()
            
            # Get website (if available)
            website_elem = soup.find('a', {'class': 'tgme_page_website'})
            if website_elem:
                result['website'] = website_elem.text.strip()
            
            return result
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def _parse_telegram_page(self, soup, result, url):
        """Parse generic Telegram page"""
        try:
            result['success'] = True
            result['url'] = url
            
            # Try to find title
            title_elem = soup.find('title')
            if title_elem:
                title_text = title_elem.text.strip()
                if title_text and 'Telegram' not in title_text:
                    result['full_name'] = title_text
            
            # Try to find description
            desc_elem = soup.find('meta', {'name': 'description'})
            if desc_elem and desc_elem.get('content'):
                desc_text = desc_elem['content'].strip()
                if desc_text and 'Telegram' not in desc_text:
                    result['bio'] = desc_text
            
            return result
        except:
            result['success'] = False
            return result
    
    def _find_phone_number(self, username):
        """Try to find phone number from public sources"""
        try:
            # Search for phone number patterns
            search_url = f"https://www.google.com/search?q={username}+telegram+phone+number"
            response = self.session.get(search_url, timeout=5)
            
            if response.status_code == 200:
                # Look for phone number patterns
                phone_patterns = [
                    r'\+\d{1,3}\s?\d{3}\s?\d{3}\s?\d{4}',
                    r'\+\d{10,15}',
                    r'\d{4}\s?\d{3}\s?\d{4}',
                    r'\d{11,15}'
                ]
                
                for pattern in phone_patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        return matches[0]
            
            return None
        except:
            return None
    
    def _get_user_id(self, username):
        """Get user ID (estimated)"""
        try:
            # This is an estimation, actual ID requires API
            # Try to get from public data
            url = f"https://t.me/{username}"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                # Try to find ID in page source
                ids = re.findall(r'"user_id":(\d+)', response.text)
                if ids:
                    return int(ids[0])
            
            # Return a placeholder
            return f"user_{username}"
        except:
            return f"user_{username}"
    
    def _get_last_seen(self, username):
        """Get last seen status"""
        try:
            url = f"https://t.me/{username}"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                # Look for last seen patterns
                if "last seen" in response.text:
                    match = re.search(r'last seen (.+?)[<\.]', response.text)
                    if match:
                        return match.group(1)
                elif "online" in response.text:
                    return "Online"
                elif "recently" in response.text:
                    return "Recently"
            
            return "Unknown"
        except:
            return "Unknown"
    
    def _check_restricted(self, username):
        """Check if account is restricted"""
        try:
            url = f"https://t.me/{username}"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                if "restricted" in response.text.lower():
                    return True
                if "This channel is not accessible" in response.text:
                    return True
            
            return False
        except:
            return False

api = TelegramUserInfo()

@app.route('/')
def home():
    return jsonify({
        "service": "Telegram User Info API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "/info": "GET - /info?telegram=USERNAME - Get user info",
            "/info": "GET - /info?telegram=@USERNAME - Get user info",
            "/info": "GET - /info?telegram=USERNAME@t.me - Get user info",
            "/search": "GET - /search?q=USERNAME - Search user"
        },
        "examples": {
            "username": "/info?telegram=username123",
            "with_at": "/info?telegram=@username123",
            "with_url": "/info?telegram=t.me/username123"
        },
        "returns": {
            "username": "Telegram username",
            "full_name": "User's full name",
            "first_name": "First name",
            "last_name": "Last name",
            "bio": "User bio/description",
            "phone_number": "Phone number (if found)",
            "profile_pic": "Profile picture URL",
            "verified": "Verified status",
            "scam": "Scam account check",
            "fake": "Fake account check",
            "type": "User, channel, group, or bot",
            "members_count": "Members (if channel/group)",
            "last_seen": "Last seen status",
            "url": "Telegram profile URL",
            "website": "Website (if available)",
            "location": "Location (if available)",
            "restricted": "Restricted status"
        }
    })

@app.route('/info')
def get_telegram_info():
    telegram_input = request.args.get('telegram')
    
    if not telegram_input:
        return jsonify({
            "success": False,
            "error": "Missing telegram parameter",
            "usage": "/info?telegram=username123",
            "examples": [
                "/info?telegram=username123",
                "/info?telegram=@username123",
                "/info?telegram=t.me/username123"
            ]
        }), 400
    
    try:
        result = api.fetch_user_info(telegram_input)
        
        if not result['success']:
            return jsonify({
                "success": False,
                "error": "User not found or invalid username",
                "username": result.get('username', telegram_input),
                "timestamp": datetime.now().isoformat()
            }), 404
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "user_info": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/search')
def search_telegram():
    query = request.args.get('q')
    
    if not query:
        return jsonify({
            "success": False,
            "error": "Missing search query",
            "usage": "/search?q=username"
        }), 400
    
    try:
        result = api.fetch_user_info(query)
        
        return jsonify({
            "success": True,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/validate')
def validate_username():
    username = request.args.get('username')
    
    if not username:
        return jsonify({
            "success": False,
            "error": "Missing username parameter"
        }), 400
    
    clean = api.extract_username(username)
    
    return jsonify({
        "success": True,
        "input": username,
        "cleaned": clean,
        "is_valid": bool(clean and len(clean) >= 5)
    })

# Vercel handler
def handler(request):
    return app(request)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
