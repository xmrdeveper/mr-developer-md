"""Telegram bot handlers for pairing and basic commands."""
import os
import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from bot.whatsapp_adapter import WhatsAppAdapter
from bot.storage import Storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OWNER_IDS = set()
if os.getenv('OWNER_IDS'):
    OWNER_IDS = set(x.strip() for x in os.getenv('OWNER_IDS').split(','))

class TelegramPairingBot:
    def __init__(self, token):
        self.token = token
        self.updater = Updater(token, use_context=True)
        self.dp = self.updater.dispatcher
        data_dir = os.getenv('DATA_DIR', './auth_states')
        self.storage = Storage(data_dir)
        self.adapter = WhatsAppAdapter(self.storage)
        self.register_handlers()

    def register_handlers(self):
        self.dp.add_handler(CommandHandler('start', self.cmd_start))
        self.dp.add_handler(CommandHandler('help', self.cmd_help))
        self.dp.add_handler(CommandHandler('pair', self.cmd_pair, pass_args=True))
        self.dp.add_handler(CommandHandler('unpair', self.cmd_unpair))
        self.dp.add_handler(CommandHandler('status', self.cmd_status))
        self.dp.add_handler(CommandHandler('session', self.cmd_session))
        self.dp.add_handler(CommandHandler('send', self.cmd_send, pass_args=True))
        self.dp.add_handler(CommandHandler('ping', self.cmd_ping))
        self.dp.add_handler(CommandHandler('runtime', self.cmd_runtime))
        # owner/admin commands (simple checks)
        self.dp.add_handler(CommandHandler('broadcast', self.cmd_broadcast))

    def run(self):
        logger.info('Starting Telegram bot')
        self.updater.start_polling()
        self.updater.idle()

    def cmd_start(self, update: Update, context: CallbackContext):
        text = (
            "❐ ◆「ACCESS GRANTED ✅」◆\n\n"
            "┊◆ 🎉 Welcome to mr-developer-md pairing bot\n\n"
            "Use /pair <phone> to start pairing your WhatsApp account.\n"
            "Example: /pair 2348012345678\n"
        )
        update.message.reply_text(text)

    def cmd_help(self, update: Update, context: CallbackContext):
        text = (
            "Available commands:\n"
            "/pair <phone> - start pairing and receive QR\n"
            "/unpair - remove stored session\n"
            "/status - current connection status\n"
            "/session - show session info\n"
            "/send <phone> <message> - send WhatsApp message\n"
            "/ping - bot latency\n"
        )
        update.message.reply_text(text)

    def cmd_pair(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        args = context.args
        phone = args[0] if args else None
        update.message.reply_text('Starting pairing... Generating pairing code and QR...')
        try:
            qr_bytes, code = self.adapter.start_pairing(str(chat_id), phone)
            # send QR as photo
            update.message.reply_photo(qr_bytes, caption=f'Pairing code: {code}\nScan in WhatsApp > Linked Devices > Link a Device')
            update.message.reply_text('Scan the QR or use the pairing code shown above. It will expire in a short time.')
        except Exception as e:
            logger.exception('Pairing failed')
            update.message.reply_text('Failed to start pairing: ' + str(e))

    def cmd_unpair(self, update: Update, context: CallbackContext):
        chat_id = str(update.message.chat_id)
        ok = self.storage.delete_session(chat_id)
        update.message.reply_text('Unpaired.' if ok else 'No active session to unpair.')

    def cmd_status(self, update: Update, context: CallbackContext):
        chat_id = str(update.message.chat_id)
        s = self.storage.load_session(chat_id)
        if not s:
            update.message.reply_text('No active WhatsApp session.')
        else:
            update.message.reply_text(f"Session active: label={s.get('label')} paired_at={s.get('paired_at')}")

    def cmd_session(self, update: Update, context: CallbackContext):
        chat_id = str(update.message.chat_id)
        s = self.storage.load_session(chat_id)
        if not s:
            update.message.reply_text('No session info available.')
        else:
            update.message.reply_text('Session details:\n' + '\n'.join(f'{k}: {v}' for k, v in s.items()))

    def cmd_send(self, update: Update, context: CallbackContext):
        chat_id = str(update.message.chat_id)
        args = context.args
        if len(args) < 2:
            update.message.reply_text('Usage: /send <phone> <message>')
            return
        to = args[0]
        text = ' '.join(args[1:])
        try:
            self.adapter.send_message(chat_id, to, text)
            update.message.reply_text('Message sent.')
        except Exception as e:
            logger.exception('send failed')
            update.message.reply_text('Failed to send message: ' + str(e))

    def cmd_ping(self, update: Update, context: CallbackContext):
        update.message.reply_text('PONG')

    def cmd_runtime(self, update: Update, context: CallbackContext):
        update.message.reply_text('Runtime information not implemented in scaffold.')

    def cmd_broadcast(self, update: Update, context: CallbackContext):
        user = str(update.message.from_user.id)
        if OWNER_IDS and user not in OWNER_IDS:
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Broadcast not implemented in scaffold.')
