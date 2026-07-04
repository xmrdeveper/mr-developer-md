FROM python:3.11-slim

WORKDIR /app

# install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV DATA_DIR=/app/auth_states

CMD ["python", "scripts/run_bot.py"]
