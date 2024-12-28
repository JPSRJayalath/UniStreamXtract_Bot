import instaloader
import requests
import os

def download_instagram_content(content_url, download_folder):
    loader = instaloader.Instaloader()

    try:
        # Extract the shortcode from the URL
        shortcode = content_url.split("/")[-2]

        # Load the Post object
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # Fetch the title (caption) of the video
        title = post.caption

        # Ensure the download folder exists
        if not os.path.exists(download_folder):
            os.makedirs(download_folder, exist_ok=True)

        # Check the content type
        if post.is_video:
            # Handle video (reels or video posts)
            video_url = post.video_url

            response = requests.get(video_url)
            if response.status_code == 200:
                file_path = os.path.join(download_folder, f"{shortcode}_video.mp4")
                with open(file_path, "wb") as video_file:
                    video_file.write(response.content)
                return 0, title
            else:
                return 1, response.status_code

        elif post.typename == "GraphSidecar":
            # Handle carousel posts (multiple images/videos)
            for i, node in enumerate(post.get_sidecar_nodes(), start=1):
                media_url = node.video_url if node.is_video else node.display_url
                file_extension = "mp4" if node.is_video else "jpg"
                file_path = os.path.join(download_folder, f"{shortcode}_{i}.{file_extension}")
                response = requests.get(media_url)
                if response.status_code == 200:
                    with open(file_path, "wb") as media_file:
                        media_file.write(response.content)
                else:
                    return 1, str(response.status_code)
            return 0, title
        else:
            # Handle single image post
            image_url = post.url
            response = requests.get(image_url)
            if response.status_code == 200:
                file_path = os.path.join(download_folder, f"{shortcode}_image.jpg")
                with open(file_path, "wb") as image_file:
                    image_file.write(response.content)
                return 0, title
            else:
                return 1, response.status_code

    except Exception as e:
        return 1, f"Error: {str(e)}"
