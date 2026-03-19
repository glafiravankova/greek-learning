### Learn Greek
A spaced repetition application for learning Greek words, built with vanilla JavaScript and Google Sheets as a database.

## Features
📚 Dictionary with sortable columns

➕ Add new words via Google Forms integration

🏋️ Spaced repetition training algorithm

📊 Word statuses:

new → learn → check → 1 day gap → 2 day gap → 3 day gap → 5 day gap → 8 day gap → 12 day gap → 20 day gap → 30 day gap → 60 day gap

🔄 Automatic daily status updates

🎯 Daily limit of 10 new words

📱 Fully responsive design (works on phone, tablet, desktop)

☁️ All data stored in Google Sheets — syncs across all devices automatically

## How It Works
1. Words are added through a simple form and sent to Google Forms
2. Google Apps Script automatically copies new words to the main sheet
3. The app reads data directly from Google Sheets API
4. Training sessions update word statuses in real time
5. Daily limit of 10 new words is enforced by a smart scheduling system (first_review column)

## Technologies
Frontend: Vanilla HTML5, CSS3, JavaScript

Backend: Google Sheets (as database) + Google Apps Script (for updates)

Hosting: GitHub Pages

APIs: Google Sheets API v4, Google Apps Script API

## Why This Stack?
- 100% free (no server costs)
- Works in regions with restricted access
- Data syncs across all devices automatically
- No backend to maintain
- Full control over data (it's just a Google Sheet)

