import asyncio
import html
import os
import re
import shutil
import sqlite3
import tempfile
import time
import subprocess
from pathlib import Path

import yt_dlp
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = shutil.which("ffmpeg")
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN", "8771909249:AAGBriW24rysElxGKxjxbHBMzWx5CTg7dwM").strip()
BOT_NAME = "VIDEO DOWNLOADER BOT"
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "8546199829").split(",") if x.strip().isdigit()}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "49"))
DOWNLOAD_ROOT = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
DB_PATH = os.getenv("DATABASE_PATH", "bot.db")
MAX_CONCURRENT_FRAGMENTS = max(1, min(int(os.getenv("CONCURRENT_FRAGMENTS", "8")), 32))
URL_RE = re.compile(r"^https?://\S+$", re.I)


def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, first_seen INTEGER, downloads INTEGER DEFAULT 0)")
    con.commit()
    return con


def save_user(user):
    if not user:
        return
    with db() as con:
        con.execute("INSERT OR IGNORE INTO users(user_id,name,username,first_seen) VALUES(?,?,?,?)", (user.id, user.full_name[:200], user.username or "", int(time.time())))
        con.execute("UPDATE users SET name=?, username=? WHERE user_id=?", (user.full_name[:200], user.username or "", user.id))


def inc_download(user_id):
    with db() as con:
        con.execute("UPDATE users SET downloads=downloads+1 WHERE user_id=?", (user_id,))


def stats():
    with db() as con:
        users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        downloads = con.execute("SELECT COALESCE(SUM(downloads),0) FROM users").fetchone()[0]
    return users, downloads


def safe_name(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|\n\r]+", "_", name).strip()[:180] or "download"


def main_menu(is_admin=False):
    rows = [
        [InlineKeyboardButton("🔗 New Download", callback_data="menu:new"), InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings")],
        [InlineKeyboardButton("📥 My Downloads", callback_data="menu:history"), InlineKeyboardButton("❓ Help", callback_data="menu:help")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


def quality_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 BEST", callback_data="q:best"), InlineKeyboardButton("⚡ 1080P", callback_data="q:1080")],
        [InlineKeyboardButton("🎬 720P", callback_data="q:720"), InlineKeyboardButton("📺 480P", callback_data="q:480")],
        [InlineKeyboardButton("📱 360P", callback_data="q:360"), InlineKeyboardButton("🎵 MP3", callback_data="q:mp3")],
        [InlineKeyboardButton("📚 Playlist", callback_data="q:playlist")],
        [InlineKeyboardButton("🏠 Home", callback_data="menu:home")],
    ])


def settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Speed Mode: ON", callback_data="set:speed")],
        [InlineKeyboardButton("🔔 Notifications: ON", callback_data="set:notify")],
        [InlineKeyboardButton("🏠 Home", callback_data="menu:home")],
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistics", callback_data="admin:stats"), InlineKeyboardButton("👥 Users", callback_data="admin:users")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast")],
        [InlineKeyboardButton("🏠 Home", callback_data="menu:home")],
    ])


def format_for_quality(q, ffmpeg):
    if q == "best":
        return "bestvideo+bestaudio/best" if ffmpeg else "best[ext=mp4]/best"
    h = int(q)
    return (f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best" if ffmpeg
            else f"best[height<={h}][ext=mp4]/best[height<={h}]/best")


def progress_bar(pct):
    filled = max(0, min(10, int(pct / 10)))
    return "▰" * filled + "▱" * (10 - filled)


def make_progress_hook(loop, message):
    last = {"t": 0.0}
    def hook(d):
        if d.get("status") != "downloading":
            return
        now = time.time()
        if now - last["t"] < 2:
            return
        last["t"] = now
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        done = d.get("downloaded_bytes", 0)
        pct = done / total * 100 if total else 0
        speed = d.get("speed") or 0
        eta = d.get("eta")
        speed_txt = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "calculating..."
        eta_txt = f"{int(eta)}s" if eta is not None else "--"
        text = f"⚡ <b>DOWNLOADING</b>\n\n{progress_bar(pct)} <b>{pct:.1f}%</b>\n🚀 Speed: <b>{speed_txt}</b>\n⏱ ETA: <b>{eta_txt}</b>"
        asyncio.run_coroutine_threadsafe(message.edit_text(text, parse_mode="HTML"), loop)
    return hook


def _transcode_to_telegram_mp4(src: Path, dst: Path):
    if not FFMPEG_EXE:
        raise RuntimeError("FFmpeg is required to create a Telegram-compatible MP4. Install ffmpeg or imageio-ffmpeg.")
    cmd = [
        FFMPEG_EXE, "-y", "-i", str(src),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-c:v", "libx264", "-preset", os.getenv("X264_PRESET", "veryfast"),
        "-crf", os.getenv("X264_CRF", "23"),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", str(dst)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def download_sync(url, quality, workdir, loop, message):
    if not FFMPEG_EXE and quality not in {"mp3"}:
        raise RuntimeError("FFmpeg is not available. The bot needs FFmpeg to merge video/audio and make a compatible MP4.")
    opts = {
        "outtmpl": str(workdir / "%(title)s.%(ext)s"),
        "noplaylist": quality != "playlist",
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": MAX_CONCURRENT_FRAGMENTS,
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 3,
        "socket_timeout": 30,
        "buffersize": "1M",
        "http_chunk_size": 10 * 1024 * 1024,
        "progress_hooks": [make_progress_hook(loop, message)],
    }
    if FFMPEG_EXE:
        opts["ffmpeg_location"] = FFMPEG_EXE

    if quality == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    elif quality == "playlist":
        opts["format"] = "bestvideo+bestaudio/best"
        opts["noplaylist"] = False
        opts["outtmpl"] = str(workdir / "%(playlist_title)s" / "%(playlist_index)s - %(title)s.%(ext)s")
        opts["merge_output_format"] = "mp4"
    else:
        h = None if quality == "best" else int(quality)
        opts["format"] = "bestvideo+bestaudio/best" if h is None else f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    files = [p for p in workdir.rglob("*") if p.is_file() and p.suffix.lower() != ".part"]
    # Force every video sent to Telegram into the widely compatible H.264/AAC MP4
    # format. This fixes black video/no-audio cases caused by AV1/VP9/WebM or
    # separate video/audio streams that Telegram clients cannot play reliably.
    if quality != "mp3":
        converted = []
        for src in files:
            if src.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".ts", ".avi"}:
                dst = src.with_name(src.stem + ".telegram.mp4")
                _transcode_to_telegram_mp4(src, dst)
                src.unlink(missing_ok=True)
                dst.rename(dst.with_name(dst.name.replace(".telegram.mp4", ".mp4")))
                converted.append(dst.with_name(dst.name.replace(".telegram.mp4", ".mp4")))
        if converted:
            files = converted
    return info, files


async def start(update, context):
    save_user(update.effective_user)
    name = html.escape(update.effective_user.first_name or "there")
    admin = update.effective_user.id in ADMIN_IDS
    text = (f"✨ <b>WELCOME, {name.upper()}!</b> ✨\n\n"
            f"🎬 <b>{BOT_NAME}</b>\n"
            "Fast, clean & easy media downloading.\n\n"
            "🔗 Send a video URL and choose your quality.\n"
            "⚡ Multi-fragment downloads for better speed.\n"
            "🎵 MP3 • 🎬 Video • 📚 Playlist\n\n"
            "👇 <b>Choose an option:</b>")
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu(admin))


async def help_cmd(update, context):
    await update.message.reply_text("❓ <b>How to use</b>\n\n1️⃣ Tap New Download\n2️⃣ Send a supported URL\n3️⃣ Select quality\n4️⃣ Wait for download & upload\n\nUse /start anytime to return home.", parse_mode="HTML", reply_markup=main_menu(update.effective_user.id in ADMIN_IDS))


async def url_message(update, context):
    save_user(update.effective_user)
    url = update.message.text.strip()
    if not URL_RE.match(url):
        await update.message.reply_text("❌ <b>Invalid URL</b>\n\nPlease send a complete http/https video URL.", parse_mode="HTML")
        return
    context.user_data["url"] = url
    await update.message.reply_text("🎯 <b>SELECT DOWNLOAD QUALITY</b>\n\nChoose the format you want:", parse_mode="HTML", reply_markup=quality_keyboard())


async def callback(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id
    save_user(q.from_user)
    admin = uid in ADMIN_IDS

    if data == "menu:home":
        await q.edit_message_text("🏠 <b>MAIN MENU</b>\n\nWhat would you like to do?", parse_mode="HTML", reply_markup=main_menu(admin)); return
    if data == "menu:new":
        await q.edit_message_text("🔗 <b>SEND VIDEO URL</b>\n\nPaste the URL here and I'll show the available download options.", parse_mode="HTML"); return
    if data == "menu:settings":
        await q.edit_message_text("⚙️ <b>SETTINGS</b>\n\nSpeed mode uses parallel media fragments where supported.\nNotifications are kept minimal during downloads.", parse_mode="HTML", reply_markup=settings_keyboard()); return
    if data.startswith("set:"):
        await q.answer("Setting saved", show_alert=False); return
    if data == "menu:help":
        await q.edit_message_text("❓ <b>HELP</b>\n\nSend a supported media URL. Choose quality, then the bot downloads and uploads the result.\n\n⚠️ Download only content you are authorized to download.", parse_mode="HTML", reply_markup=main_menu(admin)); return
    if data == "menu:history":
        with db() as con:
            row = con.execute("SELECT downloads FROM users WHERE user_id=?", (uid,)).fetchone()
        count = row[0] if row else 0
        await q.edit_message_text(f"📥 <b>MY DOWNLOADS</b>\n\nCompleted downloads: <b>{count}</b>", parse_mode="HTML", reply_markup=main_menu(admin)); return
    if data == "admin:panel" and admin:
        await q.edit_message_text("👑 <b>ADMIN PANEL</b>\n\nManage the bot from here.", parse_mode="HTML", reply_markup=admin_keyboard()); return
    if data == "admin:stats" and admin:
        users, downloads = stats(); await q.edit_message_text(f"📊 <b>BOT STATISTICS</b>\n\n👥 Users: <b>{users}</b>\n📥 Downloads: <b>{downloads}</b>", parse_mode="HTML", reply_markup=admin_keyboard()); return
    if data == "admin:users" and admin:
        users, _ = stats(); await q.edit_message_text(f"👥 <b>USERS</b>\n\nRegistered users: <b>{users}</b>\n\nUse /broadcast your message to send an announcement.", parse_mode="HTML", reply_markup=admin_keyboard()); return
    if data == "admin:broadcast" and admin:
        context.user_data["broadcast"] = True
        await q.edit_message_text("📢 <b>BROADCAST MODE</b>\n\nSend the message you want to broadcast now.\n\nSend /cancel to stop.", parse_mode="HTML"); return
    if data.startswith("q:"):
        url = context.user_data.get("url")
        if not url:
            await q.edit_message_text("❌ Send a URL first.", reply_markup=main_menu(admin)); return
        quality = data.split(":", 1)[1]
        labels = {"best":"BEST QUALITY","1080":"1080P","720":"720P","480":"480P","360":"360P","mp3":"MP3","playlist":"PLAYLIST"}
        await q.edit_message_text(f"🚀 <b>STARTING {labels.get(quality, quality)} DOWNLOAD</b>\n\nPreparing your media…", parse_mode="HTML")
        await q.message.chat.send_action(ChatAction.TYPING)
        workdir = Path(tempfile.mkdtemp(prefix="vdb_", dir=str(DOWNLOAD_ROOT)))
        try:
            loop = asyncio.get_running_loop()
            _, files = await asyncio.to_thread(download_sync, url, quality, workdir, loop, q.message)
            if not files: raise RuntimeError("No output file was created.")
            max_bytes = MAX_UPLOAD_MB * 1024 * 1024
            sent = 0
            for path in files:
                if path.stat().st_size > max_bytes:
                    await q.message.reply_text(f"⚠️ <b>{html.escape(path.name)}</b> is {path.stat().st_size/1024/1024:.1f} MB and exceeds the configured {MAX_UPLOAD_MB} MB upload limit.", parse_mode="HTML")
                    continue
                await q.message.edit_text(f"📤 <b>UPLOADING</b>\n\n<code>{html.escape(path.name[:100])}</code>", parse_mode="HTML")
                with path.open("rb") as fh:
                    if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}:
                        await q.message.reply_video(video=fh, caption=f"🎬 {safe_name(path.stem)[:850]}", supports_streaming=True)
                    else:
                        await q.message.reply_document(document=fh, caption=f"📁 {safe_name(path.stem)[:850]}")
                sent += 1
            if sent:
                inc_download(uid)
                await q.message.reply_text("✅ <b>DOWNLOAD COMPLETE!</b>\n\nEnjoy your file. ❤️", parse_mode="HTML", reply_markup=main_menu(admin))
            else:
                await q.message.reply_text("⚠️ Download completed, but the result was too large to upload with the current limit.", reply_markup=main_menu(admin))
        except Exception as exc:
            await q.message.reply_text(f"❌ <b>DOWNLOAD FAILED</b>\n\n<code>{html.escape(str(exc)[:1800])}</code>", parse_mode="HTML", reply_markup=main_menu(admin))
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


async def broadcast_cmd(update, context):
    if update.effective_user.id not in ADMIN_IDS: return
    msg = update.message.text.partition(" ")[2].strip()
    if not msg:
        await update.message.reply_text("Usage: /broadcast Your announcement")
        return
    with db() as con: ids = [r[0] for r in con.execute("SELECT user_id FROM users").fetchall()]
    ok = 0
    for uid in ids:
        try:
            await context.bot.send_message(uid, f"📢 <b>ANNOUNCEMENT</b>\n\n{html.escape(msg)}", parse_mode="HTML"); ok += 1
            await asyncio.sleep(0.05)
        except Exception: pass
    await update.message.reply_text(f"✅ Broadcast sent to {ok}/{len(ids)} users.")


async def cancel(update, context):
    context.user_data.clear(); await update.message.reply_text("🛑 Cancelled.", reply_markup=main_menu(update.effective_user.id in ADMIN_IDS))


def main():
    if not BOT_TOKEN: raise SystemExit("BOT_TOKEN environment variable is required.")
    db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, url_message))
    print(f"{BOT_NAME} is running…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()
