import os
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

import json
from telegram import Update, BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# ========== A. CONFIG ==========
TOKEN = "8666612292:AAHObKPjfMVEQPeqRqTTKBYx3xPEBLS8PHQ"
ADMIN_ID = 7440168853

USERS_FILE = "users.json"
BANNED_FILE = "banned.json"
STATS_FILE = "stats.json"
BLOCKED_FILE = "blocked.json"
MESSAGES_FILE = "messages.json"
BROADCAST_FILE = "broadcast.json"

# ========== B. DATABASE ==========
def load_json(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

all_users = set(load_json(USERS_FILE).get("users", []))
banned_users = set(load_json(BANNED_FILE).get("banned", []))
blocked_users = set(load_json(BLOCKED_FILE).get("blocked", []))
stats = load_json(STATS_FILE)
messages_map = load_json(MESSAGES_FILE)
broadcast_map = load_json(BROADCAST_FILE) # admin_msg_id: {user_id: user_msg_id}

print(f"[START] Users: {len(all_users)} | Banned: {len(banned_users)}")

# ========== C. COMMANDS ==========
async def setup_commands(application: Application):
    user_commands = [BotCommand("start", "Start bot")]
    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = [
        BotCommand("start", "Start bot"),
        BotCommand("panel", "Admin Panel"),
        BotCommand("stats", "Full Statistics"),
        BotCommand("users", "All Users List"),
        BotCommand("banned", "Banned Users"),
        BotCommand("blocked", "Blocked Bot Users"),
        BotCommand("ban", "Ban user - /ban 12345"),
        BotCommand("unban", "Unban user - /unban 12345"),
        BotCommand("broadcast", "Send to all - /broadcast msg")
    ]
    await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))

# ========== D. START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if user.id == ADMIN_ID:
        await panel_command(update, context)
        return

    if user.id in banned_users:
        await update.message.reply_text("🚫 You are banned from this bot")
        return

    is_new = user.id not in all_users
    all_users.add(user.id)
    save_json(USERS_FILE, {"users": list(all_users)})
    stats[str(user.id)] = {
        "joined": datetime.now().strftime("%Y-%m-%d"),
        "name": user.full_name,
        "username": user.username or "None",
        "active": True
    }
    save_json(STATS_FILE, stats)

    if is_new:
        username = f"@{user.username}" if user.username else "No username"
        profile_link = f"<a href='tg://user?id={user.id}'>View Profile</a>"
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆕 <b>New User Joined!</b>\n\n"
                 f"👤 Name: {user.full_name}\n"
                 f"Username: {username}\n"
                 f"Chat ID: <code>{user.id}</code>\n"
                 f"{profile_link}\n\n"
                 f"📊 Total Users: {len(all_users)}",
            parse_mode='HTML'
        )

    await update.message.reply_text(
        "👋 Welcome to JA CAPTCHA BOT\n\n"
        "📝 Describe your problem in detail\n"
        "⏰ You will get a reply within 24 hours\n\n"
        "⚡️ For faster assistance, please explain clearly\n\n"
        "❓ Do you need any help?",
        parse_mode='HTML'
    )

# ========== E. PANEL - NO BUTTON ==========
async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id!= ADMIN_ID:
        return

    total = len(all_users)
    banned = len(banned_users)
    blocked = len(blocked_users)
    active = sum(1 for s in stats.values() if s.get("active", True))

    await update.message.reply_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Total Users: {total}\n"
        f"✅ Active: {active}\n"
        f"🚫 Banned by Admin: {banned}\n"
        f"🚷 Blocked Bot: {blocked}\n\n"
        f"<b>Commands - Click to Copy:</b>\n"
        f"<code>/stats</code> - Full Statistics\n"
        f"<code>/users</code> - All Users List\n"
        f"<code>/banned</code> - Banned Users\n"
        f"<code>/blocked</code> - Blocked Bot Users\n"
        f"<code>/ban 12345</code> - Ban user\n"
        f"<code>/unban 12345</code> - Unban user\n"
        f"<code>/broadcast msg</code> - Send to all\n\n"
        f"💡 Reply to user message to send reply\n"
        f"💡 Edit your message to <code>/del</code> to delete from user\n"
        f"💡 Broadcast photo/video/doc + <code>/del</code> = delete from all users",
        parse_mode='HTML'
    )

# ========== F. STATS ==========
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id!= ADMIN_ID:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(1 for d in stats.values() if d.get("joined") == today)

    await update.message.reply_text(
        f"📊 <b>Full Statistics</b>\n\n"
        f"👥 Total Users: {len(all_users)}\n"
        f"✅ Active: {sum(1 for s in stats.values() if s.get('active', True))}\n"
        f"🚫 Banned by Admin: {len(banned_users)}\n"
        f"🚷 Blocked Bot: {len(blocked_users)}\n"
        f"📅 Today Joined: {today_count}",
        parse_mode='HTML'
    )

# ========== G. USERS ==========
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id!= ADMIN_ID:
        return

    text = f"👥 <b>Users: {len(all_users)}</b>\n\n"
    for idx, uid in enumerate(list(all_users)[:30], 1):
        name = stats.get(str(uid), {}).get("name", "Unknown")
        username = stats.get(str(uid), {}).get("username", "None")
        status = "🚫" if uid in banned_users else "👤"
        if uid in blocked_users: status += "🚷"
        text += f"{idx}. {name} {status}\n@{username}\n<code>{uid}</code>\n\n"

    await update.message.reply_text(text, parse_mode='HTML')

# ========== H. BANNED ==========
async def banned_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id!= ADMIN_ID:
        return

    text = f"🚫 <b>Banned: {len(banned_users)}</b>\n\n"
    for idx, uid in enumerate(list(banned_users)[:30], 1):
        name = stats.get(str(uid), {}).get("name", "Unknown")
        text += f"{idx}. {name}\n<code>{uid}</code>\n\n"
    if not banned_users:
        text += "No banned users"

    await update.message.reply_text(text, parse_mode='HTML')

# ========== I. BLOCKED ==========
async def blocked_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id!= ADMIN_ID:
        return

    text = f"🚷 <b>Blocked Bot: {len(blocked_users)}</b>\n\n"
    for idx, uid in enumerate(list(blocked_users)[:30], 1):
        name = stats.get(str(uid), {}).get("name", "Unknown")
        text += f"{idx}. {name}\n<code>{uid}</code>\n\n"
    if not blocked_users:
        text += "No blocked users"

    await update.message.reply_text(text, parse_mode='HTML')

# ========== J. BAN/UNBAN ==========
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id!= ADMIN_ID:
        return
    user_id = None
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    elif context.args and context.args[0].isdigit():
        user_id = int(context.args[0])

    if user_id:
        banned_users.add(user_id)
        save_json(BANNED_FILE, {"banned": list(banned_users)})
        await update.message.reply_text(f"🚫 User <code>{user_id}</code> banned", parse_mode='HTML')
        try:
            await context.bot.send_message(chat_id=user_id, text="🚫 You have been banned by admin")
        except:
            pass

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id!= ADMIN_ID:
        return
    user_id = None
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    elif context.args and context.args[0].isdigit():
        user_id = int(context.args[0])

    if user_id and user_id in banned_users:
        banned_users.remove(user_id)
        save_json(BANNED_FILE, {"banned": list(banned_users)})
        await update.message.reply_text(f"✅ User <code>{user_id}</code> unbanned", parse_mode='HTML')
        try:
            await context.bot.send_message(chat_id=user_id, text="✅ You have been unbanned by admin")
        except:
            pass

# ========== K. BROADCAST ==========
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id!= ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Usage: <code>/broadcast Your message</code>", parse_mode='HTML')
        return

    msg = " ".join(context.args)
    success = 0
    failed = 0

    for uid in all_users:
        if uid in banned_users or uid in blocked_users:
            continue
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 <b>Announcement</b>\n\n{msg}", parse_mode='HTML')
            success += 1
        except:
            failed += 1
            blocked_users.add(uid)

    save_json(BLOCKED_FILE, {"blocked": list(blocked_users)})
    await update.message.reply_text(f"✅ Broadcast Done\n\nSuccess: {success}\nFailed: {failed}")

# ========== L. MESSAGE HANDLER - BROADCAST DELETE TRACKING ==========
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global messages_map, broadcast_map
    user = update.message.from_user

    # Admin Reply/Broadcast
    if user.id == ADMIN_ID:
        # Reply to User
        if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            admin_msg_id = str(update.message.reply_to_message.message_id)
            if admin_msg_id in messages_map:
                target_user_id = messages_map[admin_msg_id]["user_id"]
                try:
                    if update.message.text:
                        sent = await context.bot.send_message(chat_id=target_user_id, text=update.message.text)
                    elif update.message.photo:
                        sent = await context.bot.send_photo(chat_id=target_user_id, photo=update.message.photo[-1].file_id, caption=update.message.caption)
                    elif update.message.video:
                        sent = await context.bot.send_video(chat_id=target_user_id, video=update.message.video.file_id, caption=update.message.caption)
                    elif update.message.document:
                        sent = await context.bot.send_document(chat_id=target_user_id, document=update.message.document.file_id, caption=update.message.caption)
                    elif update.message.voice:
                        sent = await context.bot.send_voice(chat_id=target_user_id, voice=update.message.voice.file_id, caption=update.message.caption)
                    else:
                        sent = await context.bot.send_message(chat_id=target_user_id, text="Message")

                    messages_map[str(update.message.message_id)] = {"user_id": target_user_id, "user_msg_id": sent.message_id}
                    save_json(MESSAGES_FILE, messages_map)

                    await update.message.reply_text(f"✅ Sent to user <code>{target_user_id}</code>", parse_mode='HTML')
                except Exception as e:
                    await update.message.reply_text(f"❌ Failed: {str(e)}")
                return

        # Broadcast - TRACK ALL MESSAGE IDS FOR DELETE
        if not update.message.reply_to_message:
            broadcast_data = {}
            success = 0
            for uid in all_users:
                if uid in banned_users or uid in blocked_users:
                    continue
                try:
                    if update.message.text:
                        sent = await context.bot.send_message(chat_id=uid, text=f"📢 <b>Announcement</b>\n\n{update.message.text}", parse_mode='HTML')
                    elif update.message.photo:
                        sent = await context.bot.send_photo(chat_id=uid, photo=update.message.photo[-1].file_id, caption=update.message.caption)
                    elif update.message.video:
                        sent = await context.bot.send_video(chat_id=uid, video=update.message.video.file_id, caption=update.message.caption)
                    elif update.message.document:
                        sent = await context.bot.send_document(chat_id=uid, document=update.message.document.file_id, caption=update.message.caption)
                    broadcast_data[str(uid)] = sent.message_id
                    success += 1
                except:
                    blocked_users.add(uid)
            save_json(BLOCKED_FILE, {"blocked": list(blocked_users)})

            # Save broadcast mapping for delete
            broadcast_map[str(update.message.message_id)] = broadcast_data
            save_json(BROADCAST_FILE, broadcast_map)

            await update.message.reply_text(f"✅ Broadcast sent to {success} users")
            return

    if user.id in banned_users:
        return

    # User message to admin
    username = f"@{user.username}" if user.username else "No username"
    user_info = f"👤 From: {user.full_name}\nUsername: {username}\nID: <code>{user.id}</code>\n\n"

    try:
        sent_msg = None
        if update.message.text:
            sent_msg = await context.bot.send_message(chat_id=ADMIN_ID, text=user_info + f"💬 {update.message.text}", parse_mode='HTML')
        elif update.message.photo:
            sent_msg = await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=user_info + f"📷 Photo\n{update.message.caption or ''}", parse_mode='HTML')
        elif update.message.video:
            sent_msg = await context.bot.send_video(chat_id=ADMIN_ID, video=update.message.video.file_id, caption=user_info + f"🎥 Video\n{update.message.caption or ''}", parse_mode='HTML')
        elif update.message.document:
            sent_msg = await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=user_info + f"📄 {update.message.document.file_name}\n{update.message.caption or ''}", parse_mode='HTML')
        elif update.message.voice:
            sent_msg = await context.bot.send_voice(chat_id=ADMIN_ID, voice=update.message.voice.file_id, caption=user_info + f"🎤 Voice", parse_mode='HTML')
        else:
            sent_msg = await context.bot.send_message(chat_id=ADMIN_ID, text=user_info + f"💬 Message", parse_mode='HTML')

        if sent_msg:
            messages_map[str(sent_msg.message_id)] = {"user_id": user.id, "user_msg_id": update.message.message_id}
            save_json(MESSAGES_FILE, messages_map)

        await update.message.reply_text("✅ Sent to admin")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ========== M. EDIT HANDLER - /del DELETE FROM ALL ==========
async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.edited_message.from_user

    # User edit করলে admin এ নোটিফিকেশন
    if user.id!= ADMIN_ID:
        username = f"@{user.username}" if user.username else "No username"
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✏️ <b>User Edited Message</b>\n\n"
                 f"👤 From: {user.full_name}\n"
                 f"Username: {username}\n"
                 f"ID: <code>{user.id}</code>\n\n"
                 f"💬 New Message: {update.edited_message.text or '[Media/File]'}",
            parse_mode='HTML'
        )

    # Admin edit করে /del দিলে user এর কাছ থেকে delete হবে
    if user.id == ADMIN_ID:
        if update.edited_message.text and update.edited_message.text.strip() == "/del":
            admin_msg_id = str(update.edited_message.message_id)

            # Single user message delete
            if admin_msg_id in messages_map:
                data = messages_map[admin_msg_id]
                try:
                    await context.bot.delete_message(chat_id=data["user_id"], message_id=data["user_msg_id"])
                    await context.bot.delete_message(chat_id=ADMIN_ID, message_id=update.edited_message.message_id)
                    await context.bot.send_message(chat_id=ADMIN_ID, text="✅ Deleted from user's chat")
                except Exception as e:
                    await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ Could not delete: {str(e)}")
                return

            # Broadcast message delete from all users
            if admin_msg_id in broadcast_map:
                deleted = 0
                failed = 0
                for user_id, msg_id in broadcast_map[admin_msg_id].items():
                    try:
                        await context.bot.delete_message(chat_id=int(user_id), message_id=msg_id)
                        deleted += 1
                    except:
                        failed += 1

                try:
                    await context.bot.delete_message(chat_id=ADMIN_ID, message_id=update.edited_message.message_id)
                except:
                    pass

                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"✅ Deleted from all users\n\nDeleted: {deleted}\nFailed: {failed}"
                )
                return

        # Normal edit করলে user এর কাছে update হবে
        admin_msg_id = str(update.edited_message.message_id)
        if admin_msg_id in messages_map:
            data = messages_map[admin_msg_id]
            try:
                await context.bot.edit_message_text(
                    chat_id=data["user_id"],
                    message_id=data["user_msg_id"],
                    text=update.edited_message.text
                )
            except:
                pass

# ========== N. RUN ==========
app = Application.builder().token(TOKEN).build()
app.post_init = setup_commands

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("panel", panel_command))
app.add_handler(CommandHandler("stats", stats_command))
app.add_handler(CommandHandler("users", users_command))
app.add_handler(CommandHandler("banned", banned_command))
app.add_handler(CommandHandler("blocked", blocked_command))
app.add_handler(CommandHandler("ban", ban_command))
app.add_handler(CommandHandler("unban", unban_command))
app.add_handler(CommandHandler("broadcast", broadcast_command))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))

print("KolotiBablo Live Chat Official Bot Running...")
print(f"[START] Users: {len(all_users)} | Banned: {len(banned_users)} | Blocked: {len(blocked_users)}")
app.run_polling()
