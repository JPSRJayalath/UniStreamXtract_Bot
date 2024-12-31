import os.path

import yt_dlp

# Function to fetch YouTube video details with yt-dlp (this is blocking)
def fetch_youtube_video_info(url):
    ydl_opts = {
        'noplaylist': True,  # Don't fetch a playlist if the URL is a playlist
        'quiet': True,  # Suppress output to keep it clean
        'extract_flat': True,  # Only extract the metadata without downloading the video
        'force_generic_extractor': False,  # Use the YouTube extractor
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract the video info
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
                "dislike_count": info.get("dislike_count"),
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

def yt_dl(user_id, url, audio_id, video_id):

    # Create Folder with user_id
    if os.path.exists(f'./downloads/yt/{user_id}') == False:
        os.makedirs(f'./downloads/yt/{user_id}', exist_ok=True)

    # Choose download option for yt_dlp
    if str(video_id) == '0':
        ydl_opts = {
            'format': f'{audio_id}',
            'user_agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0',  # Custom User-Agent string
            'socket_timeout': 30,  # Set timeout for the connection
            'retries': 3,
            'outtmpl': f'./downloads/yt/{user_id}/audio.%(ext)s',  # Output filename template
            'quiet': True,  # Suppress output to keep it clean
        }

    else:
        ydl_opts = {
            'format': f'{video_id}+{audio_id}',
            'user_agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0',
            # Custom User-Agent string
            'socket_timeout': 30,  # Set timeout for the connection
            'retries': 10,  # Retry failed downloads multiple times
            'outtmpl': f'./downloads/yt/{user_id}/UniStreamXtracted_Stream.%(ext)s',  # Output filename template
            'quiet': True,  # Suppress output to keep it clean
            'noplaylist': True,  # Disable playlist download if video is part of a playlist
            'max_filesize': None,  # No size limit, useful for long videos
            'noprogress': True,  # Show download progress
            'fragment_retries': 10,  # Retry fragment downloads multiple times
            'buffersize': 1024 * 1024 * 10,  # Set buffer size to handle larger files
            'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Ensure final format is MP4
            }
        ]
        }


    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(url)
        return "Done"
    except Exception as e:
        return f"Error: {e}"

