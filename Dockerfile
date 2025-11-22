FROM python:3.12-slim

WORKDIR /app

# Встановлення залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання кода та ресурсів
COPY main.py .
COPY templates ./templates
COPY static ./static

EXPOSE 3000 5000

CMD ["python", "main.py"]