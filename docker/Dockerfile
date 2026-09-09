FROM python:3.12-slim-bookworm

WORKDIR /app

# Dependências de sistema mínimas (build de pacotes Python com extensões nativas
# e client do MySQL). Fixado em "bookworm" por estabilidade dos pacotes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
