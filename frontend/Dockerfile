# SKPL Agent Frontend Dockerfile
# Multi-stage build: build with Node, serve with vite preview
#
# Usage:
#   docker build -f Dockerfile -t skpl-agent-frontend .
#   docker run -p 4173:4173 skpl-agent-frontend

# ===== Stage 1: Build =====
FROM node:22-alpine AS builder

WORKDIR /app

# Use Aliyun npm mirror for faster downloads (China network)
RUN npm config set registry https://registry.npmmirror.com

# Copy package files first for better layer caching
COPY package.json package-lock.json pnpm-workspace.yaml .npmrc ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Build the frontend
RUN npm run build

# ===== Stage 2: Runtime =====
FROM node:22-alpine AS runtime

WORKDIR /app

# Use Aliyun npm mirror
RUN npm config set registry https://registry.npmmirror.com

# Copy package files and install only production deps
COPY --from=builder /app/package.json /app/package-lock.json /app/pnpm-workspace.yaml /app/.npmrc ./
RUN npm install --legacy-peer-deps --omit=dev

# Copy built assets
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/index.html ./
COPY --from=builder /app/vite.config.ts ./

# Create non-root user
RUN adduser --disabled-password --gecos "" skpl && \
    chown -R skpl:skpl /app

USER skpl

EXPOSE 4173

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:4173/', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "4173"]