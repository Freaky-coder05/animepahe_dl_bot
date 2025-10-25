import os
import subprocess
import re
import glob
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/content/downloads")

# Ensure download folder exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Initialize bot
app = Client("animepahe_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def sanitize_filename(name: str) -> str:
    """Remove invalid filename characters."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


def get_episode_links(series_link: str):
    """Fetch all episode links for a series using animepahe-cli-beta."""
    ep_list_file = os.path.join(DOWNLOAD_DIR, "episodes.txt")
    cmd = ["animepahe-cli-beta", "-l", series_link, "-f", "episodes.txt"]
    subprocess.run(cmd, cwd=DOWNLOAD_DIR, check=True)
    with open(ep_list_file, "r") as f:
        links = [line.strip() for line in f if line.strip()]
    return links


def get_download_url(link: str, quality: int) -> str:
    """Get the direct download URL for the given episode and quality."""
    cmd = ["animepahe-cli-beta", "-l", link, "-q", str(quality), "-x", "-f", "link.txt"]
    subprocess.run(cmd, cwd=DOWNLOAD_DIR, check=True)
    path = os.path.join(DOWNLOAD_DIR, "link.txt")
    with open(path, "r") as f:
        url = f.readline().strip()
    return url


def download_with_aria2(url: str, output_file: str):
    """Download using aria2c (multi-threaded)."""
    cmd = [
        "aria2c",
        "-x", "16",
        "-s", "16",
        "-o", output_file,
        "-d", DOWNLOAD_DIR,
        url
    ]
    subprocess.run(cmd, check=True)


@app.on_message(filters.private & filters.regex(r"https?://.*animepahe.*"))
async def download_specific_episode(_, message: Message):
    text = message.text.strip()
    # Example message: https://animepahe.ru/anime/bleach 5
    parts = text.split()
    if len(parts) < 2:
        await message.reply_text("⚠️ Please include the episode number.\nExample:\n`https://animepahe.ru/anime/bleach 5`")
        return

    series_link = parts[0]
    try:
        episode_number = int(parts[1])
    except ValueError:
        await message.reply_text("❌ Invalid episode number. Example:\n`https://animepahe.ru/anime/bleach 5`")
        return

    await message.reply_text(f"📺 Fetching episodes for series...\nSelected episode: {episode_number}")

    try:
        episode_links = get_episode_links(series_link)
    except Exception as e:
        await message.reply_text(f"❌ Failed to fetch episode list: {e}")
        return

    if episode_number < 1 or episode_number > len(episode_links):
        await message.reply_text(f"❌ Episode {episode_number} not found! This series has only {len(episode_links)} episodes.")
        return

    ep_link = episode_links[episode_number - 1]
    await message.reply_text(f"🎬 Found Episode {episode_number}.\nStarting downloads...")

    for q in [360, 720, 1080]:
        await message.reply_text(f"⬇️ Downloading Episode {episode_number} in {q}p...")

        try:
            url = get_download_url(ep_link, q)
        except Exception as e:
            await message.reply_text(f"❌ Failed to get URL for {q}p: {e}")
            continue

        output_file = f"episode_{episode_number}_{q}p.mp4"

        try:
            download_with_aria2(url, output_file)
        except Exception as e:
            await message.reply_text(f"❌ Download failed for {q}p: {e}")
            continue

        final_path = os.path.join(DOWNLOAD_DIR, output_file)
        if not os.path.exists(final_path):
            files = glob.glob(os.path.join(DOWNLOAD_DIR, "*"), recursive=True)
            if files:
                latest_file = max(files, key=os.path.getmtime)
                shutil.move(latest_file, final_path)

        await message.reply_document(final_path)
        await message.reply_text(f"✅ Uploaded Episode {episode_number} {q}p")

    await message.reply_text("🎉 All qualities downloaded successfully!")


@app.on_message(filters.command("start") & filters.private)
async def start(_, m: Message):
    await m.reply_text(
        "👋 Send me an AnimePahe series link followed by episode number.\n\n"
        "📘 Example:\n`https://animepahe.ru/anime/bleach 5`\n\n"
        "I’ll download Episode 5 in 360p, 720p, and 1080p."
    )


if __name__ == "__main__":
    print("Bot is running ...")
    app.run()
