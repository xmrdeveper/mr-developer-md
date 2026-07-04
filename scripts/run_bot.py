#!/usr/bin/env python3
"""Entry point to run the Telegram pairing bot with robust startup and import-time diagnostics.

This file performs imports lazily and prints full tracebacks on import/run failures so
platform logs (Railway) show the real error instead of a silent crash during module import.
"""
import os
import sys
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

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

    # Lazy import of the bot module so import errors are caught and logged cleanly
    try:
        from bot.telegram_bot import TelegramPairingBot
    except Exception:
        print('Failed to import bot.telegram_bot — printing traceback to help diagnose the issue:', file=sys.stderr)
        traceback.print_exc()
        # Keep process alive briefly so logs are captured by the host platform
        try:
            threading.Event().wait(60)
        except KeyboardInterrupt:
            pass
        # Re-raise so the process exits with a non-zero status (deployment will show failure)
        raise

    try:
        bot = TelegramPairingBot(token)
        bot.run()
    except Exception:
        print('Exception while running the bot — printing traceback:', file=sys.stderr)
        traceback.print_exc()
        # keep process alive briefly so logs are visible in Railway
        try:
            threading.Event().wait(10)
        except KeyboardInterrupt:
            pass
        raise
