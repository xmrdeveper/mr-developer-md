// examples/wa_set_profile.js
// Example Baileys helper to update WhatsApp profile picture programmatically.
// Requires a working MD session created by Baileys (auth folder).
// Usage:
// 1) npm init -y
// 2) npm install @whiskeysockets/baileys
// 3) node examples/wa_set_profile.js ./auth output_640.jpg

const fs = require('fs');
const path = require('path');
const { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error('Usage: node examples/wa_set_profile.js <authDir> <imagePath>');
    process.exit(2);
  }
  const authDir = args[0];
  const imagePath = args[1];

  if (!fs.existsSync(imagePath)) {
    console.error('Image file not found:', imagePath);
    process.exit(2);
  }

  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version, isLatest } = await fetchLatestBaileysVersion();
  console.log('Baileys version:', version, 'isLatest?', isLatest);

  const sock = makeWASocket({ auth: state, version });
  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect } = update;
    console.log('connection update', connection);
    if (connection === 'close') {
      const code = (lastDisconnect && lastDisconnect.error && lastDisconnect.error.output && lastDisconnect.error.output.statusCode) || null;
      console.log('Disconnected, code:', code);
    }
  });

  // Wait for socket.user to become available
  await new Promise((resolve) => {
    if (sock && sock.user) return resolve();
    const on = (ev) => {
      if (sock.user) {
        sock.ev.off('connection.update', on);
        resolve();
      }
    };
    sock.ev.on('connection.update', on);
    // fallback timeout
    setTimeout(resolve, 5000);
  });

  if (!sock.user) {
    console.warn('Warning: socket.user not available yet — proceeding anyway.');
  }

  try {
    const imgBuffer = fs.readFileSync(imagePath);
    // Many Baileys versions expose updateProfilePicture; if not available, this will throw.
    if (typeof sock.updateProfilePicture === 'function') {
      console.log('Calling sock.updateProfilePicture...');
      await sock.updateProfilePicture(sock.user.id, imgBuffer);
      console.log('Profile picture updated (via updateProfilePicture).');
    } else {
      // Fallback: upload media and set as profile picture via presence of user ID.
      console.log('updateProfilePicture not available on this Baileys version. Attempting fallback...');
      const jid = sock.user && sock.user.id ? sock.user.id : null;
      if (!jid) {
        throw new Error('No user JID available for profile update fallback.');
      }
      // Upload the profile photo as a noiseless message (library behavior may differ)
      const { upload } = require('@whiskeysockets/baileys').DEFAULT; // may not exist in all builds
      if (!upload) throw new Error('Baileys upload helper not available in this build.');
      const { url } = await upload(imgBuffer);
      // There's no standardized fallback; inform user to update manually
      console.log('Uploaded image to temporary url:', url);
      console.log('Please use the library API for your Baileys version to set profile picture programmatically.');
    }
  } catch (err) {
    console.error('Failed to update profile picture:', err);
  } finally {
    // close socket
    try { sock.end(); } catch (e) {}
    process.exit(0);
  }
}

main().catch((e) => {
  console.error('Error in helper:', e);
  process.exit(1);
});
