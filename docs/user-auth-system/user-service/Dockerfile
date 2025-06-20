FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Команда для запуска тестов при сборке (если установлена переменная RUN_TESTS)
RUN if [ "$RUN_TESTS" = "true" ]; then \
        coverage run -m unittest discover -s tests && \
        coverage report; \
    fi

# Добавим задержку перед запуском
CMD sleep 10 && python app.py
