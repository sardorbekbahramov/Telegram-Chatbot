# Telegram Medical Assistant Bot (Flask + Gemini)

## Setup (local)
1. Create `.env` with:
   - TELEGRAM_BOT_TOKEN
   - GEMINI_API_KEY
   - (optional) RENDER_EXTERNAL_URL for local webhook testing
2. Install dependencies:

3. Run locally:


## Deploy to Render
1. Push repo to GitHub.
2. Create a new **Web Service** on Render and connect your repo.
3. Set environment variables in Render dashboard:
- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY`
4. Deploy. Render will use Procfile: `web: gunicorn main:app`
5. After deploy, open the service URL to trigger webhook setup.

