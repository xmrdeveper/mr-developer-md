"""Simple storage layer for session and pairing persistence.
Supports optional encryption using PASS_PHRASE from env via Fernet.
"""
import os
import json
from pathlib import Path
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64

PASS_PHRASE = os.getenv('PASS_PHRASE')

def _derive_key(passphrase: str, salt: bytes = b"mr-developer-md") -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))

class Storage:
    def __init__(self, base_dir: str = './auth_states'):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)
        self._fernet = None
        if PASS_PHRASE:
            key = _derive_key(PASS_PHRASE)
            self._fernet = Fernet(key)

    def _path_for(self, telegram_id: str, suffix: str):
        return self.base / f"{telegram_id}.{suffix}.json"

    def save_pairing(self, telegram_id: str, data: dict):
        p = self._path_for(telegram_id, 'pairing')
        self._write_json(p, data)

    def load_pairing(self, telegram_id: str):
        p = self._path_for(telegram_id, 'pairing')
        return self._read_json(p)

    def delete_pairing(self, telegram_id: str):
        p = self._path_for(telegram_id, 'pairing')
        if p.exists():
            p.unlink()
            return True
        return False

    def save_session(self, telegram_id: str, data: dict):
        p = self._path_for(telegram_id, 'session')
        data['updated_at'] = datetime.utcnow().isoformat()
        self._write_json(p, data)

    def load_session(self, telegram_id: str):
        p = self._path_for(telegram_id, 'session')
        return self._read_json(p)

    def delete_session(self, telegram_id: str):
        p = self._path_for(telegram_id, 'session')
        if p.exists():
            p.unlink()
            return True
        return False

    def list_sessions(self):
        out = []
        for f in self.base.glob('*.session.json'):
            try:
                with f.open('r') as fh:
                    out.append(json.load(fh))
            except Exception:
                continue
        return out

    def _write_json(self, path: Path, data: dict):
        raw = json.dumps(data, indent=2).encode('utf-8')
        if self._fernet:
            raw = self._fernet.encrypt(raw)
        with path.open('wb') as fh:
            fh.write(raw)

    def _read_json(self, path: Path):
        if not path.exists():
            return None
        raw = path.read_bytes()
        if self._fernet:
            try:
                raw = self._fernet.decrypt(raw)
            except Exception:
                return None
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return None
