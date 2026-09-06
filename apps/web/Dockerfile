FROM node:20-alpine AS deps

WORKDIR /app

RUN apk upgrade --no-cache

COPY package*.json ./
RUN npm ci

FROM node:20-alpine AS builder

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

RUN apk upgrade --no-cache

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build
RUN node -e "const fs = require('fs'); for (const file of ['./.next/standalone/package.json', './.next/standalone/node_modules/next/package.json']) { const pkg = JSON.parse(fs.readFileSync(file, 'utf8')); delete pkg.devDependencies; delete pkg.scripts; fs.writeFileSync(file, JSON.stringify(pkg, null, 2)); }" \
    && rm -rf .next/standalone/node_modules/next/dist/compiled/@vercel/nft .next/standalone/node_modules/next/dist/compiled/cross-spawn .next/standalone/node_modules/next/dist/compiled/tar

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

RUN addgroup -S nodejs \
    && adduser -S nextjs -G nodejs -u 10001 \
    && apk upgrade --no-cache

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
RUN rm -f package-lock.json \
    && npm install --omit=dev --package-lock=false --ignore-scripts --no-audit --no-fund cross-spawn@7.0.5 tar@7.5.21 \
    && rm -rf node_modules/next/dist/compiled/@vercel/nft node_modules/next/dist/compiled/cross-spawn node_modules/next/dist/compiled/tar \
    && cp -R node_modules/cross-spawn node_modules/next/dist/compiled/cross-spawn \
    && cp -R node_modules/tar node_modules/next/dist/compiled/tar \
    && node -e "const fs = require('fs'); for (const file of ['./package.json', './node_modules/next/package.json']) { const pkg = JSON.parse(fs.readFileSync(file, 'utf8')); delete pkg.devDependencies; delete pkg.scripts; fs.writeFileSync(file, JSON.stringify(pkg, null, 2)); }" \
    && npm cache clean --force \
    && rm -rf /root/.npm /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000').then((response) => process.exit(response.ok ? 0 : 1)).catch(() => process.exit(1))"

CMD ["node", "server.js"]
