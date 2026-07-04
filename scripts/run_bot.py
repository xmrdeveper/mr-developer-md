#!/usr/bin/env python3
"""Entry point to run the Telegram pairing bot with a friendly Railway-safe startup.

If TELEGRAM_TOKEN is missing the process will expose a small HTTP health endpoint
so the container stays alive and Railway logs show a clear error message instead of
crashing immediately.
"""
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

from bot.telegram_bot import TelegramPairingBot

PORT = int(os.getenv('PORT', os.getenv('RAILWAY_PORT', '8080')))

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        token = os.getenv('TELEGRAM_TOKEN')
        if token:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'OK - TELEGRAM_TOKEN present')
        else:
            self.send_response(503)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            msg = 'MISCONFIGURED - TELEGRAM_TOKEN not set in environment. See .env.example'
            self.wfile.write(msg.encode('utf-8'))

def start_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f'Health server listening on 0.0.0.0:{PORT}')
    return server

if __name__ == '__main__':
    start_health_server()

    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        # Keep process alive for debugging in the host platform (Railway) so logs are visible
        print('ERROR: TELEGRAM_TOKEN not set. Copy .env.example to .env and set TELEGRAM_TOKEN.', file=sys.stderr)
        print('The health endpoint will report MISCONFIGURED until TELEGRAM_TOKEN is set.')
        try:
            # sleep forever
            threading.Event().wait()
        except KeyboardInterrupt:
            print('Exiting on KeyboardInterrupt')
            sys.exit(1)

    try:
        bot = TelegramPairingBot(token)
        bot.run()
    except Exception as e:
        # Log the exception clearly and keep process alive briefly to ensure logs are collected
        import traceback
        traceback.print_exc()
        print('Bot crashed: see traceback above', file=sys.stderr)
        # keep process alive for a short while so logs are visible in Railway
        try:
            threading.Event().wait(10)
        except KeyboardInterrupt:
            pass
        raise
