import re
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from telegram import (
    Update, ChatPermissions, ChatMemberStatus, ChatPrivileges,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackContext, ChatMemberHandler
)

# ------------------- DATA STORAGE (in-memory, resets on each Vercel invocation) -------------------
# For production, replace with Redis (Upstash), Vercel KV, or a database.
warnings: Dict[Tuple[int, int], int] = {}
notes: Dict[int, Dict[str, str]] = {}
blacklist_words = ["spam", "badword"]
rules_text = "📜 Group Rules:\n1. Be respectful\n2. No spam\n3. Follow admin instructions"
welcome_message = "👋 Welcome {mention} to {title}!"

# ------------------- HELPER FUNCTIONS -------------------

async def is_admin(update: Update, user_id: int) -> bool:
    """Check if user is admin or owner in the chat."""
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except:
        return False

async def resolve_user(update: Update, args: list) -> Optional[int]:
    """Extract user_id from reply, command argument, or username."""
    message = update.effective_message
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    if args:
        user_ref = args[0]
        try:
            if user_ref.isdigit():
                return int(user_ref)
            if user_ref.startswith("@"):
                user = await update.effective_chat.get_member(user_ref[1:])
                return user.user.id
        except:
            pass
    return None

def user_mention(user) -> str:
    """Return mention string for a user."""
    if user.username:
        return f"@{user.username}"
    else:
        return user.first_name or "User"

async def check_admin_and_reply(update: Update) -> bool:
    """Reply if user is not admin."""
    user = update.effective_user
    if not user or not await is_admin(update, user.id):
        await update.message.reply_text("⛔️ You need admin permissions!")
        return False
    return True

# ------------------- BASIC COMMANDS -------------------

async def start(update: Update, context: CallbackContext):
    if update.effective_chat.type == "private":
        await update.message.reply_text("👋 Hello! I'm an advanced group management bot. Add me to a group and make me admin!")

async def help_command(update: Update, context: CallbackContext):
    help_text = """
🛠 Advanced Group Management Bot

👮 Admin Tools:
/ban [user] - Ban a user
/unban [user] - Unban a user
/kick [user] - Kick a user
/mute [user] [minutes] - Mute a user
/unmute [user] - Unmute a user
/warn [user] - Warn a user
/unwarn [user] - Remove warning
/warns [user] - Check warnings
/purge [reply] - Bulk delete messages
/pin [reply] - Pin a message
/unpin - Unpin current message
/settitle [text] - Change group title
/setphoto [reply] - Set group photo
/setdescription [text] - Set group description
/promote [user] - Promote to admin
/demote [user] - Demote admin

📝 Group Features:
/setrules [text] - Set group rules
/rules - Show rules
/setwelcome [text] - Set welcome message
/welcome - Show welcome
/report [reply] - Report to admins
/staff - Show admins

💾 Utilities:
/setnote [name] [text] - Save note
/getnote [name] - Get note
/id - Get user/chat ID
/info [user] - Get user info

🎉 Fun:
/slap [reply] - Slap a user
/roll - Roll a dice
/coin - Flip a coin
/say [text] - Make bot say something
"""
    await update.message.reply_text(help_text)

async def ping(update: Update, context: CallbackContext):
    start = datetime.now()
    msg = await update.message.reply_text("🏓 Pinging...")
    delta = (datetime.now() - start).total_seconds() * 1000
    await msg.edit_text(f"🏓 Pong! {delta:.2f}ms")

# ------------------- MODERATION COMMANDS -------------------

async def ban(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await update.effective_chat.ban_member(user_id)
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"🔨 Banned {user_mention(user)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ban failed: {str(e)}")

async def unban(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await update.effective_chat.unban_member(user_id)
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"✅ Unbanned {user_mention(user)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Unban failed: {str(e)}")

async def kick(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await update.effective_chat.ban_member(user_id, until_date=datetime.now() + timedelta(seconds=30))
        await update.effective_chat.unban_member(user_id)
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"👢 Kicked {user_mention(user)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Kick failed: {str(e)}")

async def mute(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    duration = 60
    if len(context.args) > 1 and context.args[1].isdigit():
        duration = int(context.args[1])
    try:
        await update.effective_chat.restrict_member(
            user_id,
            ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(minutes=duration)
        )
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"🔇 Muted {user_mention(user)} for {duration} minutes")
    except Exception as e:
        await update.message.reply_text(f"❌ Mute failed: {str(e)}")

async def unmute(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        perms = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await update.effective_chat.restrict_member(user_id, perms)
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"🔊 Unmuted {user_mention(user)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Unmute failed: {str(e)}")

async def warn(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    chat_id = update.effective_chat.id
    key = (chat_id, user_id)
    warnings[key] = warnings.get(key, 0) + 1
    count = warnings[key]
    if count >= 3:
        try:
            await update.effective_chat.restrict_member(
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(hours=24)
            )
            warnings[key] = 0
            user = await context.bot.get_chat(user_id)
            await update.message.reply_text(f"🔇 Muted {user_mention(user)} for 24 hours due to 3 warnings.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Warning added but mute failed: {str(e)}")
    else:
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"⚠️ Warned {user_mention(user)} (Warnings: {count}/3)")

async def unwarn(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    chat_id = update.effective_chat.id
    key = (chat_id, user_id)
    if warnings.get(key, 0) > 0:
        warnings[key] -= 1
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"✅ Removed warning from {user_mention(user)} (Now: {warnings[key]}/3)")
    else:
        await update.message.reply_text(f"ℹ️ User has no warnings.")

async def warns(update: Update, context: CallbackContext):
    user_id = await resolve_user(update, context.args) or update.effective_user.id
    chat_id = update.effective_chat.id
    count = warnings.get((chat_id, user_id), 0)
    user = await context.bot.get_chat(user_id)
    await update.message.reply_text(f"⚠️ {user_mention(user)} has {count}/3 warnings.")

async def purge(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    message = update.effective_message
    if not message.reply_to_message:
        await message.reply_text("⚠️ Reply to the first message to purge from.")
        return
    try:
        start_id = message.reply_to_message.id
        end_id = message.id
        msg_ids = []
        async for msg in message.chat.iterate_messages(limit=100, reverse=True):
            if msg.id < start_id:
                break
            if start_id <= msg.id <= end_id:
                msg_ids.append(msg.id)
        if not msg_ids:
            await message.reply_text("❌ No messages found to delete.")
            return
        for i in range(0, len(msg_ids), 100):
            await message.chat.delete_messages(msg_ids[i:i+100])
        notify = await message.reply_text(f"🧹 Deleted {len(msg_ids)} messages.")
        await asyncio.sleep(5)
        await notify.delete()
    except Exception as e:
        await message.reply_text(f"❌ Purge failed: {str(e)}")

async def pin(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    if not update.effective_message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to pin.")
        return
    try:
        await update.effective_message.reply_to_message.pin(disable_notification=True)
        await update.message.reply_text("📌 Message pinned.")
    except Exception as e:
        await update.message.reply_text(f"❌ Pin failed: {str(e)}")

async def unpin(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    try:
        await update.effective_chat.unpin_all_messages()
        await update.message.reply_text("📌 Message unpinned.")
    except Exception as e:
        await update.message.reply_text(f"❌ Unpin failed: {str(e)}")

async def set_title(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /settitle <new title>")
        return
    title = " ".join(context.args)
    try:
        await update.effective_chat.set_title(title)
        await update.message.reply_text(f"✅ Title updated to: {title}")
    except Exception as e:
        await update.message.reply_text(f"❌ Title change failed: {str(e)}")

async def set_photo(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    reply = update.effective_message.reply_to_message
    if not reply or not reply.photo:
        await update.message.reply_text("⚠️ Reply to a photo to set as group photo.")
        return
    try:
        photo_file = await reply.photo[-1].get_file()
        await update.effective_chat.set_photo(photo_file)
        await update.message.reply_text("✅ Group photo updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to set photo: {str(e)}")

async def set_description(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /setdescription <text>")
        return
    desc = " ".join(context.args)
    try:
        await update.effective_chat.set_description(desc)
        await update.message.reply_text("✅ Group description updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to set description: {str(e)}")

async def promote(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await update.effective_chat.promote_member(
            user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_change_info=True,
            can_post_messages=True,
            can_edit_messages=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_topics=True
        )
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"👑 Promoted {user_mention(user)} to admin!")
    except Exception as e:
        await update.message.reply_text(f"❌ Promote failed: {str(e)}")

async def demote(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    user_id = await resolve_user(update, context.args)
    if not user_id:
        await update.message.reply_text("⚠️ Reply to a user, or provide a valid username/ID.")
        return
    try:
        await update.effective_chat.promote_member(
            user_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False
        )
        user = await context.bot.get_chat(user_id)
        await update.message.reply_text(f"👑 Demoted {user_mention(user)} from admin!")
    except Exception as e:
        await update.message.reply_text(f"❌ Demote failed: {str(e)}")

# ------------------- GROUP FEATURES -------------------

async def set_rules(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /setrules <text>")
        return
    global rules_text
    rules_text = " ".join(context.args)
    await update.message.reply_text("✅ Rules updated!")

async def show_rules(update: Update, context: CallbackContext):
    await update.message.reply_text(rules_text)

async def set_welcome(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /setwelcome <message>\nUse {mention} and {title} as placeholders.")
        return
    global welcome_message
    welcome_message = " ".join(context.args)
    await update.message.reply_text("✅ Welcome message updated!")

async def show_welcome(update: Update, context: CallbackContext):
    await update.message.reply_text(welcome_message.replace("{mention}", "USER").replace("{title}", update.effective_chat.title))

async def welcome_new_member(update: Update, context: CallbackContext):
    for user in update.message.new_chat_members:
        welcome_text = welcome_message.replace("{mention}", user.mention_html()).replace("{title}", update.effective_chat.title)
        await update.message.reply_text(welcome_text, parse_mode="HTML")

async def report(update: Update, context: CallbackContext):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to report.")
        return
    admins = []
    async for member in update.effective_chat.get_members(filter=ChatMemberStatus.ADMINISTRATOR):
        if not member.user.is_bot:
            admins.append(member.user.mention_html())
    if admins:
        report_msg = (
            f"🚨 Report\n"
            f"👤 Reporter: {update.effective_user.mention_html()}\n"
            f"⚠️ Reported message: {update.message.reply_to_message.link}\n"
            f"🛡 Admins notified:\n" + "\n".join(admins)
        )
        await update.message.reply_text(report_msg, parse_mode="HTML")
    else:
        await update.message.reply_text("ℹ️ No admins available to notify.")

async def staff(update: Update, context: CallbackContext):
    admins = []
    async for member in update.effective_chat.get_members(filter=ChatMemberStatus.ADMINISTRATOR):
        if not member.user.is_bot:
            admins.append(member.user.mention_html())
    if admins:
        await update.message.reply_text("👮 Group Admins:\n" + "\n".join(admins), parse_mode="HTML")
    else:
        await update.message.reply_text("ℹ️ No admins found.")

# ------------------- UTILITIES -------------------

async def set_note(update: Update, context: CallbackContext):
    if not await check_admin_and_reply(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: /setnote <name> <text>")
        return
    name = context.args[0]
    text = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    notes.setdefault(chat_id, {})[name] = text
    await update.message.reply_text(f"📝 Note {name} saved!")

async def get_note(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /getnote <name>")
        return
    name = context.args[0]
    chat_id = update.effective_chat.id
    if notes.get(chat_id, {}).get(name):
        await update.message.reply_text(notes[chat_id][name])
    else:
        await update.message.reply_text(f"⚠️ Note {name} not found.")

async def user_id(update: Update, context: CallbackContext):
    if update.effective_chat.type == "private":
        await update.message.reply_text(f"🆔 Your ID: {update.effective_user.id}")
    elif update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        await update.message.reply_text(f"👤 {user_mention(user)}'s ID: {user.id}")
    else:
        await update.message.reply_text(f"👤 Your ID: {update.effective_user.id}\n💬 Chat ID: {update.effective_chat.id}")

async def user_info(update: Update, context: CallbackContext):
    user_id = await resolve_user(update, context.args) or update.effective_user.id
    try:
        member = await update.effective_chat.get_member(user_id)
        joined = member.joined_date.strftime('%Y-%m-%d') if member.joined_date else "N/A"
        info_text = (
            f"👤 User Information\n"
            f"🆔 ID: {member.user.id}\n"
            f"👤 Name: {member.user.first_name}\n"
            f"📛 Username: @{member.user.username if member.user.username else 'N/A'}\n"
            f"👥 In Group: {'Yes' if member.status != ChatMemberStatus.BANNED else 'No'}\n"
            f"🛡 Status: {member.status.name}\n"
            f"📅 Joined: {joined}"
        )
        await update.message.reply_text(info_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ------------------- FUN COMMANDS -------------------

async def slap(update: Update, context: CallbackContext):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await update.message.reply_text(f"👋 {update.effective_user.mention_html()} slapped {target.mention_html()} with a large trout! 🐟", parse_mode="HTML")
    else:
        await update.message.reply_text("⚠️ Reply to a user to slap.")

async def roll(update: Update, context: CallbackContext):
    await update.message.reply_text(f"🎲 You rolled a {random.randint(1, 6)}!")

async def coin(update: Update, context: CallbackContext):
    side = "Heads" if random.randint(0, 1) == 0 else "Tails"
    await update.message.reply_text(f"🪙 Coin flip: {side}")

async def say(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /say <text>")
        return
    text = " ".join(context.args)
    await update.message.reply_text(text)

# ------------------- SETUP WEBHOOK (used by Vercel) -------------------

def create_application() -> Application:
    """Build and return the PTB Application with all handlers."""
    app = Application.builder().token("7468327119:AAFzswUn3TAcDhI_OE62YP9AeEAl5JLm05w").build()

    # Basic
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping))

    # Moderation
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("unwarn", unwarn))
    app.add_handler(CommandHandler("warns", warns))
    app.add_handler(CommandHandler("purge", purge))
    app.add_handler(CommandHandler("pin", pin))
    app.add_handler(CommandHandler("unpin", unpin))
    app.add_handler(CommandHandler("settitle", set_title))
    app.add_handler(CommandHandler("setphoto", set_photo))
    app.add_handler(CommandHandler("setdescription", set_description))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))

    # Group features
    app.add_handler(CommandHandler("setrules", set_rules))
    app.add_handler(CommandHandler("rules", show_rules))
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("welcome", show_welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("staff", staff))

    # Utilities
    app.add_handler(CommandHandler("setnote", set_note))
    app.add_handler(CommandHandler("getnote", get_note))
    app.add_handler(CommandHandler("id", user_id))
    app.add_handler(CommandHandler("info", user_info))

    # Fun
    app.add_handler(CommandHandler("slap", slap))
    app.add_handler(CommandHandler("roll", roll))
    app.add_handler(CommandHandler("coin", coin))
    app.add_handler(CommandHandler("say", say))

    return app 