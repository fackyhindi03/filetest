# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

FROM python:3.10.8-slim-buster

# Install system dependencies
RUN apt update && apt upgrade -y \
    && apt install -y git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /requirements.txt
RUN pip3 install --upgrade pip \
    && pip3 install --no-cache-dir -r /requirements.txt

# Create application directory
WORKDIR /VJ-File-Store
COPY . /VJ-File-Store

# Expose HTTP port for streaming server
EXPOSE 8080

# Start both the Telegram bot and the aiohttp web server
# Using a shell to background the web server before launching the bot
CMD ["sh", "-c", "python web_server.py & python bot.py"]
