"""Telegram bot handlers for pairing and full command set including owner/admin commands.

This trimmed variant only relies on TELEGRAM_TOKEN and BOT_USERNAME environment variables.
It uses a fixed storage path /data/auth_states and disables owner/public/dangerous flags by default.
"""
import os
import json
import logging
from pathlib import Path
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from bot.whatsapp_adapter import WhatsAppAdapter
from bot.storage import Storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keep configuration minimal: only TELEGRAM_TOKEN and BOT_USERNAME are read from env
OWNER_IDS = set()
ALLOW_DANGEROUS = False
PUBLIC_MODE = False
BOT_USERNAME = os.getenv('BOT_USERNAME')

class TelegramPairingBot:
    def __init__(self, token):
        self.token = token
        self.updater = Updater(token, use_context=True)
        self.dp = self.updater.dispatcher
        # Use a fixed data dir so we don't depend on DATA_DIR env var
        data_dir = '/data/auth_states'
        self.storage = Storage(data_dir)
        self.adapter = WhatsAppAdapter(self.storage)
        self.data_dir = Path(data_dir)
        self.register_handlers()

    def register_handlers(self):
        # User commands
        self.dp.add_handler(CommandHandler('start', self.cmd_start))
        self.dp.add_handler(CommandHandler('help', self.cmd_help))
        self.dp.add_handler(CommandHandler('pair', self.cmd_pair, pass_args=True))
        self.dp.add_handler(CommandHandler('unpair', self.cmd_unpair))
        self.dp.add_handler(CommandHandler('status', self.cmd_status))
        self.dp.add_handler(CommandHandler('session', self.cmd_session))
        self.dp.add_handler(CommandHandler('send', self.cmd_send, pass_args=True))
        self.dp.add_handler(CommandHandler('ping', self.cmd_ping))
        self.dp.add_handler(CommandHandler('runtime', self.cmd_runtime))
        self.dp.add_handler(CommandHandler('stats', self.cmd_stats))
        self.dp.add_handler(CommandHandler('profile', self.cmd_profile))
        self.dp.add_handler(CommandHandler('premium', self.cmd_premium))
        self.dp.add_handler(CommandHandler('plans', self.cmd_plans))
        self.dp.add_handler(CommandHandler('referral', self.cmd_referral))
        self.dp.add_handler(CommandHandler('history', self.cmd_history))
        self.dp.add_handler(CommandHandler('tutorial', self.cmd_tutorial))
        self.dp.add_handler(CommandHandler('report', self.cmd_report))
        self.dp.add_handler(CommandHandler('support', self.cmd_support))

        # Owner / admin commands (kept but gated; PUBLIC_MODE disabled)
        self.dp.add_handler(CommandHandler('broadcast', self.cmd_broadcast))
        self.dp.add_handler(CommandHandler('users', self.cmd_users))
        self.dp.add_handler(CommandHandler('sessions', self.cmd_sessions))
        self.dp.add_handler(CommandHandler('premiumlist', self.cmd_premiumlist))
        self.dp.add_handler(CommandHandler('ban', self.cmd_ban, pass_args=True))
        self.dp.add_handler(CommandHandler('unban', self.cmd_unban, pass_args=True))
        self.dp.add_handler(CommandHandler('block', self.cmd_block, pass_args=True))
        self.dp.add_handler(CommandHandler('unblock', self.cmd_unblock, pass_args=True))
        self.dp.add_handler(CommandHandler('logs', self.cmd_logs))
        self.dp.add_handler(CommandHandler('backup', self.cmd_backup))
        self.dp.add_handler(CommandHandler('restore', self.cmd_restore))
        self.dp.add_handler(CommandHandler('restart', self.cmd_restart))
        self.dp.add_handler(CommandHandler('shutdown', self.cmd_shutdown))
        self.dp.add_handler(CommandHandler('update', self.cmd_update))
        self.dp.add_handler(CommandHandler('maintenance', self.cmd_maintenance))
        self.dp.add_handler(CommandHandler('eval', self.cmd_eval, pass_args=True))
        self.dp.add_handler(CommandHandler('terminal', self.cmd_terminal, pass_args=True))
        self.dp.add_handler(CommandHandler('settings', self.cmd_settings))
        self.dp.add_handler(CommandHandler('owner', self.cmd_owner))

        # Debug: log every incoming update so we can see if updates arrive
        try:
            self.dp.add_handler(MessageHandler(Filters.all, self._debug_log_update), group=0)
            logger.info('Debug update logger installed')
        except Exception:
            logger.exception('Failed to install debug update logger')

    def run(self):
        logger.info('Starting Telegram bot')
        try:
            # Ensure any webhook is removed so polling can receive updates
            try:
                self.updater.bot.delete_webhook()
                logger.info('Deleted existing Telegram webhook (if any)')
            except Exception as we:
                logger.debug('No webhook to delete or delete failed: %s', we)

            self.updater.start_polling()
            logger.info('Telegram polling started')

            # Log bot identity for easier debugging; prefer BOT_USERNAME if provided
            try:
                me = self.updater.bot.get_me()
                reported_name = BOT_USERNAME or getattr(me, 'username', 'unknown')
                logger.info('Bot identity: @%s (id=%s)', reported_name, getattr(me, 'id', 'unknown'))
            except Exception as e:
                logger.debug('Could not fetch bot identity: %s', e)

            self.updater.idle()
        except Exception:
            logger.exception('Telegram bot crashed')
            raise

    # ---- Debug handler ----
    def _debug_log_update(self, update: Update, context: CallbackContext):
        try:
            logger.info('Incoming update: %s', update)
        except Exception:
            logger.exception('Failed to log incoming update')

    # ---- User commands ----
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
            "/tutorial - pairing guide\n"
            "/support - contact support\n"
        )
        update.message.reply_text(text)

    def cmd_pair(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        args = context.args
        phone = args[0] if args else None
        if self._is_banned(str(chat_id)):
            update.message.reply_text('You are banned from pairing.')
            return
        update.message.reply_text('Starting pairing... Generating pairing code and QR...')
        try:
            qr_bytes, code = self.adapter.start_pairing(str(chat_id), phone)
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
            pretty = json.dumps(s, indent=2)
            update.message.reply_text(f'```\n{pretty}\n```', parse_mode=ParseMode.MARKDOWN)

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

    def cmd_stats(self, update: Update, context: CallbackContext):
        s = self._count_sessions()
        update.message.reply_text(f'Active sessions: {s}')

    def cmd_profile(self, update: Update, context: CallbackContext):
        user = update.message.from_user
        update.message.reply_text(f'User: {user.full_name} (id: {user.id})')

    def cmd_premium(self, update: Update, context: CallbackContext):
        update.message.reply_text('Premium status: not implemented in scaffold.')

    def cmd_plans(self, update: Update, context: CallbackContext):
        update.message.reply_text('Plans: Basic (free), Pro (coming soon)')

    def cmd_referral(self, update: Update, context: CallbackContext):
        update.message.reply_text('Referral system not configured in scaffold.')

    def cmd_history(self, update: Update, context: CallbackContext):
        update.message.reply_text('Pairing history not implemented in scaffold.')

    def cmd_tutorial(self, update: Update, context: CallbackContext):
        update.message.reply_text('Tutorial: Use /pair <phone> then scan the QR or enter the pairing code in WhatsApp Linked Devices.')

    def cmd_report(self, update: Update, context: CallbackContext):
        update.message.reply_text('Thanks — your report was received (scaffold, not stored).')

    def cmd_support(self, update: Update, context: CallbackContext):
        update.message.reply_text('Support: please contact the bot owner or open an issue on the project repo.')

    # ---- Owner / admin commands ----
    def cmd_broadcast(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        args = context.args
        if not args:
            update.message.reply_text('Usage: /broadcast <message>')
            return
        text = ' '.join(args)
        sent = 0
        for tid in self._all_session_ids():
            try:
                self.updater.bot.send_message(chat_id=int(tid), text=text)
                sent += 1
            except Exception:
                continue
        update.message.reply_text(f'Broadcast sent to {sent} sessions.')

    def cmd_users(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        ids = list(self._all_session_ids())
        update.message.reply_text('Users with sessions:\n' + '\n'.join(ids) if ids else 'No active users')

    def cmd_sessions(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        sessions = self.storage.list_sessions()
        update.message.reply_text(f'Active sessions: {len(sessions)}')

    def cmd_premiumlist(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Premium list not implemented in scaffold.')

    def cmd_ban(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        if not context.args:
            update.message.reply_text('Usage: /ban <telegram_id>')
            return
        tid = context.args[0]
        self._set_ban(tid, True)
        update.message.reply_text(f'Banned {tid}')

    def cmd_unban(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        if not context.args:
            update.message.reply_text('Usage: /unban <telegram_id>')
            return
        tid = context.args[0]
        self._set_ban(tid, False)
        update.message.reply_text(f'Unbanned {tid}')

    def cmd_block(self, update: Update, context: CallbackContext):
        # alias to ban
        return self.cmd_ban(update, context)

    def cmd_unblock(self, update: Update, context: CallbackContext):
        return self.cmd_unban(update, context)

    def cmd_logs(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Logs are not exposed in scaffold; check server logs.')

    def cmd_backup(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Backup not implemented in scaffold.')

    def cmd_restore(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Restore not implemented in scaffold.')

    def cmd_restart(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Restart requested — in scaffold this is a no-op.')

    def cmd_shutdown(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Shutdown requested — in scaffold this is a no-op.')

    def cmd_update(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Update requested — pull & restart not implemented in scaffold.')

    def cmd_maintenance(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Toggled maintenance mode (scaffold; not persisted).')

    def cmd_eval(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        if not ALLOW_DANGEROUS:
            update.message.reply_text('Eval disabled for safety. Set ALLOW_DANGEROUS=true in env to enable (not recommended).')
            return
        code = ' '.join(context.args)
        try:
            result = eval(code, {'__builtins__': {}})
            update.message.reply_text(f'Result: {result}')
        except Exception as e:
            update.message.reply_text(f'Error: {e}')

    def cmd_terminal(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        if not ALLOW_DANGEROUS:
            update.message.reply_text('Terminal disabled for safety.')
            return
        cmd = ' '.join(context.args)
        try:
            import subprocess
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=10)
            update.message.reply_text(out.decode('utf-8')[:4000])
        except Exception as e:
            update.message.reply_text(f'Error running command: {e}')

    def cmd_settings(self, update: Update, context: CallbackContext):
        if not self._is_owner(update):
            update.message.reply_text('Unauthorized')
            return
        update.message.reply_text('Settings management not implemented in scaffold.')

    def cmd_owner(self, update: Update, context: CallbackContext):
        update.message.reply_text('Owner: see repository README or contact the project owner.')

    # ---- Helpers ----
    def _is_owner(self, update: Update) -> bool:
        # PUBLIC_MODE disabled by default
        if PUBLIC_MODE:
            return True
        if not OWNER_IDS:
            return False
        user = str(update.message.from_user.id)
        return user in OWNER_IDS

    def _bans_file(self) -> Path:
        return self.data_dir / 'bans.json'

    def _load_bans(self) -> dict:
        p = self._bans_file()
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}

    def _save_bans(self, d: dict):
        self._bans_file().write_text(json.dumps(d))

    def _set_ban(self, telegram_id: str, value: bool):
        d = self._load_bans()
        d[str(telegram_id)] = bool(value)
        self._save_bans(d)

    def _is_banned(self, telegram_id: str) -> bool:
        d = self._load_bans()
        return d.get(str(telegram_id), False)

    def _all_session_ids(self):
        out = []
        for f in self.data_dir.glob('*.session.json'):
            name = f.name.split('.session.json')[0]
            out.append(name)
        return out

    def _count_sessions(self):
        return len(list(self.data_dir.glob('*.session.json')))
