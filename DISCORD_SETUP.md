# Discord Bot Setup Instructions

## 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give it a name (e.g., "Security Assessment Bot")
4. Go to the "Bot" section
5. Click "Add Bot"
6. Copy the bot token (keep this secret!)

## 2. Configure Bot Permissions

In the Bot section:
- **Enable "Message Content Intent"** (required for reading message content and accessing file attachments)
- Set appropriate permissions

**Note:** File attachments are accessed through message content, so no separate "attachments" intent is needed.

## 3. Invite Bot to Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`
3. Select permissions:
   - Send Messages
   - Attach Files
   - Read Message History
   - Use Slash Commands
4. Copy the generated URL and open it to invite the bot

## 4. Environment Configuration

Add to your `.env` file:
```
DISCORD_BOT_TOKEN=your_bot_token_here
```

## 5. Install Dependencies

```bash
pip install -r requirements.txt
```

## 6. Run the Bot

```bash
python discord_bot.py
```

## Bot Usage

### Security Assessments
- Upload a Draw.io file (.drawio or .xml) to any channel
- The bot will automatically analyze it and provide a security report

### Security Questions
- Mention the bot (@SecurityBot) or DM it
- Ask questions like:
  - "What WAF tools do you recommend for AWS?"
  - "How to secure AI applications?"
  - "Best practices for API security"

### Example Commands
```
@SecurityBot What controls can help protect AI applications?
@SecurityBot I need to implement a WAF for an AWS ecosystem. Which tools do you recommend?
```

## Features

- 🤖 Automated Draw.io security assessment
- 💬 General security question answering
- 📊 Risk scoring and threat analysis
- 📝 Markdown report generation
- 🎯 PYTM threat modeling integration
- 📋 CIS Controls mapping