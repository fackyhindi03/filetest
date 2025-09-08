FROM python:3.10-slim-bookworm

# Install OS deps in one layer, no upgrades
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

# App setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "bot.py"]
