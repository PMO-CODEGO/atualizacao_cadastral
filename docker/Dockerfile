FROM python:3.12-slim-bookworm

WORKDIR /app

# Dependências de sistema: build de pacotes Python com extensões nativas,
# client do MySQL, e libs de renderização do WeasyPrint (geração de PDF).
# Fixado em "bookworm" por estabilidade desses pacotes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    default-libmysqlclient-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    fonts-liberation \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
