import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
LOG_DIR = os.getenv("LOG_DIR", "logs")

# Create directories
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Initialize Pyrogram bot
app = Client("animepahe_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def run_cli_stream(link: str, quality: int):
    """
    Runs animepahe-cli download command and streams stdout for progress.
    """
    cmd = ["animepahe-cli", "-l", link, "-q", str(quality)]
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=DOWNLOAD_DIR
    )
    for line in process.stdout:
        yield line.strip()


def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


@app.on_message(filters.private & filters.regex(r"https?://.*animepahe.*"))
async def download_anime(_, message: Message):
    link = message.text.strip()

    # Extract anime name and episode number (basic method)
    parts = link.rstrip("/").split("/")
    anime_name = sanitize_filename(parts[-2].replace("-", "_"))
    episode_num = sanitize_filename(parts[-1].replace("-", "_"))

    await message.reply_text(f"🎬 Starting download for:\n{anime_name} Episode {episode_num}")

    for q in [360, 720, 1080]:
        filename = f"{anime_name}_ep{episode_num}_{q}p.mp4"
        msg = await message.reply_text(f"⬇️ Downloading {q}p ... 0%")

        # Stream download progress
        last_percent = ""
        for line in run_cli_stream(link, q):
            if "%" in line:
                try:
                    percent = [s for s in line.split() if "%" in s][0]
                    if percent != last_percent:
                        last_percent = percent
                        await msg.edit_text(f"⬇️ Downloading {q}p ... {percent}")
                except:
                    pass

        await msg.edit_text(f"✅ {q}p download complete! Uploading to Telegram ...")

        # Upload the file
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.exists(file_path):
            await message.reply_document(file_path)
        else:
            await message.reply_text(f"❌ File {filename} not found after download.")

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
