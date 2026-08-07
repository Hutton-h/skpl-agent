---
name: scheduler
description: Scheduled task management workflow — creates, lists, updates, and monitors recurring tasks with conditional triggers, failure retry logic, and execution history tracking.
version: 1.0.0
category: automation
when_to_use: User asks to schedule a recurring task, set up a cron job, automate a periodic workflow, or manage scheduled tasks.
---

# Scheduler Skill — 定时任务管理

## Goal
Help the user create, manage, and monitor scheduled tasks through the SKPL schedule system — from defining the trigger to verifying execution and handling failures.

## Available Tools
The `schedule` tool (built-in) for creating/managing scheduled tasks. RunPython for custom trigger logic.

## Workflow

### Step 1: Requirement Gathering
Clarify the task to be scheduled:
- **What**: the exact task description (will become the schedule's message)
- **When**: frequency (daily, weekly, specific days, time of day)
- **Output**: where should results go? File, notification, chat?
- **Failure behavior**: retry? notify on failure? skip?

### Step 2: Cron Expression Building
Convert the user's schedule description to a cron expression:
- Daily at 9 AM: `0 9 * * *`
- Weekdays at 8 AM: `0 8 * * 1-5`
- Every Monday: `0 9 * * 1`
- First of month: `0 9 1 * *`
- Every 30 minutes: `*/30 * * * *`

**Limitation**: 5-field cron cannot express "third Friday of month" or "every other week". Inform the user and suggest the closest alternative.

### Step 3: Task Creation
Create the scheduled task with:
- `name`: short human-readable label
- `message`: detailed task description including output path, format, and gating rules
- `cron_expression`: the trigger schedule
- `timezone`: user's timezone (default: Asia/Shanghai)

Include in the message:
- Output file path and format
- "Skip if today's output already exists" rule
- "Only run if new items are found" rule
- Notification preference (notify / silent)

### Step 4: Verification
After creation:
- List existing tasks to confirm the new one appears
- If possible, trigger a test run immediately
- Show the user how to pause, resume, or delete the task

### Step 5: Monitoring
Periodically check:
- Execution history: last run time, success/failure
- Failure alerts: if a task fails, suggest remediation
- Schedule drift: if the task's timing no longer matches the intent

## Quality Rules
- Cron expressions must be validated before creation
- Minimum interval is 10 minutes — warn if user requests more frequent
- Include gating rules in the message to prevent duplicate work
- Always confirm the created task with the user