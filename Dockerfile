# Используем образ с уже установленным Playwright
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

WORKDIR /app

# Копируем зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Переменные окружения
ENV PORT=8000

EXPOSE 8000

# Запуск
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]