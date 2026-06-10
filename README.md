# ⚡ Mentora — AI-Powered Life Coach

Mentora is a web application that acts as your personal AI life coach. It tracks your digital habits, builds an evolving "life resume," and provides AI-powered career suggestions and mentoring through a chatbot powered by Grok (xAI).

## ✨ Features

- **🤖 AI Chatbot (Grok)** — Chat with Mentora for career advice, motivation, habit improvement, and emotional support. Uses sentiment analysis to understand your mood.
- **📄 Auto-Updating Life Resume** — Your resume auto-evolves as you chat with Mentora. Every update is version-tracked, so you can see how you've grown.
- **📊 Screen Time Analysis** — Chrome extension tracks your browsing habits and categorizes time as productive or leisure.
- **🚀 Career Suggestions** — AI-matched career paths based on your interests, skills, and goals.
- **🎓 Onboarding Questionnaire** — Comprehensive profile setup that feeds into all features.

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python) |
| AI/Chat | Grok (xAI API) via OpenAI-compatible client |
| NLP | KeyBERT for keyword extraction |
| Frontend | Jinja2 templates + vanilla CSS (metallic dark theme) |
| Charts | Chart.js |
| Extension | Chrome Extension (Manifest V3) |
| Data | JSON file storage |

## 🚀 Quick Start

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/YOUR_USERNAME/Life-Resume-AI.git
cd Life-Resume-AI
pip install -r requirements.txt
```

### 2. Get Your Free Grok API Key

1. Go to [https://console.x.ai/](https://console.x.ai/)
2. Create an account and generate an API key
3. Create `backend/.env` and add:

```env
XAI_API_KEY=your_actual_api_key_here
```

### 3. Run the App

```bash
cd backend
python app.py
```

Visit [http://localhost:5000](http://localhost:5000)

### 4. Install Chrome Extension (Optional)

1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" → select the `my-extension/` folder
4. Log in to Mentora and the extension will track your browsing habits

## 📁 Project Structure

```
Life-Resume-AI/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── keyword_extractor.py   # KeyBERT keyword extraction
│   ├── .env                   # API keys (not committed)
│   ├── data/
│   │   ├── users.json         # User data (not committed)
│   │   └── career_keywords_cleaned.csv
│   ├── static/
│   │   └── mentora.jpg
│   └── templates/
│       ├── login.html
│       ├── register.html
│       ├── questionnaire.html
│       ├── dashboard.html
│       ├── chat-ui.html
│       ├── resume.html
│       ├── edit_resume.html
│       ├── analysis.html
│       └── career_suggestions.html
├── my-extension/
│   ├── manifest.json
│   ├── background.js
│   ├── popup.html
│   └── popup.js
├── data/
│   └── career_keywords_cleaned.csv
├── requirements.txt
├── .gitignore
└── README.md
```

## 🔑 API Setup (Grok / xAI)

Mentora uses the **Grok API** (by xAI) for:
- Conversational AI chatbot
- Sentiment analysis
- Auto-resume updates from chat context

**Steps:**
1. Visit [https://console.x.ai/](https://console.x.ai/)
2. Sign up / Log in
3. Navigate to API Keys → Create new key
4. Copy the key into `backend/.env` as `XAI_API_KEY=...`
5. The free tier provides sufficient usage for personal use

## 📝 License

This project is for educational and personal use.
