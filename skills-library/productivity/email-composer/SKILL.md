---
name: email-composer
description: Email composition workflow — drafts business, marketing, notification, and follow-up emails in multiple languages. Produces polished, context-aware email drafts ready for review and send.
version: 1.0.0
category: productivity
when_to_use: User asks to write, draft, or compose an email — business correspondence, marketing outreach, meeting follow-ups, notifications, or any professional email communication.
---

# Email Composer Skill — 邮件撰写

## Goal
From user-provided context (recipient, purpose, key points), produce a polished email draft in the requested language and tone.

## Available Tools
Write, docwriter skill.

## Workflow

### Step 1: Context Gathering
Clarify with the user (if not provided):
- Recipient: name, role, relationship to sender
- Purpose: introduction, follow-up, proposal, notification, thank-you
- Tone: formal, semi-formal, friendly, urgent
- Language: specify if different from conversation language
- Key points: 2-4 must-include items
- Call to action: what should the recipient do?

### Step 2: Draft Structure
Build the email with:
- **Subject line**: clear, specific, under 60 characters
- **Opening**: personalized greeting + context bridge
- **Body**: 2-3 short paragraphs, one idea each
- **Call to action**: single, clear next step
- **Closing**: professional sign-off with sender info

### Step 3: Tone Calibration
Adjust based on email type:
- **Cold outreach**: warm, respectful, value-first
- **Follow-up**: polite persistence, reference previous contact
- **Internal**: direct, action-oriented
- **Client-facing**: polished, solution-focused
- **Notification**: concise, informative, no fluff

### Step 4: Multi-Language Support
If requesting a non-English email:
- Write in the target language directly (not translated from English)
- Use culturally appropriate greetings and closings
- Verify character encoding for special characters
- Note any localization considerations

### Step 5: Delivery
Present the draft in the chat for review. Also write to a file so the user can copy-paste or refine.

## Quality Rules
- Subject lines must be specific — never "Hello" or "Quick question"
- Keep paragraphs under 4 sentences
- One call to action per email
- Proofread for grammar and tone consistency
- Mark placeholders with [brackets] — never leave them empty