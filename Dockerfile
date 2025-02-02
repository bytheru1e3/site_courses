# Используем более легкий базовый образ
FROM python:3.10-slim

# Устанавливаем системные зависимости и удаляем кеши
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Настраиваем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python-зависимости и удаляем кеши
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

# Копируем остальные файлы проекта
COPY . .

# Указываем команду запуска контейнера
CMD ["python", "app.py"]