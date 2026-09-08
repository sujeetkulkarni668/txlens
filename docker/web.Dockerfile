# TxLens web frontend image.
# STATUS: not built/verified in this environment (no Docker, no network to
# run `npm install`). Build context is the repo ROOT (not apps/web), since
# apps/web depends on the @txlens/shared-types workspace package — npm
# workspaces need the whole monorepo present to symlink it correctly.
# Validate locally with:
#   docker build -f docker/web.Dockerfile -t txlens-web .

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
COPY apps/web/package.json apps/web/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
COPY packages/blockchain/package.json packages/blockchain/package.json
RUN npm install

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build --workspace=apps/web

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/apps/web/next.config.* ./apps/web/
COPY --from=builder /app/apps/web/public ./apps/web/public
COPY --from=builder /app/apps/web/.next ./apps/web/.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/apps/web/package.json ./apps/web/package.json

WORKDIR /app/apps/web
EXPOSE 3000
CMD ["npm", "start"]
