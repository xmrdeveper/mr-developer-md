// name=examples/wa-telegram-pair.js
// Minimal WhatsApp <-> Telegram pairing example using Baileys and node-telegram-bot-api
// Install: npm i @adiwajshing/baileys qrcode node-telegram-bot-api
// Run: TELEGRAM_TOKEN=... node examples/wa-telegram-pair.js

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@adiwajshing/baileys');
const TelegramBot = require('node-telegram-bot-api');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');

const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN;
const DATA_DIR = process.env.DATA_DIR || path.resolve('./auth_states');

if (!TELEGRAM_TOKEN) {
  console.error('Please set TELEGRAM_TOKEN environment variable');
  process.exit(1);
}

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

const tg = new TelegramBot(TELEGRAM_TOKEN, { polling: true });

// in-memory map of telegramId -> { sock, authDir, phone }
const sessions = new Map();

async function startWhatsAppForTelegramUser(telegramId, phoneLabel) {
  const safeLabel = phoneLabel ? `${String(telegramId)}-${phoneLabel}` : String(telegramId);
  const authDir = path.join(DATA_DIR, safeLabel);

  if (!fs.existsSync(authDir)) fs.mkdirSync(authDir, { recursive: true });

  const { state, saveCreds } = await useMultiFileAuthState(authDir);

  const sock = makeWASocket({
    printQRInTerminal: false,
    auth: state,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      try {
        const png = await qrcode.toBuffer(qr, { type: 'png', scale: 6 });
        await tg.sendPhoto(telegramId, png, { caption: 'Scan this QR with WhatsApp (expires quickly)' });
      } catch (err) {
        console.error('QR -> Telegram error', err);
        await tg.sendMessage(telegramId, 'Failed to send QR: ' + String(err));
      }
    }

    if (connection === 'open') {
      await tg.sendMessage(telegramId, 'WhatsApp paired successfully ✅');
      console.log(`WhatsApp session opened for Telegram user ${telegramId} (${phoneLabel || 'default'})`);
    }

    if (connection === 'close') {
      const loggedOut = lastDisconnect && lastDisconnect.error && lastDisconnect.error.output && lastDisconnect.error.output.statusCode === DisconnectReason.loggedOut;
      console.log('WhatsApp connection closed', { loggedOut, lastDisconnect });
      if (loggedOut) {
        await tg.sendMessage(telegramId, 'WhatsApp session logged out. Use /pair to pair again.');
        // Optionally remove saved auth state here
      }
    }
  });

  sessions.set(String(telegramId), { sock, authDir, phone: phoneLabel || null });
  return sock;
}

async function stopSession(telegramId) {
  const s = sessions.get(String(telegramId));
  if (!s) return false;
  try {
    await s.sock.logout();
  } catch (e) {
    console.warn('Logout error', e?.message || e);
  }
  // delete auth dir
  try {
    const rimraf = (p) => {
      if (fs.existsSync(p)) {
        fs.readdirSync(p).forEach(f => {
          const cur = path.join(p, f);
          if (fs.lstatSync(cur).isDirectory()) rimraf(cur);
          else fs.unlinkSync(cur);
        });
        fs.rmdirSync(p);
      }
    };
    rimraf(s.authDir);
  } catch (e) {
    console.warn('Auth dir cleanup failed', e?.message || e);
  }
  sessions.delete(String(telegramId));
  return true;
}

// Commands:
// /pair [phone]
// /unpair
// /status
// /send <phone> <message>  (example command to send a message)

tg.onText(/\/pair(?:\s+(\S+))?/, async (msg, match) => {
  const telegramId = msg.from.id;
  const phone = match && match[1] ? match[1] : null;

  if (sessions.has(String(telegramId))) {
    await tg.sendMessage(telegramId, 'A session is already active. Use /unpair to remove it first.');
    return;
  }

  await tg.sendMessage(telegramId, 'Starting pairing... I will send you a WhatsApp QR to scan.');
  try {
    await startWhatsAppForTelegramUser(telegramId, phone);
  } catch (err) {
    console.error('Start WA error', err);
    await tg.sendMessage(telegramId, 'Failed to start pairing: ' + err.message);
  }
});

tg.onText(/\/unpair/, async (msg) => {
  const telegramId = msg.from.id;
  const ok = await stopSession(telegramId);
  if (!ok) return tg.sendMessage(telegramId, 'No active session to unpair.');
  await tg.sendMessage(telegramId, 'Session unpaired and cleaned up.');
});

tg.onText(/\/status/, async (msg) => {
  const telegramId = msg.from.id;
  const s = sessions.get(String(telegramId));
  if (!s) return tg.sendMessage(telegramId, 'No active WhatsApp session.');
  try {
    const user = s.sock.user || {};
    await tg.sendMessage(telegramId, `WhatsApp session active${s.phone ? ` (label: ${s.phone})` : ''} for: ${user.name || user.id || 'unknown'}`);
  } catch (e) {
    await tg.sendMessage(telegramId, 'Could not determine session status.');
  }
});

// Simple send command: /send <phone> <message>
// Phone must be in WhatsApp format: 2348012345678@s.whatsapp.net or 2348012345678
tg.onText(/\/send\s+(\S+)\s+([\s\S]+)/, async (msg, match) => {
  const telegramId = msg.from.id;
  const s = sessions.get(String(telegramId));
  if (!s) return tg.sendMessage(telegramId, 'No active session. Use /pair first.');

  let to = match[1];
  const text = match[2];
  if (!to.includes('@')) to = to.replace(/[^0-9]/g, '') + '@s.whatsapp.net';

  try {
    await s.sock.sendMessage(to, { text });
    await tg.sendMessage(telegramId, 'Message sent');
  } catch (e) {
    console.error('sendMessage error', e);
    await tg.sendMessage(telegramId, 'Failed to send message: ' + (e?.message || e));
  }
});

console.log('Telegram pairing bot running. Use /pair to start.');
