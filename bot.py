import os
import subprocess
import re
import glob
import shutil
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

# Create download directory if not exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Initialize Pyrogram bot
app = Client("animepahe_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


def run_cli(link: str, quality: int):
    """Run animepahe-cli for a given link and quality."""
    cmd = ["animepahe-cli", "-l", link, "-q", str(quality)]
    subprocess.run(cmd, cwd=DOWNLOAD_DIR, check=True)


@app.on_message(filters.private & filters.regex(r"https?://.*animepahe.*"))
async def download_anime(_, message: Message):
    link = message.text.strip()

    # Extract anime name and episode number (basic)
    parts = link.rstrip("/").split("/")
    anime_name = sanitize_filename(parts[-2].replace("-", "_"))
    episode_num = sanitize_filename(parts[-1].replace("-", "_"))

    await message.reply_text(f"🎬 Starting download for:\n{anime_name} Episode {episode_num}")

    for q in [360, 720, 1080]:
        await message.reply_text(f"⬇️ Downloading {q}p ...")

        # Run CLI download
        try:
            run_cli(link, q)
        except subprocess.CalledProcessError:
            await message.reply_text(f"❌ Download failed for {q}p")
            continue

        # Wait briefly to ensure file is written
        time.sleep(2)

        # Detect the most recently downloaded file (any extension, any subfolder)
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "**/*.*"), recursive=True)
        if not files:
            await message.reply_text(f"❌ No downloaded file found for quality {q}p")
            continue

        latest_file = max(files, key=os.path.getmtime)  # newest file
        ext = os.path.splitext(latest_file)[1]
        target_file = os.path.join(DOWNLOAD_DIR, f"{anime_name}_ep{episode_num}_{q}p{ext}")

        # Rename/move to standardized filename
        shutil.move(latest_file, target_file)

        # Upload to Telegram
        await message.reply_document(target_file)

    await message.reply_text("✅ All downloads finished!")


@app.on_message(filters.command("start") & filters.private)
async def start(_, m: Message):
    await m.reply_text(
        "👋 Send me an AnimePahe episode link.\n"
        "I will download it in 360p, 720p, and 1080p and send the files to you."
    )


if __name__ == "__main__":
    print("Bot is running ...")
    app.run()
