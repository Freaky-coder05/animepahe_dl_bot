import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
LOG_DIR = os.getenv("LOG_DIR", "logs")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

app = Client("animepahe_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def run_cli(link: str, quality: int):
    cmd = ["animepahe-cli", "-l", link, "-q", str(quality)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=DOWNLOAD_DIR)
    return proc.returncode, proc.stdout, proc.stderr

@app.on_message(filters.private & filters.regex(r"https?://.*animepahe.*"))
async def download_anime(_, message: Message):
    link = message.text.strip()
    await message.reply_text(f"🎬 Starting download for:\n{link}\n\nQualities: 360p, 720p, 1080p")
    for q in [360, 720, 1080]:
        msg = await message.reply_text(f"⬇️ Downloading {q}p ...")
        code, out, err = run_cli(link, q)
        with open(os.path.join(LOG_DIR, f"{q}p.log"), "a") as f:
            f.write(out + "\n" + err)
        if code == 0:
            await msg.edit_text(f"✅ {q}p download complete!")
        else:
            await msg.edit_text(f"❌ {q}p failed.\n{err}")

@app.on_message(filters.command("start") & filters.private)
async def start(_, m: Message):
    await m.reply_text("👋 Send me an AnimePahe episode link to download in 360p, 720p, and 1080p.")

app.run()
