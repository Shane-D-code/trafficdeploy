FROM node:20-bookworm

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/package*.json /app/backend/
WORKDIR /app/backend
RUN npm install --omit=dev

COPY backend/ /app/backend/
RUN npm run build

WORKDIR /app
COPY frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm install

COPY frontend/ /app/frontend/
RUN npm run build

WORKDIR /app
COPY traffic_violation_project/ /app/traffic_violation_project/
WORKDIR /app/traffic_violation_project
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
RUN mkdir -p data uploads evidence

WORKDIR /app/backend
EXPOSE 5000

CMD ["sh", "-c", "node dist/app.js"]
