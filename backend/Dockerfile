FROM node:18-alpine

RUN apk add --no-cache python3 py3-pip py3-numpy py3-opencv py3-pillow

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY dist ./dist

EXPOSE 5000

CMD ["node", "dist/app.js"]
