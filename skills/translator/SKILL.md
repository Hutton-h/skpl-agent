---
name: translator
description: Professional multi-language translation with reflection-based quality assurance. Delegates translation to a dedicated sub-agent via TeamCreate/AgentCreate and verifies quality before delivery.
version: 1.1.0
category: productivity
when_to_use: User requests translation of text, documents, or messages between any language pair, or needs content rendered in a different language.
---

# Translator Skill

## Hard Requirement
NEVER translate inline in the main conversation. Always delegate to a translator sub-agent so the main context stays clean and quality can be reviewed independently.

## Workflow (follow in order)

### Step 1: TeamCreate — REQUIRED FIRST STEP
Call `TeamCreate` with a descriptive name, e.g. `translation-zh-en-<topic>`.
Skipping this step causes `AgentCreate` to fail. Do not attempt AgentCreate before TeamCreate succeeds.

### Step 2: AgentCreate — create the translator sub-agent
Use a system prompt like:

```
You are a professional translator. Translate the text provided by the team leader from {SOURCE} to {TARGET}.

Rules:
1. Preserve the original formatting: paragraphs, lists, headings, tables.
2. Keep code blocks, URLs, file paths, and technical identifiers unchanged.
3. Translate naturally, not word-for-word; adapt idioms and cultural references.
4. Preserve tone (formal/casual/marketing/technical).
5. When finished, you MUST report the complete translation back to the team leader via TeamSay. The leader is blocked waiting for your TeamSay message — a normal reply is not enough.
```

### Step 3: TeamSay the task
Send the translator: the source text, source/target languages, and any style requirements.

### Step 4: Wait for the TeamSay reply
Do not proceed until the translator reports back.

### Step 5: Reflection-based quality review
Check the returned translation for:
- Accuracy — no meaning shifts or omissions
- Completeness — every sentence translated
- Fluency — natural phrasing in the target language
- Formatting — structure preserved

If any check fails, TeamSay specific revision instructions to the translator ONCE, then re-review.

### Step 6: Deliver + clean up
Present the final translation to the user, then call `TeamDelete` to release the team.

## Long Documents
Translate section by section (one TeamSay per section), then merge in order before delivery.

## Supported Languages
Chinese (Simplified/Traditional), English, Japanese, Korean, French, German, Spanish, Russian, Arabic, Portuguese, and more — the sub-agent translates any pair the underlying model supports.
