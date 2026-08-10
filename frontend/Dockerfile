# SKPL Agent Frontend Dockerfile
# Multi-stage build: build with Node + pnpm, serve with vite preview
#
# Usage:
#   docker build -f frontend/Dockerfile -t skpl-agent-frontend .
#   docker run -p 4173:4173 skpl-agent-frontend

# ===== Stage 1: Build =====
FROM node:22-alpine AS builder

WORKDIR /app

# Enable corepack for pnpm
RUN corepack enable && corepack prepare pnpm@11.17.0 --activate

# Use Aliyun npm mirror for faster downloads (China network)
RUN npm config set registry https://registry.npmmirror.com

# Copy package files first for better layer caching
# (pnpm-lock.yaml may not exist yet; pnpm install will generate it)
COPY frontend/package.json frontend/pnpm-workspace.yaml frontend/.npmrc ./
COPY frontend/pnpm-lock.yaml* ./

# Install dependencies with pnpm
RUN pnpm install --no-frozen-lockfile

# Copy source code
COPY frontend/ .

# Build the frontend
RUN pnpm run build

# ===== Stage 2: Runtime =====
FROM node:22-alpine AS runtime

WORKDIR /app

# Enable corepack for pnpm
RUN corepack enable && corepack prepare pnpm@11.17.0 --activate

# Use Aliyun npm mirror
RUN npm config set registry https://registry.npmmirror.com

# Copy package files and install only production deps
COPY --from=builder /app/package.json /app/pnpm-lock.yaml /app/pnpm-workspace.yaml /app/.npmrc ./
RUN pnpm install --prod --no-frozen-lockfile

# Copy built assets
COPY --from=builder /app/dist ./dist

# Create non-root user
RUN adduser --disabled-password --gecos "" skpl && \
    chown -R skpl:skpl /app

USER skpl

EXPOSE 4173

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:4173/', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "4173"]