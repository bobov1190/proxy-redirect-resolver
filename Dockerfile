FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Копируем зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Переменные окружения для оптимизации
ENV PORT=8000
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# Ограничиваем использование памяти
ENV NODE_OPTIONS="--max-old-space-size=512"

EXPOSE 8000

# Запуск с ограничением воркеров
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "30"]