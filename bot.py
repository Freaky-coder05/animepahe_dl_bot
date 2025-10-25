import os
import subprocess
import requests
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/content/downloads")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client("animepahe_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


def get_series_slug(series_url: str) -> str:
    """Extract the anime slug from a URL."""
    return series_url.rstrip("/").split("/")[-1]


def get_episode_link(series_slug: str, episode_number: int):
    """Fetch AnimePahe episode play URL via API."""
    api = f"https://animepahe.ru/api?m=release&id={series_slug}&sort=episode_asc"
    res = requests.get(api).json()

    if "data" not in res:
        raise ValueError("❌ No episodes found for this series.")
    episodes = res["data"]

    if episode_number < 1 or episode_number > len(episodes):
        raise ValueError(f"Invalid episode number. Series has {len(episodes)} episodes.")

    ep_data = episodes[episode_number - 1]
    session = ep_data["session"]
    ep_num = ep_data["episode"]

    return f"https://animepahe.ru/play/{series_slug}/{session}", ep_num


@app.on_message(filters.private & filters.regex(r"https?://.*animepahe.*"))
async def handle_download(_, message: Message):
    """
    If user sends:
      - only series link → download all episodes (1080p)
      - series link + number → download that episode in 360p, 720p, 1080p
    """
    parts = message.text.strip().split()

    # Case 1: Only URL (download all episodes)
    if len(parts) == 1:
        series_url = parts[0]
        slug = get_series_slug(series_url)
        await message.reply_text(f"📥 Downloading all episodes for `{slug}` in 1080p ...")

        try:
            subprocess.run(
                ["animepahe-cli-beta", "-l", series_url, "-q", "1080", "-d", DOWNLOAD_DIR],
                check=True
            )
            await message.reply_text("✅ All episodes downloaded successfully.")
        except subprocess.CalledProcessError as e:
            await message.reply_text(f"❌ CLI error: {e}")
        return

    # Case 2: URL + Episode Number (download 3 qualities)
    elif len(parts) == 2:
        series_url, ep_str = parts
        slug = get_series_slug(series_url)

        try:
            episode_number = int(ep_str)
        except ValueError:
            await message.reply_text("❌ Invalid episode number format.")
            return

        await message.reply_text(f"🎬 Fetching episode {episode_number} info for `{slug}` ...")

        try:
            episode_url, ep_num = get_episode_link(slug, episode_number)
        except Exception as e:
            await message.reply_text(f"❌ Failed to fetch episode: {e}")
            return

        await message.reply_text(f"📺 Found Episode {ep_num}\n🔗 {episode_url}")

        # Download all 3 qualities
        for quality in ["360", "720", "1080"]:
            await message.reply_text(f"⬇️ Downloading {quality}p ...")

            try:
                subprocess.run(
                    [
                        "animepahe-cli-beta",
                        "-e", episode_url,
                        "-q", quality,
                        "-d", DOWNLOAD_DIR
                    ],
                    check=True
                )
                # Find the latest file
                latest = max(
                    (os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)),
                    key=os.path.getmtime
                )
                await message.reply_document(latest, caption=f"{slug} - Episode {ep_num} ({quality}p)")
            except subprocess.CalledProcessError as e:
                await message.reply_text(f"❌ Download failed for {quality}p: {e}")
                continue

        await message.reply_text(f"✅ Finished downloading all qualities for episode {ep_num}!")
    else:
        await message.reply_text(
            "⚙️ Usage:\n"
            "`<series_url>` → all episodes (1080p)\n"
            "`<series_url> <episode_number>` → one episode in 360p, 720p, 1080p"
        )


@app.on_message(filters.command("start") & filters.private)
async def start(_, m: Message):
    await m.reply_text(
        "👋 Send an AnimePahe series link.\n\n"
        "Examples:\n"
        "`https://animepahe.ru/anime/bleach` → All episodes (1080p)\n"
        "`https://animepahe.ru/anime/bleach 5` → Episode 5 (360p + 720p + 1080p)"
    )


if __name__ == "__main__":
    print("🚀 Bot is running...")
    app.run()
