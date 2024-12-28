import asyncio
import json
import zipfile
import aiohttp
import aiofiles
import os
import shutil

max_bigited = 2 * 1000 * 1024 * 1024

with open('./config/config.json') as configs:
    bot_config = json.load(configs)


async def send_file(user_id, bot_token, semaphore, file_path, title, caption, doc_type):
    url = {
        'vid': f'http://localhost:8081/bot{bot_token}/sendVideo',
        'doc': f'http://localhost:8081/bot{bot_token}/sendDocument',
        'aud': f'http://localhost:8081/bot{bot_token}/sendAudio',
        'ani': f'http://localhost:8081/bot{bot_token}/sendAnimation'
    }

    file_size = os.path.getsize(file_path + title)

    if max_bigited > file_size:
        try:
            async with semaphore:  # Limiting concurrent uploads
                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field('chat_id', str(user_id))  # Add the chat_id field

                    # Open the file and add it to the form
                    async with aiofiles.open(file_path + title, 'rb') as file:
                        if doc_type == 'vid':
                            form.add_field('video', await file.read(), filename=title, content_type='video/mp4')
                            form.add_field('caption', caption)  # Add caption for video
                        elif doc_type == 'doc':
                            form.add_field('document', await file.read(), filename=title, content_type='application/octet-stream')
                            form.add_field('caption', caption)  # Add caption for document
                        elif doc_type == 'aud':
                            form.add_field('audio', await file.read(), filename=title, content_type='audio/mpeg')
                            form.add_field('caption', caption)  # Add caption for audio
                        elif doc_type == 'ani':
                            form.add_field('animation', await file.read(), filename=title, content_type='image/gif')
                            form.add_field('caption', caption)  # Add caption for animation
                        # elif doc_type == 'zip':
                        #     form.add_field('document', await file.read(), filename=title, content_type='application/zip')
                        #     form.add_field('caption', caption)  # Add caption for zip file
                        else:
                            return f"Invalid doc_type: {doc_type}"

                    # Make the POST request
                    async with session.post(url[doc_type], data=form) as response:
                        if response.status == 200:
                            shutil.rmtree(file_path)
                            return 'Done'
                        else:
                            shutil.rmtree(file_path)
                            return f"Error: {response.status} - {await response.text()}"
        except aiohttp.ClientError as e:
            return f"ClientError: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    else:
        return 201



async def send_files(user_id, bot_token, semaphore, file_path, title, caption, doc_type):
    url = {
        'vid': f'http://localhost:8081/bot{bot_token}/sendVideo',
        'doc': f'http://localhost:8081/bot{bot_token}/sendDocument',
        'aud': f'http://localhost:8081/bot{bot_token}/sendAudio',
        'ani': f'http://localhost:8081/bot{bot_token}/sendAnimation',
        'img': f'http://localhost:8081/bot{bot_token}/sendPhoto'  # New URL entry for sending images
    }

    file_size = os.path.getsize(file_path + title)

    if max_bigited > file_size:  # Ensure the file size is under the allowed limit
        try:
            async with semaphore:  # Limiting concurrent uploads
                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field('chat_id', str(user_id))  # Add the chat_id field

                    # Open the file and add it to the form
                    async with aiofiles.open(file_path + title, 'rb') as file:
                        if doc_type == 'vid':
                            form.add_field('video', await file.read(), filename=title, content_type='video/mp4')
                            form.add_field('caption', caption)  # Add caption for video
                        elif doc_type == 'doc':
                            form.add_field('document', await file.read(), filename=title, content_type='application/octet-stream')
                            form.add_field('caption', caption)  # Add caption for document
                        elif doc_type == 'aud':
                            form.add_field('audio', await file.read(), filename=title, content_type='audio/mpeg')
                            form.add_field('caption', caption)  # Add caption for audio
                        elif doc_type == 'ani':
                            form.add_field('animation', await file.read(), filename=title, content_type='image/gif')
                            form.add_field('caption', caption)  # Add caption for animation
                        elif doc_type == 'img':  # Handling image files
                            form.add_field('photo', await file.read(), filename=title, content_type='image/jpeg')  # Adjust content type if necessary
                            form.add_field('caption', caption)  # Add caption for image
                        else:
                            return f"Invalid doc_type: {doc_type}"

                    # Make the POST request
                    async with session.post(url[doc_type], data=form) as response:
                        if response.status == 200:
                            return 0
                        else:
                            return f"Error: {response.status}"
        except aiohttp.ClientError as e:
            return f"ClientError: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    else:
        return 201


async def send_file_drm(user_id, bot_token, semaphore, title, doc_type):
    url = {
        'vid': f'http://localhost:8081/bot{bot_token}/sendVideo',
        'doc': f'http://localhost:8081/bot{bot_token}/sendDocument'
    }

    video_path = f'./downloads/vdocipher/{user_id}/OUT/{title}.mp4'
    video_dir = f'./downloads/vdocipher/{user_id}/OUT/'
    zip_saved = f'./downloads/vdocipher/{user_id}/DRM/'

    file_size = os.path.getsize(video_path)

    if max_bigited > file_size:

        if user_id == bot_config['owner_user_id']:

            zip_result = zipping(user_id, zip_saved, title, video_dir)
            if zip_result == 0:
                ff = await send_file(user_id, bot_token, semaphore, zip_saved, f'{title}.zip', f'{title}', 'doc')
                print(ff)
            else:
                return 'error'
        else:
            await send_file(user_id, bot_token, semaphore, video_dir, f'{title}.mp4', f'{title}', 'vid')

    else:
        return 201


def zipping(user_id, zip_path, title, folder_path):
    if os.path.exists(zip_path) == False:
        os.makedirs(zip_path, exist_ok=True)
    try:
        with zipfile.ZipFile(f'{zip_path+title}.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=folder_path)  # Preserve folder structure
                    zipf.write(file_path, arcname=arcname)
        print(f"Folder {folder_path} zipped successfully as {zip_path+title}.zip")
        return 0

    except Exception as e:
        print(f"An error occurred: {e}")


async def search_file_name(ext, path):
    try:
        extension = ext
        filepath = path
        files = os.listdir(filepath)
        txt_files = list([file for file in files if os.path.splitext(file)[1] == extension])
        file_name = txt_files[0]
        return file_name, "Done"
    except Exception as e:
        return e, 'Fail'