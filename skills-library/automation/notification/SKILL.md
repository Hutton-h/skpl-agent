---
name: notification
description: Multi-channel notification workflow — sends messages via WhatsApp, email, and webhook. Routes to the appropriate channel based on available credentials and user preference.
version: 1.0.0
category: automation
when_to_use: User asks to send a notification, alert, report delivery, or message through WhatsApp, email, or webhook.
---

# Notification Skill — 多渠道通知

## Goal
Route a user's message through the appropriate notification channel — WhatsApp (Cloud API or Desktop), email (SMTP), or webhook — based on available credentials and user preference.

## Available Tools
send_notification (WhatsApp Cloud API), desktop (WhatsApp Desktop fallback), Write (email template), RunPython (webhook).

## Workflow

### Step 1: Channel Selection
Determine the best channel:
1. **WhatsApp Cloud API**: if `send_notification` tool is available and WhatsApp credentials are configured — ALWAYS prefer this. 有 Cloud API 凭据时优先使用。
2. **WhatsApp Desktop**: if no Cloud API, fall back to the whatsapp-desktop skill (screen-based GUI automation). 桌面端作为备选。
3. **Email**: if SMTP credentials are configured and the user wants email delivery.
4. **Webhook**: if the user provides a webhook URL.

Ask the user which channel if multiple are available and they haven't specified.

### Step 2: Message Preparation
Format the message for the target channel:
- **WhatsApp**: plain text, no markdown. Keep under 4096 characters. Emojis OK.
- **Email**: subject line + HTML body with proper formatting.
- **Webhook**: JSON payload structured per the webhook's expected format.

### Step 3: Send
Execute based on the chosen channel:

**WhatsApp Cloud API (send_notification):**
```
Call send_notification with:
- channel: "whatsapp"
- to: recipient phone number
- message: the prepared text
```

**WhatsApp Desktop (whatsapp-desktop skill):**
Follow the whatsapp-desktop skill workflow:
- Verify desktop node is connected
- Open WhatsApp Desktop
- Locate contact, type message, send
- Screenshot for verification

**Email:**
Use RunPython with smtplib to send via configured SMTP.

**Webhook:**
Use RunPython with requests to POST the JSON payload.

### Step 4: Confirmation
Report back:
- Channel used
- Recipient
- Message preview (first 100 chars)
- Send timestamp
- Any warnings or failures

## Quality Rules
- Never send without explicit user confirmation of the message content
- Truncate messages that exceed channel limits and warn the user
- Handle failures gracefully — suggest alternative channels
- Do not expose credentials in the response