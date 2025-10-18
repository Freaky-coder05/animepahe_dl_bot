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
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/content/downloads")

# Create download directory if not exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Initialize Pyrogram bot
app = Client("animepahe_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


def get_download_url(link: str, quality: int) -> str:
    """Use animepahe-cli to get the direct download URL."""
    cmd = ["animepahe-cli", "-l", link, "-q", str(quality), "-x", "-f", "links.txt"]
    subprocess.run(cmd, cwd=DOWNLOAD_DIR, check=True)
    path = os.path.join(DOWNLOAD_DIR, "links.txt")
    with open(path, "r") as f:
        url = f.readline().strip()
    return url


def download_with_aria2(url: str, output_file: str):
    """Download file using aria2c (multi-threaded)."""
    cmd = [
        "aria2c",
        "-x", "16",  # 16 connections
        "-s", "16",
        "-o", output_file,
        "-d", DOWNLOAD_DIR,
        url
    ]
    subprocess.run(cmd, check=True)


@app.on_message(filters.private & filters.regex(r"https?://.*animepahe.*"))
async def download_anime(_, message: Message):
    link = message.text.strip()

    # Extract anime name and episode number (basic)
    parts = link.rstrip("/").split("/")
    anime_name = sanitize_filename(parts[-2].replace("-", "_"))
    episode_num = sanitize_filename(parts[-1].replace("-", "_"))
    print(f"{anime_name}{anime_name}.mp4")
    await message.reply_text(f"🎬 Starting download for:\n{anime_name} Episode {episode_num}")

    for q in [360, 720, 1080]:
        await message.reply_text(f"⬇️ Preparing {q}p download ...")

        # Get direct download URL
        try:
            url = get_download_url(link, q)
        except Exception as e:
            await message.reply_text(f"❌ Failed to get URL for {q}p: {e}")
            continue

        # Prepare output filename
        ext = os.path.splitext(url)[1] or ".mp4"
        output_file = f"{anime_name}_ep{episode_num}_{q}p{ext}"

        # Download with aria2c
        try:
            download_with_aria2(url, output_file)
        except Exception as e:
            await message.reply_text(f"❌ Download failed for {q}p: {e}")
            continue

        # Rename/move to standard location
        final_path = os.path.join(DOWNLOAD_DIR, output_file)
        if not os.path.exists(final_path):
            # If aria2c did not save exactly, find the newest file
            files = glob.glob(os.path.join(DOWNLOAD_DIR, "*"), recursive=True)
            if files:
                latest_file = max(files, key=os.path.getmtime)
                shutil.move(latest_file, final_path)

        # Upload to Telegram
        await message.reply_document(final_path)

    await message.reply_text("✅ All downloads finished!")


@app.on_message(filters.command("start") & filters.private)
async def start(_, m: Message):
    await m.reply_text(
        "👋 Send me an AnimePahe episode link.\n"
        "I will download it in 360p, 720p, and 1080p using multi-threaded download and send the files to you."
    )


if __name__ == "__main__":
    print("Bot is running ...")
    app.run()
