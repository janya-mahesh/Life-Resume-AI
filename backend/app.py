# app.py — Mentora Backend (Groq-powered)
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import re
from openai import OpenAI
from urllib.parse import urlparse
from datetime import datetime
from keyword_extractor import extract_keywords
from dotenv import load_dotenv
import copy

load_dotenv()

app = Flask(__name__)

# ─── Groq Client (Free Tier) ──────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
grok_client = None
if GROQ_API_KEY:
    grok_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

USERS_FILE = os.path.join('data', 'users.json')
CAREER_CSV = os.path.join('data', 'career_keywords_cleaned.csv')

# ─── Utility Functions ────────────────────────────────────────────────────────

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def save_keywords_to_user(email, keywords):
    users = load_users()
    if email not in users:
        return
    users[email].setdefault("keywords", [])
    users[email]["keywords"].append({
        "text": keywords,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_users(users)

def categorize_url(url):
    productive_sites = [
        "stackoverflow.com", "github.com", "kaggle.com", "wikipedia.org",
        "coursera.org", "edx.org", "linkedin.com", "medium.com",
        "docs.google.com", "drive.google.com", "zoom.us"
    ]
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return "leisure"
    return "productive" if any(site in hostname for site in productive_sites) else "leisure"

def extract_day(ts_ms):
    try:
        return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None

# ─── App Info for Screen Time Analysis ────────────────────────────────────────

APP_INFO = {
    'instagram.com': {'name': 'Instagram', 'type': 'leisure', 'prompt': "Instagram is fun, but don't forget to take breaks! 📸"},
    'youtube.com': {'name': 'YouTube', 'type': 'leisure', 'prompt': "Watched anything interesting on YouTube lately? 📺"},
    'stackoverflow.com': {'name': 'Stack Overflow', 'type': 'productive', 'prompt': "Learning something new on Stack Overflow? 🚀"},
    'github.com': {'name': 'GitHub', 'type': 'productive', 'prompt': "Building something cool on GitHub? 💻"},
    'wikipedia.org': {'name': 'Wikipedia', 'type': 'productive', 'prompt': "Exploring new knowledge on Wikipedia? 📚"},
    'netflix.com': {'name': 'Netflix', 'type': 'leisure', 'prompt': "Binge-watching on Netflix? 🍿"},
    'twitter.com': {'name': 'Twitter', 'type': 'leisure', 'prompt': "Catching up on trends on Twitter? 🐦"},
    'coursera.org': {'name': 'Coursera', 'type': 'productive', 'prompt': "Taking a course on Coursera? 🎓"},
    'facebook.com': {'name': 'Facebook', 'type': 'leisure', 'prompt': "Connecting with friends on Facebook? 👥"},
    'tiktok.com': {'name': 'TikTok', 'type': 'leisure', 'prompt': "Scrolling through TikTok? Don't forget to take a break! 🎵"},
    'whatsapp.com': {'name': 'WhatsApp', 'type': 'leisure', 'prompt': "Chatting on WhatsApp? Stay connected! 💬"},
    'reddit.com': {'name': 'Reddit', 'type': 'leisure', 'prompt': "Browsing Reddit? Found any good threads? 👀"},
    'snapchat.com': {'name': 'Snapchat', 'type': 'leisure', 'prompt': "Snapping on Snapchat? 📸"},
    'edx.org': {'name': 'edX', 'type': 'productive', 'prompt': "Learning something new on edX? 🎓"},
    'kaggle.com': {'name': 'Kaggle', 'type': 'productive', 'prompt': "Working on data science projects on Kaggle? 📊"},
    'linkedin.com': {'name': 'LinkedIn', 'type': 'productive', 'prompt': "Networking on LinkedIn? 🤝"},
    'gmail.com': {'name': 'Gmail', 'type': 'productive', 'prompt': "Catching up on emails? 📧"},
    'outlook.com': {'name': 'Outlook', 'type': 'productive', 'prompt': "Checking your Outlook inbox? 📧"},
    'amazon.com': {'name': 'Amazon', 'type': 'leisure', 'prompt': "Shopping on Amazon? 🛒"},
    'flipkart.com': {'name': 'Flipkart', 'type': 'leisure', 'prompt': "Browsing deals on Flipkart? 🛍️"},
    'medium.com': {'name': 'Medium', 'type': 'productive', 'prompt': "Reading articles on Medium? 📝"},
    'zoom.us': {'name': 'Zoom', 'type': 'productive', 'prompt': "Attending meetings on Zoom? 🎥"},
}

def get_app_info(url):
    try:
        hostname = urlparse(url).hostname
    except Exception:
        hostname = None
    if hostname:
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
            return {'name': 'Other', 'type': 'leisure', 'prompt': "Hope you're enjoying your time online!"}
        parts = hostname.lower().split('.')
        main_domain = '.'.join(parts[-2:]) if len(parts) > 2 else hostname.lower()
        info = APP_INFO.get(main_domain)
        if info:
            return info
        if main_domain.endswith('.edu'):
            clean_name = main_domain.replace('.edu', '').title()
            return {'name': clean_name, 'type': 'productive', 'prompt': "Learning something new? 🚀"}
        clean_name = re.sub(r'\.(com|org|net|edu|io)$', '', main_domain).title()
        return {'name': clean_name, 'type': 'leisure', 'prompt': "Hope you're enjoying your time online!"}
    return {'name': 'Other', 'type': 'leisure', 'prompt': "Hope you're enjoying your time online!"}


# ─── Grok Chat & Sentiment Analysis ──────────────────────────────────────────

def get_user_context(email):
    """Build a context string from user profile for Grok."""
    users = load_users()
    user = users.get(email, {})
    if not user:
        return "No user profile available."
    
    parts = []
    if user.get("name"):
        parts.append(f"Name: {user['name']}")
    if user.get("age"):
        parts.append(f"Age: {user['age']}")
    if user.get("phase"):
        parts.append(f"Life Phase: {user['phase']}")
    if user.get("interests"):
        parts.append(f"Interests: {user['interests']}")
    if user.get("achievements"):
        parts.append(f"Achievements/Goals: {user['achievements']}")
    if user.get("hobbies"):
        parts.append(f"Hobbies: {user['hobbies']}")
    if user.get("struggles"):
        parts.append(f"Struggles: {user['struggles']}")
    if user.get("career_suggestions"):
        parts.append(f"Career Suggestions: {', '.join(user['career_suggestions'])}")
    
    return "\n".join(parts) if parts else "No profile data yet."


def get_screen_time_summary(email):
    """Generate screen time summary for the user."""
    users = load_users()
    user = users.get(email, {})
    screen_time_data = user.get('screen_time_data', [])
    
    if not screen_time_data:
        return None
    
    # Find most recent day
    days = [extract_day(entry.get("timestamp")) for entry in screen_time_data if entry.get("timestamp")]
    days = [d for d in days if d]
    if not days:
        return None
    
    most_recent_day = max(days)
    today_data = [e for e in screen_time_data if extract_day(e.get("timestamp")) == most_recent_day]
    
    # Aggregate by app
    app_usage = {}
    app_types = {}
    for entry in today_data:
        url = entry.get('url', 'Other')
        info = get_app_info(url)
        app_name = info['name']
        app_usage[app_name] = app_usage.get(app_name, 0) + entry.get('timeSpent', 0)
        app_types[app_name] = info['type']
    
    sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
    app_lines = [f"{app}: {round(secs / 3600, 2)}h" for app, secs in sorted_apps if secs > 0]
    
    total_time = sum(app_usage.values())
    productive_time = sum(v for k, v in app_usage.items() if app_types.get(k) == 'productive')
    leisure_time = sum(v for k, v in app_usage.items() if app_types.get(k) == 'leisure')
    
    return {
        "total_hours": round(total_time / 3600, 2),
        "productive_hours": round(productive_time / 3600, 2),
        "leisure_hours": round(leisure_time / 3600, 2),
        "app_breakdown": ", ".join(app_lines),
        "top_app": sorted_apps[0][0] if sorted_apps else "None"
    }


def chat_with_grok(message, email, is_proactive=False):
    """Send message to Grok and get response with sentiment analysis."""
    if not grok_client:
        return [{
            "text": "API not configured. Please set your GROQ_API_KEY in the .env file. "
                    "Visit https://console.groq.com/keys to get your free API key."
        }]
    
    user_context = get_user_context(email)
    screen_summary = get_screen_time_summary(email)
    
    screen_context = ""
    if screen_summary:
        screen_context = (
            f"\n\nScreen Time Data (most recent day):\n"
            f"Total: {screen_summary['total_hours']}h, "
            f"Productive: {screen_summary['productive_hours']}h, "
            f"Leisure: {screen_summary['leisure_hours']}h\n"
            f"App breakdown: {screen_summary['app_breakdown']}"
        )
    
    system_prompt = f"""You are Mentora, a warm and insightful AI life coach. Your role is to:
1. Analyze the user's emotions and provide empathetic responses (sentiment analysis)
2. Give career advice based on their profile
3. Provide screen time insights and habit improvement tips
4. Motivate and encourage personal growth
5. Help users discover their strengths and passions

USER PROFILE:
{user_context}
{screen_context}

IMPORTANT RULES:
- Keep responses concise (2-4 sentences max unless giving detailed advice)
- Use relevant emojis naturally
- If the user expresses negative emotions, be supportive and offer actionable advice
- If asked about screen time, reference the actual data above
- If asked about career, match their interests to suitable career paths
- Always be encouraging and positive
- End with a follow-up question or actionable suggestion when appropriate

RESUME AUTO-UPDATE RULE:
If the user mentions NEW interests, achievements, skills, hobbies, struggles, or goals 
in their message, include a line at the VERY END of your response in this exact format:
[RESUME_UPDATE: field=value]
Examples:
[RESUME_UPDATE: interests=coding, AI, machine learning]
[RESUME_UPDATE: achievements=Won a hackathon]
[RESUME_UPDATE: hobbies=playing guitar, hiking]
Only include this if genuinely new information is shared. Do NOT include it for casual chat."""

    if is_proactive and screen_summary:
        message = (
            f"Give me a brief, friendly screen time summary. "
            f"Total: {screen_summary['total_hours']}h, "
            f"Productive: {screen_summary['productive_hours']}h, "
            f"Leisure: {screen_summary['leisure_hours']}h. "
            f"Top app: {screen_summary['top_app']}. "
            f"App breakdown: {screen_summary['app_breakdown']}"
        )
    elif is_proactive:
        return [{"text": "I don't have enough screen time data yet. Start browsing and I'll track your habits! 📊"}]
    
    try:
        response = grok_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        reply_text = response.choices[0].message.content.strip()
        
        # Extract resume updates if any
        resume_update_match = re.findall(r'\[RESUME_UPDATE:\s*(\w+)=(.+?)\]', reply_text)
        if resume_update_match and email:
            process_auto_resume_update(email, resume_update_match)
            # Remove the update tags from visible response
            reply_text = re.sub(r'\[RESUME_UPDATE:.*?\]', '', reply_text).strip()
        
        return [{"text": reply_text}]
    
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower():
            return [{"text": "⚠️ Invalid API key. Please check your XAI_API_KEY in the .env file."}]
        elif "429" in error_msg or "rate" in error_msg.lower():
            return [{"text": "⏳ Rate limit reached. Please wait a moment and try again."}]
        return [{"text": f"Sorry, I'm having trouble right now. Error: {error_msg}"}]


def process_auto_resume_update(email, updates):
    """Auto-update user resume based on chat-extracted info and save a version."""
    users = load_users()
    if email not in users:
        return
    
    user = users[email]
    
    # Save current state as a version before updating
    version_snapshot = {
        "timestamp": datetime.now().isoformat(),
        "name": user.get("name", ""),
        "interests": user.get("interests", ""),
        "achievements": user.get("achievements", ""),
        "hobbies": user.get("hobbies", ""),
        "struggles": user.get("struggles", ""),
        "phase": user.get("phase", ""),
    }
    
    user.setdefault("resume_versions", [])
    
    changed = False
    for field, value in updates:
        field = field.strip().lower()
        value = value.strip()
        if field in ["interests", "achievements", "hobbies", "struggles", "phase", "name"]:
            current = user.get(field, "")
            # Append new info rather than overwrite (smarter merge)
            if current and value.lower() not in current.lower():
                user[field] = f"{current}, {value}"
            elif not current:
                user[field] = value
            changed = True
    
    if changed:
        # Only save version if something actually changed
        user["resume_versions"].append(version_snapshot)
        # Keep only last 20 versions
        if len(user["resume_versions"]) > 20:
            user["resume_versions"] = user["resume_versions"][-20:]
        
        # Re-extract keywords from updated profile
        combined = " ".join([
            user.get("interests", ""),
            user.get("achievements", ""),
            user.get("hobbies", "")
        ])
        if combined.strip():
            try:
                new_keywords = extract_keywords(combined)
                user.setdefault("keywords", [])
                user["keywords"].append({
                    "text": new_keywords,
                    "source": "auto_update",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception:
                pass
        
        # Auto-generate career suggestions based on updated profile
        try:
            update_career_suggestions(email, user)
        except Exception:
            pass
    
    save_users(users)


def update_career_suggestions(email, user):
    """Update career suggestions based on user profile keywords."""
    if not os.path.exists(CAREER_CSV):
        return
    
    combined = " ".join([
        user.get("interests", ""),
        user.get("achievements", ""),
        user.get("hobbies", ""),
        user.get("struggles", "")
    ]).lower()
    
    # Simple keyword extraction
    words = re.sub(r'[^\w\s]', '', combined).split()
    stopwords = {"i", "the", "a", "an", "and", "to", "of", "in", "on", "for", "with", "is", "are", "my", "im", "just", "want", "not", "sure", "yet"}
    user_keywords = set(w for w in words if w not in stopwords and len(w) > 2)
    
    df = pd.read_csv(CAREER_CSV)
    suggestions = []
    for _, row in df.iterrows():
        career = row.get("career", "")
        career_keyword = str(row.get("keyword", "")).lower().strip()
        if career_keyword in user_keywords:
            suggestions.append(career)
    
    if suggestions:
        user["career_suggestions"] = suggestions[:5]


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        users = load_users()
        
        if email in users:
            stored_password = users[email].get('password', '')
            if stored_password and stored_password != password:
                return render_template('login.html', error="Invalid password. Please try again.")
            return redirect(url_for('dashboard', email=email))
        
        return redirect(url_for('onboarding', email=email))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not name or not password:
            return render_template('register.html', error="All fields are required.")
        
        users = load_users()
        if email in users:
            return render_template('register.html', error="Account already exists. Please login.")
        
        users[email] = {
            "name": name,
            "password": password,
            "screen_time_data": [],
            "resume_versions": [],
            "keywords": []
        }
        save_users(users)
        return redirect(url_for('onboarding', email=email))
    return render_template('register.html')

@app.route('/onboarding/<email>', methods=['GET', 'POST'])
def onboarding(email):
    if request.method == 'POST':
        users = load_users()
        if email not in users:
            users[email] = {"screen_time_data": [], "resume_versions": [], "keywords": []}
        
        interests = request.form.get('interests', '')
        achievements = request.form.get('goals', '')
        hobbies = request.form.get('passion', '')
        
        # Extract keywords
        try:
            interest_keywords = extract_keywords(interests) if interests else []
            achievement_keywords = extract_keywords(achievements) if achievements else []
            hobby_keywords = extract_keywords(hobbies) if hobbies else []
        except Exception:
            interest_keywords = achievement_keywords = hobby_keywords = []
        
        users[email].setdefault("keywords", [])
        users[email]["keywords"].extend([
            {"text": interest_keywords, "source": "interests", "timestamp": datetime.now().isoformat()},
            {"text": achievement_keywords, "source": "achievements", "timestamp": datetime.now().isoformat()},
            {"text": hobby_keywords, "source": "hobbies", "timestamp": datetime.now().isoformat()}
        ])
        
        users[email].update({
            "name": request.form.get('name', users[email].get('name', '')),
            "age": request.form.get('age', ''),
            "phase": request.form.get('level', ''),
            "interests": interests,
            "achievements": achievements,
            "hobbies": hobbies,
            "struggles": request.form.get('challenges', ''),
            "screen_time_data": users[email].get('screen_time_data', []),
            "resume_versions": users[email].get('resume_versions', [])
        })
        
        # Generate initial career suggestions
        try:
            update_career_suggestions(email, users[email])
        except Exception:
            pass
        
        save_users(users)
        return redirect(url_for('dashboard', email=email))
    return render_template('questionnaire.html', email=email)

@app.route('/dashboard/<email>')
def dashboard(email):
    users = load_users()
    user = users.get(email, {})
    motivations = [
        "Stay hungry, stay foolish. — Steve Jobs",
        "Every day is a second chance.",
        "You've got this! 💪",
        "The only way to do great work is to love what you do.",
        "Progress, not perfection.",
        "Your future self will thank you for starting today.",
        "Small steps lead to big changes. 🚀"
    ]
    return render_template('dashboard.html', user=user, email=email, motivations=motivations)

@app.route('/resume/<email>')
def resume(email):
    users = load_users()
    user = users.get(email, {})
    return render_template('resume.html', user=user, email=email)

@app.route('/edit-resume/<email>', methods=['GET', 'POST'])
def edit_resume(email):
    users = load_users()
    if request.method == 'POST':
        if email not in users:
            users[email] = {}
        
        # Save version before editing
        user = users[email]
        version_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "name": user.get("name", ""),
            "interests": user.get("interests", ""),
            "achievements": user.get("achievements", ""),
            "hobbies": user.get("hobbies", ""),
            "struggles": user.get("struggles", ""),
            "phase": user.get("phase", ""),
            "source": "manual_edit"
        }
        user.setdefault("resume_versions", [])
        user["resume_versions"].append(version_snapshot)
        
        users[email].update({
            "name": request.form.get('name', ''),
            "age": request.form.get('age', ''),
            "phase": request.form.get('phase', ''),
            "interests": request.form.get('interests', ''),
            "achievements": request.form.get('achievements', ''),
            "hobbies": request.form.get('hobbies', ''),
            "struggles": request.form.get('struggles', '')
        })
        
        # Re-generate career suggestions
        try:
            update_career_suggestions(email, users[email])
        except Exception:
            pass
        
        save_users(users)
        return redirect(url_for('resume', email=email))
    return render_template('edit_resume.html', user=users.get(email, {}), email=email)

@app.route('/career-suggestions/<email>')
def career_suggestions(email):
    users = load_users()
    user = users.get(email, {})
    suggestions = user.get("career_suggestions", [])
    return render_template("career_suggestions.html", user=user, email=email, suggestions=suggestions)

@app.route('/resume/update', methods=['POST'])
def update_resume():
    data = request.json
    email = data.get("email")
    suggestions = data.get("career_suggestions", [])
    
    if not email:
        return jsonify({"status": "error", "message": "Email required"}), 400
    
    users = load_users()
    if email not in users:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    users[email]["career_suggestions"] = suggestions
    save_users(users)
    return jsonify({"status": "ok", "message": "Career suggestions updated"})

@app.route('/analysis/<email>')
def analysis(email):
    users = load_users()
    user = users.get(email, {})
    screen_time_data = user.get('screen_time_data', [])
    
    if screen_time_data:
        total_time = sum(entry.get('timeSpent', 0) for entry in screen_time_data)
        productive_time = sum(entry.get('timeSpent', 0) for entry in screen_time_data if entry.get('category') == 'productive')
        leisure_time = sum(entry.get('timeSpent', 0) for entry in screen_time_data if entry.get('category') == 'leisure')
        
        unique_days = set()
        for entry in screen_time_data:
            ts = entry.get("timestamp")
            if ts:
                day = extract_day(ts)
                if day:
                    unique_days.add(day)
        
        num_days = max(len(unique_days), 1)
        # Fixed: divide by 3600 to get hours (was dividing by 60 = minutes)
        avg_daily_screen_time = total_time / num_days / 3600
        avg_productive = productive_time / num_days / 3600
        avg_social_media = leisure_time / num_days / 3600
    else:
        avg_daily_screen_time = avg_productive = avg_social_media = 0
    
    summary = {
        "avg_daily_screen_time": round(avg_daily_screen_time, 2),
        "avg_productive": round(avg_productive, 2),
        "avg_social_media": round(avg_social_media, 2),
    }
    return render_template('analysis.html', summary=summary, email=email)

@app.route('/screen-time-data', methods=['POST'])
def screen_time_data_route():
    data = request.json
    email = data.get('email')
    usage_data = data.get('usageData', [])
    
    if not email:
        return jsonify({"status": "error", "error": "email required"}), 400
    
    users = load_users()
    if email in users:
        new_entries = []
        for entry in usage_data:
            new_entries.append({
                "url": entry.get('url', ''),
                "timeSpent": entry.get('timeSpent', 0),
                "timestamp": entry.get('timestamp', int(datetime.now().timestamp() * 1000)),
                "category": categorize_url(entry.get('url', ''))
            })
        users[email].setdefault('screen_time_data', [])
        users[email]['screen_time_data'].extend(new_entries)
        save_users(users)
    return jsonify({"status": "ok"})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get("message", "")
    email = data.get("email", "")
    
    # Extract keywords from user message
    if message and not message.startswith("__"):
        try:
            keywords = extract_keywords(message)
            if email and keywords:
                save_keywords_to_user(email, keywords)
        except Exception:
            pass
    
    # Handle proactive screen time
    if message == "__proactive_screen_time__":
        return jsonify(chat_with_grok(message, email, is_proactive=True))
    
    # Regular chat with Grok
    return jsonify(chat_with_grok(message, email))

@app.route('/api/screen-feedback')
def screen_feedback():
    email = request.args.get('email')
    users = load_users()
    user = users.get(email, {})
    screen_time_data = user.get('screen_time_data', [])
    
    if not screen_time_data:
        return jsonify({"feedback": "No screen time data available yet."})
    
    total_time = sum(entry.get('timeSpent', 0) for entry in screen_time_data)
    productive_time = sum(entry.get('timeSpent', 0) for entry in screen_time_data if entry.get('category') == 'productive')
    leisure_time = sum(entry.get('timeSpent', 0) for entry in screen_time_data if entry.get('category') == 'leisure')
    
    unique_days = {extract_day(entry.get("timestamp")) for entry in screen_time_data if extract_day(entry.get("timestamp"))}
    num_days = max(len(unique_days), 1)
    
    avg_daily = total_time / num_days / 3600
    avg_prod = productive_time / num_days / 3600
    avg_leisure = leisure_time / num_days / 3600
    
    feedback = (
        f"📱 Average screen time: {round(avg_daily, 1)} hours/day.\n"
        f"💼 Productive: {round(avg_prod, 1)} hours/day.\n"
        f"🎮 Leisure: {round(avg_leisure, 1)} hours/day.\n"
    )
    
    if avg_leisure > avg_prod:
        feedback += "⏳ Try shifting more time towards learning or productivity apps!"
    else:
        feedback += "✅ Great balance! Keep it up."
    
    return jsonify({"feedback": feedback})

@app.route('/api/users')
def get_user_data():
    email = request.args.get('email')
    users = load_users()
    if not email or email not in users:
        return jsonify({})
    return jsonify(users[email])

@app.route('/api/resume-versions/<email>')
def get_resume_versions(email):
    """API endpoint to get resume version history."""
    users = load_users()
    user = users.get(email, {})
    versions = user.get("resume_versions", [])
    return jsonify({"versions": versions, "count": len(versions)})

@app.route('/chat-ui')
def chat_ui():
    return render_template('chat-ui.html')

if __name__ == '__main__':
    print("[*] Starting Mentora Flask App...")
    print("[*] Make sure XAI_API_KEY is set in your .env file")
    print("[*] Visit http://localhost:5000")
    app.run(debug=True)
