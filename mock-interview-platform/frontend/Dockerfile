FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --silent

COPY . .

EXPOSE 3000

CMD ["sh", "-c", "npm run build && npm run start"]
