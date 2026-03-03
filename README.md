# 🚀 AppBuilder — NLP-to-App Generation System

> Describe any app in plain English → Gemini AI generates the full codebase → automatically pushed as a **private GitHub repo**.

Works from **Discord** (just type `/build`) or **Termux on your phone** (no laptop needed).

---

## ✨ What It Does

```
You type: "build me a todo app with React frontend and Node.js backend"
        ↓
Gemini 2.0 Flash generates ALL files:
  • Complete source code (frontend + backend)
  • Dockerfile
  • package.json / requirements.txt
  • README.md
  • TECHNICAL_DOCS.md
  • HOW_TO_RUN.md
  • .gitignore
        ↓
Automatically creates a private GitHub repo and pushes everything
        ↓
You get back the repo URL + how-to-run instructions
```

---

## 🗂 Project Structure

```
appbuilder/
├── .env                    ← Your secrets (NEVER commit this)
├── .env.example            ← Template for new users
├── .gitignore
├── requirements.txt
├── termux_setup.sh         ← One-shot Termux setup script
├── config.py               ← Loads all env vars
├── core/
│   ├── gemini_client.py    ← Gemini API wrapper
│   ├── app_generator.py    ← NLP → AppBundle
│   ├── file_writer.py      ← Writes files to disk (temp)
│   ├── github_pusher.py    ← Creates private repo + pushes
│   └── pipeline.py         ← Wires everything together
├── discord_bot/
│   └── bot.py              ← Discord slash-command bot
└── cli/
    └── build.py            ← Terminal/Termux CLI
```

---

## 🔑 Prerequisites

You need 3 secrets in your `.env` file:

| Secret | Where to get it |
|--------|----------------|
| `GEMINI_API_KEY` | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `GITHUB_TOKEN` | [github.com/settings/tokens](https://github.com/settings/tokens) → New token → select `repo` scope |
| `GITHUB_USERNAME` | Your GitHub username |
| `DISCORD_BOT_TOKEN` | [discord.com/developers](https://discord.com/developers/applications) → Your App → Bot → Reset Token |

---

## 💻 Option A — Use from Your Laptop (CLI)

```bash
# 1. Install dependencies
cd appbuilder
pip install -r requirements.txt

# 2. Run
python cli/build.py "make me a weather app with FastAPI and React"
```

---

## 📱 Option B — Use from Termux (Phone)

> No laptop needed! Run directly from your Android phone.

### 1. Install Termux

Download from **F-Droid** (recommended): https://f-droid.org/packages/com.termux/

### 2. Clone or copy this repo to your phone

```bash
pkg install git -y
git clone https://github.com/Arnav1771/appbuilder ~/appbuilder
cd ~/appbuilder
```

Or transfer the folder via USB/cloud storage.

### 3. Run the setup script

```bash
bash termux_setup.sh
```

### 4. Fill in your `.env` file

```bash
nano .env
```

### 5. Build your first app

```bash
python cli/build.py "simple REST API for a bookstore with FastAPI"
```

Or type interactively:

```bash
python cli/build.py -i
```

---

## 🤖 Option C — Use from Discord (Best for phone!)

> Just type `/build` in any Discord server where the bot is. No terminal needed.

### 1. Get your Discord Bot Token

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Select your Application → **Bot** section
3. Click **Reset Token** → Copy the token
4. Paste it in `.env` as `DISCORD_BOT_TOKEN=...`

> ⚠️ The Application ID and Public Key are **NOT** the bot token. The token is only visible in the **Bot** section.

### 2. Invite the bot to your server

Use this URL (replace `YOUR_APP_ID` with `1478197853456433263`):

```
https://discord.com/oauth2/authorize?client_id=1478197853456433263&permissions=2147483648&scope=bot%20applications.commands
```

### 3. Run the bot

```bash
# On laptop:
python discord_bot/bot.py

# On Termux (phone) — runs in background:
nohup python discord_bot/bot.py &
```

### 4. Use it in Discord

```
/build description: todo app with React frontend and FastAPI backend with JWT auth
/status
```

---

## 📝 Example Prompts

```
"simple hello world Flask web app"
"REST API for a bookstore with FastAPI and PostgreSQL"
"Discord bot that tracks crypto prices and sends alerts"
"full-stack todo app: React frontend, Node.js/Express backend, MongoDB"
"CLI tool to compress images in a folder with Python"
"simple blog with Django, SQLite, dark mode UI, user auth"
"weather app that shows 5-day forecast, uses OpenWeather API, React"
```

---

## ⚙️ How It Works (Technical)

1. **NLP Prompt** → sent to `gemini-2.0-flash` with a strict system prompt forcing JSON output
2. **Gemini Response** → parsed into an `AppBundle` (list of files + docs)
3. **GitHub API** → `PyGithub` creates a **private repo** and pushes all files via the GitHub Contents API (no local git installation needed)
4. **Result** → repo URL + how-to-run instructions returned to Discord or terminal

---

## 🔒 Security Notes

- Your `.env` file is in `.gitignore` and will **never** be committed
- All generated repos are **private** by default
- API keys are loaded only from environment variables, never hardcoded

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| `GEMINI_API_KEY missing` | Check your `.env` file exists and is in the `appbuilder/` folder |
| `401 Bad credentials` (GitHub) | Your GitHub token may be expired — regenerate it |
| Discord bot not responding | Make sure `DISCORD_BOT_TOKEN` is the **Bot Token**, not Application ID/Public Key |
| `JSONDecodeError` from Gemini | Try a more specific prompt, or retry |
