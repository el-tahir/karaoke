# syntax=docker/dockerfile:1
# -------------------------------------------------------------
# Frontend – Next.js 15
# -------------------------------------------------------------
FROM node:20-alpine AS deps
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# ---- Build stage ----
FROM node:20-alpine AS builder
WORKDIR /app

ENV NODE_ENV=production

# Accept build argument for API base URL
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

# ---- Production image ----
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Next.js needs the built files and node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Cloud Run provides PORT.
ENV PORT 8080
EXPOSE 8080

CMD ["npm", "start", "--", "-p", "8080"] 