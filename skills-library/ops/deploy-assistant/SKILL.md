---
name: deploy-assistant
description: Deployment workflow — helps with Docker Compose, Kubernetes, and cloud deployment configurations.
version: 1.0.0
category: ops
when_to_use: User asks about deployment, Docker, Kubernetes, or needs help configuring production infrastructure.
---
# Deployment Assistant Skill — 部署助手

## Goal
Help the user configure and execute deployments with Docker Compose, Kubernetes, or cloud platforms.

## Available Tools
Read, Grep, Glob, RunPython, Write.

## Workflow

### Step 1: Infrastructure Analysis
- Review existing deployment configuration
- Identify the target platform (Docker, K8s, VPS)
- Check for security and performance requirements

### Step 2: Configuration Generation
- Generate Docker Compose files with proper health checks
- Create Kubernetes manifests with resource limits
- Configure environment variables and secrets management

### Step 3: Deployment Execution
- Build and push images
- Apply configurations
- Verify deployment health

### Step 4: Monitoring Setup
- Configure health check endpoints
- Set up basic monitoring and alerting
- Document rollback procedures

## Quality Rules
- Never expose secrets in configuration files
- Always include health checks for all services
- Use specific version tags, never `latest`
- Document the rollback procedure
