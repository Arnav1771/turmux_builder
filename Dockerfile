# Dockerfile for AppBuilder Discord Bot
# Optimized for Fly.io free tier deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full appbuilder source
COPY . .

# Don't run as root
RUN useradd -m botuser && chown -R botuser /app
USER botuser

# Run the Discord bot
CMD ["python", "discord_bot/bot.py"]
