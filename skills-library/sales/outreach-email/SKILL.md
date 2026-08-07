---
name: outreach-email
description: Cold outreach email workflow. Personalizes messaging from lead data, builds a 3-email follow-up sequence (initial, day-3, day-7) with A/B variants, and exports the sequence to files.
version: 1.0.0
category: sales
when_to_use: User asks to write cold/outreach/sales emails, build a follow-up email sequence, or generate personalized outreach from a lead list.
---

# Outreach Email Skill — 外联邮件

## Goal
Produce a personalized 3-touch email sequence (initial / +3 days / +7 days), each with A and B variants, exported as files ready to send.

## Available Tools
Read, search_web, scrape (firecrawl), RunPython, Write, docwriter skill, translator skill (for foreign-language leads).

## Workflow

### Step 1: Gather inputs
- Lead info: from the user's list (Read/RunPython on xlsx/csv) or a described single prospect.
- Offer: product one-liner, core value props, proof points (case study, numbers), call-to-action (meeting link? reply?).
- Sender identity: name, role, company, signature block.
Missing value props? Ask once — never fabricate proof points.

### Step 2: Personalization research (per lead or segment)
If a lead list with websites: `scrape`/`search_web` each target site for 1-2 personalization hooks (recent news, product launch, hiring signal, shared pain). Store hooks next to leads. 每封邮件至少 1 个个性化钩子。

### Step 3: Write the 3-email sequence
Structure per email:
- **Email 1 (Day 0)**: personalized hook -> relevance -> one-sentence value prop -> soft CTA (question, not demand). <= 120 words.
- **Email 2 (Day +3)**: new angle — a proof point/case result -> one-line ask. <= 90 words. Reply-style thread tone.
- **Email 3 (Day +7)**: breakup email — polite close + last-value offer (resource) + easy out. <= 70 words.
Each email: subject line (<= 50 chars), preview text, body, signature.

### Step 4: A/B variants
For each of the 3 emails, produce:
- Version A: benefit-led subject & opening
- Version B: curiosity/question-led subject & opening
Note what to measure (open rate for subject, reply rate for opening).

### Step 5: Export
- Single prospect: one `.md` file with all 6 emails (3 x A/B).
- Lead list: RunPython -> `outreach-sequence.xlsx`: rows = leads, columns = hook, email1_a/b, email2_a/b, email3_a/b, subjects. Tell the user the file is downloadable.
- Non-English targets: delegate translation via the **translator** skill.

## Quality & Compliance Rules
- No false claims, no fake mutual connections, no misleading "Re:" subjects.
- Include an opt-out line suggestion (compliance: CAN-SPAM/GDPR).
- Spam-word check pass: avoid ALL-CAPS, excessive "free/buy now", over-punctuation.
