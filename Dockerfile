FROM python:3.11-slim

WORKDIR /app

# Install OS build dependencies required by some Python packages (cryptography, Pillow)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libssl-dev \
       libffi-dev \
       python3-dev \
       libjpeg-dev \
       zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app

# Default data dir inside container (mount your persistent volume here)
ENV DATA_DIR=/data/auth_states

CMD ["python", "scripts/run_bot.py"]
