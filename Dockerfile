# Dockerfile
FROM python:3.13-slim

# Зависимости для Linux + Playwright
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libgtk-3-0 libasound2 \
    libpangocairo-1.0-0 libxcb1 libx11-xcb1 libx11-6 libxshmfence1 libxi6 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Устанавливаем Playwright Chromium
RUN playwright install chromium
RUN playwright install-deps chromium

# Копируем код
COPY . .

# Render порт
ENV PORT=8000
EXPOSE 8000

# Запуск
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
