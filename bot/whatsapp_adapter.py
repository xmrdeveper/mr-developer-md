"""Placeholder WhatsApp adapter extended to handle incoming WA commands.

This adapter remains a placeholder for testing and demo. It recognizes dot- and slash-prefixed
commands and performs scaffolded actions using the Storage layer.

Key behaviors implemented for Phase A:
- .pair <label?> -> generate pairing code/QR and save pairing record under wa:{jid}
- .unpair -> remove session stored under wa:{jid}
- .status / .session -> show session information
- .send <phone> <message> -> store outgoing message in session (simulates send)
- .help / .menu / .ping / .alive -> respond with scaffolded info
- Other commands -> return an informative placeholder response

For production, replace this adapter with a real WhatsApp Multi-Device client (e.g., Baileys)
that calls these handlers when messages arrive.
"""
import io
import os
import time
import qrcode
import secrets
from datetime import datetime
from typing import Tuple, Optional

from bot.storage import Storage

class WhatsAppAdapter:
    def __init__(self, storage: Storage):
        self.storage = storage

    def start_pairing(self, owner_id: str, label: Optional[str] = None) -> Tuple[bytes, str]:
        """Generate a pairing code and QR image (placeholder).
        owner_id is an identifier for who requested pairing (telegram_id or wa:{jid}).
        Returns (qr_bytes, code)
        """
        code = secrets.token_hex(4)
        payload = f'PAIR|{owner_id}|{label or "default"}|{code}|{int(time.time())}'
        img = qrcode.make(payload)
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        pairing = {
            'owner_id': owner_id,
            'label': label,
            'code': code,
            'created_at': datetime.utcnow().isoformat()
        }
        # store pairing record keyed by owner_id
        self.storage.save_pairing(owner_id, pairing)
        return bio.getvalue(), code

    def confirm_pairing(self, owner_id: str, code: str, session_data: dict):
        rec = self.storage.load_pairing(owner_id)
        if not rec or rec.get('code') != code:
            raise RuntimeError('Invalid pairing code')
        session = {
            'label': rec.get('label') or 'default',
            'paired_at': datetime.utcnow().isoformat(),
            'session_data': session_data
        }
        self.storage.save_session(owner_id, session)
        self.storage.delete_pairing(owner_id)
        return session

    def send_message(self, owner_id: str, to: str, text: str):
        # placeholder: record message in session file (simulate send)
        s = self.storage.load_session(owner_id)
        if not s:
            raise RuntimeError('No active session')
        out = s.get('outgoing', [])
        out.append({'to': to, 'text': text, 'ts': datetime.utcnow().isoformat()})
        s['outgoing'] = out
        self.storage.save_session(owner_id, s)
        return True

    def handle_incoming(self, from_jid: str, text: str) -> Tuple[Optional[bytes], str]:
        """Handle an incoming WhatsApp message text from from_jid (e.g., '123456789@s.whatsapp.net').
        Returns (optional_binary_payload, response_text). If binary is returned, callers may send it as an image.
        """
        if not text:
            return None, 'Empty message.'

        text = text.strip()
        # accept dot or slash prefixes
        if text.startswith('.') or text.startswith('/') or text.startswith('!'):
            prefix = text[0]
            parts = text[1:].split()
            cmd = parts[0].lower()
            args = parts[1:]
        else:
            # not a command: ignore or respond with short help
            return None, 'Send .help to see available commands.'

        owner_key = f'wa:{from_jid}'

        try:
            if cmd in ('help', 'menu'):
                return None, self._format_menu()

            if cmd in ('ping', 'alive'):
                return None, 'PONG — TYLA X WhatsApp Bot (scaffold)'

            if cmd in ('pair', 'link'):
                label = args[0] if args else None
                img_bytes, code = self.start_pairing(owner_key, label)
                # Return image bytes and a short caption including the code
                caption = f'Pairing code: {code} — send this code to the Telegram bot (/pair {code}) or keep it to confirm pairing.'
                return img_bytes, caption

            if cmd in ('unpair', 'clearsession', 'resetsession'):
                ok = self.storage.delete_session(owner_key)
                return None, 'Unpaired.' if ok else 'No active session to unpair.'

            if cmd in ('status', 'session'):
                s = self.storage.load_session(owner_key)
                if not s:
                    return None, 'No active session.'
                pretty = json_safe_dump(s)
                return None, f'Session info:\n{pretty}'

            if cmd == 'send':
                if len(args) < 2:
                    return None, 'Usage: .send <phone> <message>'
                to = args[0]
                msg = ' '.join(args[1:])
                try:
                    self.send_message(owner_key, to, msg)
                    return None, 'Message queued (scaffold).'
                except Exception as e:
                    return None, 'Failed to send: ' + str(e)

            if cmd in ('sessions', 'users'):
                # only list sessions summary
                sessions = self.storage.list_sessions()
                return None, f'Active sessions: {len(sessions)}'

            if cmd in ('ban', 'unban'):
                # privileged operations — scaffold will just inform
                return None, f'Command {cmd} received. Owner-only action (not performed via scaffold).'

            # Fallback for many commands: acknowledge and provide placeholder
            return None, f'Command .{cmd} recognized — behavior not implemented in scaffold. Use /help for Telegram usage.'
        except Exception as e:
            return None, 'Error handling command: ' + str(e)

    def _format_menu(self) -> str:
        # minimal menu to avoid huge message payload
        return ("TYLA X WhatsApp Bot (scaffold) — available commands:\n"
                ".help, .pair <label?>, .unpair, .status, .session, .send <phone> <message>, .ping\n"
                "For full feature set see the project README.")


# small helper to safely dump JSON-like session info without importing json at top-level repeatedly
import json

def json_safe_dump(obj) -> str:
    try:
        return json.dumps(obj, indent=2)
    except Exception:
        return str(obj)
