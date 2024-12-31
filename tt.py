import yt_dlp
import os
from datetime import datetime
import re
import requests


# Function to fetch YouTube video details with yt-dlp (this is blocking)
def fetch_tiktok_video_info(url):
    ydl_opts = {
        'noplaylist': True,  # Don't fetch a playlist if the URL is a playlist
        'quiet': True,  # Suppress output to keep it clean
        'extract_flat': True,  # Only extract the metadata without downloading the video
        'force_generic_extractor': False,  # Use the YouTube extractor
        'retries': 5,  # Retry on errors
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract the video info
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", 'Tiktok Video'),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "url": info.get("webpage_url"),
                "thumbnail": info.get("thumbnail"),
                "formats": info.get("formats"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "dislike_count": info.get("dislike_count", 'No Dislikes'),
                "channel_url": info.get("channel_url"),
                "category": info.get("categories", []),
                "tags": info.get("tags", []),
                "is_live": info.get("is_live"),
                "age_limit": info.get("age_limit"),
                "chapters": info.get("chapters", []),
                "playlist_title": info.get("playlist_title"),
                "playlist_id": info.get("playlist_id"),
                "playlist_url": info.get("playlist_url"),
            }
    except Exception as e:
        return {"error": str(e)}


def resolve_redirect(real_url):
    """
    Follow the redirection to get the actual Facebook Reel URL.
    """
    try:
        response = requests.get(real_url, allow_redirects=True)
        return response.url
    except Exception as e:
        return 1


def create_save_directory(save_path: str) -> None:
    if not os.path.exists(save_path):
        os.makedirs(save_path)

def validate_url(url: str) -> bool:
    tiktok_pattern = r'https?://((?:vm|vt|www)\.)?tiktok\.com/.*'
    return bool(re.match(tiktok_pattern, url))


def quick_mode_tt(video_url, save_path):
    if not validate_url(video_url):
        return 1

    # Configure download options
    ydl_opts = {
        'format': 'bv*[vcodec=avc1]+ba[acodec=aac]/mp4',  # Restrict to H.264 video and AAC audio
        'merge_output_format': 'mp4',  # Ensure the output file is MP4
        'outtmpl': os.path.join(save_path, 'UniStreamXtracted_Stream.%(ext)s'),  # Filename with title and resolution
        'quiet': True,  # Suppress output in the terminal
        'no_warnings': True,  # Suppress warnings
        'retries': 5,  # Retry on errors
        'noprogress': True,  # Disable progress bar
        'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Ensure final format is MP4
            }
        ]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            return 0

    except yt_dlp.utils.DownloadError as e:
        return e
    except Exception as e:
        return e