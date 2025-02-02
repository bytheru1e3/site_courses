# Используем более легкий базовый образ
FROM python:3.10-slim

# Добавляем публичные ключи для репозиториев Debian
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0E98404D386FA1D9 6ED0E7B82643E131 F8D2585B8783D481 54404762BBB6E853 BDE6D2B9216EC7A8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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