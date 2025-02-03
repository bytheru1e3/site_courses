# Используем официальный образ Python
FROM python:3.10-slim-buster

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Настраиваем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем директории для данных
RUN mkdir -p /app/data/vector_db_cache && \
    mkdir -p /app/uploads

# Запускаем бота
CMD ["python", "run_bot.py"]
