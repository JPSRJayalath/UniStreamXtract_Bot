import os.path
import asyncio
import telethon as tl
import yt_dlp

# Function to fetch Facebook video details using yt-dlp
def fetch_facebook_video_info(url):
    ydl_opts = {
        'noplaylist': True,  # Don't fetch a playlist if the URL is a playlist
        'quiet': True,  # Suppress output to keep it clean
        'extract_flat': True,  # Only extract the metadata without downloading the video
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "url": info.get("webpage_url"),
                "thumbnail": info.get("thumbnail"),
                "formats": info.get("formats"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "dislike_count": info.get("dislike_count", 'No Dislikes'),
                "is_live": info.get("is_live"),
            }
    except Exception as e:
        return {"error": str(e)}

# Function to download Facebook video
def fb_dl(user_id, url, video_id):
    folder = f'./downloads/tiktok/{user_id}'
    os.makedirs(folder, exist_ok=True)

    ydl_opts = {
        'format': f'{video_id}',  # Use the selected video format
        'outtmpl': f'{folder}/UniStreamXtracted_Stream.%(ext)s',  # File output template
        'quiet': True,  # Suppress output
        'retries': 10,  # Retry on failure
        'socket_timeout': 30,  # Timeout for connections
        'fragment_retries': 10,  # Retry fragment downloads
        'noplaylist': True,  # Don't download playlists
        'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Ensure final format is MP4
            }
        ]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return "Done"
    except Exception as e:
        return f"Error: {e}"

# Function to present video quality options
async def select_fb_format(event, robot, formats):
    buttons = []
    for fmt in formats:
        format_id = fmt.get("format_id", "N/A")
        resolution = fmt.get("resolution", "Unknown")
        vcodec = fmt.get('vcodec')  # Video codec

        if resolution not in ["Unknown", "audio only", None]:
            button_text = f"Res: {resolution.split('x')[-1]}p | Codec: {vcodec}"
            buttons.append([tl.Button.inline(button_text, data=f"{format_id}#{resolution.split('x')[-1]}")])

    if not buttons:
        await event.reply("No available video formats.")
        return None

    message = await event.reply("Select a video quality:", buttons=buttons)
    selection_event = asyncio.Event()
    selected_format_id = {"id": None}

    async def on_callback(callback_event):
        callback_quaries = callback_event.data.decode("utf-8").split("#")
        selected_format_id["id"] = callback_quaries[0]
        await callback_event.respond(f"Selected Quality: {callback_quaries[1]}p")
        selection_event.set()
        await message.delete()

    robot.add_event_handler(on_callback, tl.events.CallbackQuery)

    try:
        await asyncio.wait_for(selection_event.wait(), timeout=120)
        return selected_format_id["id"]
    except asyncio.TimeoutError:
        await message.delete()
        return None
    finally:
        robot.remove_event_handler(on_callback, tl.events.CallbackQuery)