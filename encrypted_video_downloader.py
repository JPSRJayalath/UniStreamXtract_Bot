
import json
import requests
import xmltodict
import pprint
from tqdm import tqdm
from urllib.parse import urlparse
import video_and_audio_decrypting_and_merge_video_and_audio

data = {"video_file_name":'',"audio_file_name":''}
temp = []

def video_details(video, user_id):
    contentType = video['@contentType']
    Representation = video['Representation']
    temp_video_file = []
    temp_video_bandwith = []
    if type(Representation) == dict:
        id = Representation['@id']
        baseurl = Representation['BaseURL']
        bandwith = int(Representation['@bandwidth']) // 100
        file = open(f'./downloads/vdocipher/{user_id}/Temp/data.json', 'w')
        data['video_file_name'] = baseurl
        json.dump(data, file)
        file.close()
    else:
        for i in Representation:
            id = i['@id']
            baseurl = i['BaseURL']
            bandwith = int(i['@bandwidth']) // 1000
            temp_video_file.append(baseurl)
            temp_video_bandwith.append(bandwith)
        high_bandwith = max(temp_video_bandwith)
        high_bandwith_location = temp_video_bandwith.index(high_bandwith)
        file = open(f'./downloads/vdocipher/{user_id}/Temp/data.json', 'w')
        data['video_file_name'] = temp_video_file[high_bandwith_location]
        json.dump(data, file)
        file.close()



def audio_details(audio, user_id):
    contentType = audio['@contentType']
    Representation = audio['Representation']
    if type(Representation) == dict:
        id = Representation['@id']
        baseurl = Representation['BaseURL']
        bandwith = int(Representation['@bandwidth']) // 1000
        file = open(f'./downloads/vdocipher/{user_id}/Temp/data.json', 'w')
        data['audio_file_name'] = baseurl
        json.dump(data, file)
        file.close()
    else:
        for i in Representation:
            id = i['@id']
            baseurl = i['BaseURL']
            bandwith = int(i['@bandwidth']) // 1000
            file_name = input("Enter file name: ")
            file = open(f'./downloads/vdocipher/{user_id}/Temp/data.json', 'w')
            data['audio_file_name'] = file_name
            json.dump(data, file)
            file.close()

def get_base_url(url):
    # URL to parse

    # Parse the URL
    parsed_url = urlparse(url)

    # Extract components
    scheme = parsed_url.scheme  # 'https'
    netloc = parsed_url.netloc  # 'd1v1gqjht5uu1.cloudfront.net'
    path = parsed_url.path  # '/media/IxsvL3GWfuJRx/3a1f17c5/stream.mpd'
    temp = ''
    only_path = ''
    for i in range(len(path)):
        if path[i] == '.':
            only_path += '/'
            break
        elif path[i] == '/':
            if i == 0:
                only_path += temp
                temp = ''
            else:
                only_path += path[i] + temp
                temp = ''
        else:
            temp += path[i]

    # Reconstruct base URL
    URL = scheme+'://'+netloc+only_path
    return URL

def download_file_with_progress(url, output_path):
    """
        Downloads a video file with a progress bar animation.

        Args:
            url (str): The URL of the video file.
            output_path (str): The file path where the video will be saved.

        Returns:
            None
        """
    try:
        # Send a HEAD request to get the file size for the progress bar
        response = requests.head(url, allow_redirects=True)
        file_size = int(response.headers.get('content-length', 0))

        # Check if file size is available
        if file_size == 0:
            print("Unable to retrieve file size. Progress bar may not work correctly.")

        # Start downloading the file with streaming
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Ensure the request is successful

        # Open the file and write the content in chunks
        with open(output_path, "wb") as file, tqdm(
                desc=f"Downloading {output_path}",
                total=file_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
        ) as progress_bar:
            for chunk in response.iter_content(chunk_size=1024):  # 1 KB chunks
                if chunk:  # Skip keep-alive chunks
                    file.write(chunk)
                    progress_bar.update(len(chunk))

        print(f"Download completed: {output_path}\n")

    except requests.RequestException as e:
        print(f"Error during download: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def main(mpd_url, user_id):
    try:
        response = requests.get(mpd_url)
        if response.status_code != 200:
            print("Failed to retrieve MPD file")
            return
        mpd_content = response.content

        mpd_dict = xmltodict.parse(mpd_content)
        list_mpd = mpd_dict['MPD']['Period']['AdaptationSet']

        audio = list_mpd[0]
        video = list_mpd[1]

        video_details(video, user_id)
        audio_details(audio, user_id)

        baseurl = get_base_url(mpd_url)

        file = open(f'./downloads/vdocipher/{user_id}/Temp/data.json', 'r')
        download_data = json.loads(file.read())
        full_url = baseurl + download_data['video_file_name']
        print(full_url)  # Debugging step to verify URL

        # Call the function with the correct URL
        download_file_with_progress(full_url, f'./downloads/vdocipher/{user_id}/Temp/video.mp4')


        full_url = baseurl + download_data['audio_file_name']
        print(full_url)  # Debugging step to verify URL

        # Call the function with the correct URL
        download_file_with_progress(full_url, f'./downloads/vdocipher/{user_id}/Temp/audio.mp4')

        return 'Done'
    
    except Exception as e:
        return e