FROM node:20-alpine

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .

EXPOSE 5173

CMD ["sh", "-c", "if [ \"$APP_ENV\" = \"production\" ]; then npm run build && npm run preview -- --host 0.0.0.0 --port 5173; else npm run dev -- --host 0.0.0.0 --port 5173; fi"]
