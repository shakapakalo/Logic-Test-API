FROM node:20-alpine

WORKDIR /app

COPY server/package.json ./
RUN npm install --production=false

COPY server/ ./
RUN npm run build

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "dist/index.js"]
