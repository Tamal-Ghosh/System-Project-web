FROM node:24-bookworm-slim
ENV NPM_CONFIG_CACHE=/tmp/npm-cache
WORKDIR /app
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN npm ci && node -e "require('fs').writeFileSync('node_modules/.dermascope-lock',require('crypto').createHash('sha256').update(require('fs').readFileSync('package-lock.json')).digest('hex'))" \
    && chown -R node:node /app
COPY --chown=node:node frontend/ ./
COPY docker/frontend-entrypoint.cjs /opt/frontend-entrypoint.cjs
USER node
EXPOSE 5173
ENTRYPOINT ["node", "/opt/frontend-entrypoint.cjs"]
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
