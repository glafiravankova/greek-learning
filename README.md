# Learn Greek — Spaced Repetition Tracker

A no‑backend web app for learning Greek vocabulary using spaced repetition.  
Hosted on GitHub Pages, powered by Google Sheets.

🔗 [glafiravankova.github.io/greek-learning](https://glafiravankova.github.io/greek-learning)

---

## Problems this solves

**1. Language apps don't separate known words from difficult ones**  
You keep reviewing the same easy words, wasting time.

**2. They push too many new words at once**  
No break, no real limit. That leads to burnout, not progress.

This app solves both with a controlled spaced repetition system.

---

## How it works

- **Daily limit:** at most 10 new words per day  
- **Spaced repetition:** words you know well appear less often  
- **Hard words stay longer** until you learn them  
- **If you make a mistake** — the word resets to `to_learn` and you go through all stages again  

Word status flow:  
`new` → `to_learn` → `to_check` → `1_day` → `2_day` → `3_day` → `5_day` → `8_day` → `12_day` → `20_day` → `30_day` → `60_day`

---

## Why no backend

The original version used Flask + SQLite.  
Hosting it would require a paid server, and many platforms are blocked without a VPN.

This version is **100% frontend**:
- Google Sheets as a database  
- Google Apps Script for updates  
- GitHub Pages for hosting  

Everything is free, works anywhere, and syncs across devices automatically.

---

## Features

- Dictionary with sortable columns  
- Add multiple words at once  
- Spaced repetition training  
- Daily limit of 10 new words  
- Progress sync across devices  
- No server, no database, no subscription  

---

## Tech stack

- HTML, CSS, JavaScript (vanilla)  
- Google Sheets API  
- Google Apps Script  
- GitHub Pages  

---

## License

MIT

---

Built to learn Greek without stress.  
Μπράβο, ρε.
