"""Placeholder WhatsApp adapter for the scaffold.
This adapter simulates generating a pairing QR and keeps a minimal session file.
Replace this with a real WhatsApp Multi-Device client integration (Baileys/Node service) in production.
"""
import io
import os
import time
import qrcode
import secrets
from datetime import datetime

class WhatsAppAdapter:
    def __init__(self, storage):
        self.storage = storage

    def start_pairing(self, telegram_id: str, label: str = None):
        """Generate a pairing code and QR image (placeholder).
        Returns (qr_bytes, code)
        """
        code = secrets.token_hex(4)
        payload = f'PAIR|{telegram_id}|{label or "default"}|{code}|{int(time.time())}'
        img = qrcode.make(payload)
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        # store a temporary pairing record
        pairing = {
            'telegram_id': telegram_id,
            'label': label,
            'code': code,
            'created_at': datetime.utcnow().isoformat()
        }
        self.storage.save_pairing(telegram_id, pairing)
        return bio, code

    def confirm_pairing(self, telegram_id: str, code: str, session_data: dict):
        # verify pairing record
        rec = self.storage.load_pairing(telegram_id)
        if not rec or rec.get('code') != code:
            raise RuntimeError('Invalid pairing code')
        session = {
            'label': rec.get('label') or 'default',
            'paired_at': datetime.utcnow().isoformat(),
            'session_data': session_data
        }
        self.storage.save_session(telegram_id, session)
        self.storage.delete_pairing(telegram_id)
        return session

    def send_message(self, telegram_id: str, to: str, text: str):
        # placeholder: record message in session file (simulate send)
        s = self.storage.load_session(telegram_id)
        if not s:
            raise RuntimeError('No active session')
        # append outgoing message
        out = s.get('outgoing', [])
        out.append({'to': to, 'text': text, 'ts': datetime.utcnow().isoformat()})
        s['outgoing'] = out
        self.storage.save_session(telegram_id, s)
        return True
