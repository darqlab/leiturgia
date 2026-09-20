FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source (see .dockerignore for exclusions)
COPY . /app

EXPOSE 5000

CMD ["python", "app.py"]
