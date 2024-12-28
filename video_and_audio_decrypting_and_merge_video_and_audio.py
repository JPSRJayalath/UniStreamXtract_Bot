import json
import subprocess
import os
import shutil
from colorama import Fore

terminal_size = os.get_terminal_size().columns


def clear_temp_files(user_id):
    shutil.rmtree(f'./downloads/vdocipher/{user_id}/Temp/')
    print("Temp directry Clean...Success!")


def audio_video_merge(out_file_name, user_id):
    print('*' * terminal_size)
    print()
    path = f'ffmpeg -i ./downloads/vdocipher/{user_id}/Temp/tempdecrypted_audio.mp4 -i ./downloads/vdocipher/{user_id}/Temp/tempdecrypted_video.mp4 -vcodec copy -acodec copy ./downloads/vdocipher/{user_id}/OUT/{out_file_name}.mp4'

    try:
        # Run a command and raise an exception if it fails
        result = subprocess.run([path], capture_output=True, text=True, check=True, shell=True)
        print('*' * terminal_size)
        print()
        print("Video & Audio Merge Success!")
        print()
        print("Decrypted Video saved in OUT directry")
        print()
        print('*' * terminal_size)
        print()
        clear_temp_files(user_id)
        return "Done"
    except subprocess.CalledProcessError as e:
        # Handle the error if the command returns a non-zero exit code
        print(Fore.LIGHTRED_EX + 'Error: Command failed with return code', e.returncode)
        print(Fore.LIGHTRED_EX + 'Error Output:', e.stderr)
        clear_temp_files(user_id)
        return "Error"
    except FileNotFoundError as e:
        # Handle the error if the command is not found
        print(Fore.LIGHTRED_EX + 'Error: Command not found', e)
        clear_temp_files(user_id)
        return "Error"
    except Exception as e:
        # Handle any other exceptions
        print(Fore.LIGHTRED_EX + 'An unexpected error occurred:', e)
        return "Error"


def video_decrypt(user_id):
    keys_file = open(f"./downloads/vdocipher/{user_id}/Temp/keys.json", 'r')
    data = keys_file.read()
    keys_file.close()
    keys = json.loads(data)

    print('*' * terminal_size)
    print()
    path = './cmakebuild/mp4decrypt --key ' + keys['video_key'] + f' ./downloads/vdocipher/{user_id}/Temp/video.mp4 ./downloads/vdocipher/{user_id}/Temp/tempdecrypted_video.mp4'

    try:
        # Run a command and raise an exception if it fails
        result = subprocess.run([path], capture_output=True, text=True, check=True, shell=True)
        print("Video Decryption Success!")
        print()
        print('*' * terminal_size)
        return "Done"
    except subprocess.CalledProcessError as e:
        # Handle the error if the command returns a non-zero exit code
        print(Fore.LIGHTRED_EX + 'Error: Command failed with return code', e.returncode)
        print(Fore.LIGHTRED_EX + 'Error Output:', e.stderr)
        clear_temp_files(user_id)
        return "Error"
    except FileNotFoundError as e:
        # Handle the error if the command is not found
        print(Fore.LIGHTRED_EX + 'Error: Command not found', e)
        clear_temp_files(user_id)
        return "Error"
    except Exception as e:
        # Handle any other exceptions
        print(Fore.LIGHTRED_EX + 'An unexpected error occurred:', e)
        clear_temp_files(user_id)
        return "Error"


def audio_decrypt(user_id):
    keys_file = open(f"./downloads/vdocipher/{user_id}/Temp/keys.json", 'r')
    data = keys_file.read()
    keys_file.close()
    keys = json.loads(data)

    print('*' * terminal_size)
    print()
    path = './cmakebuild/mp4decrypt --key ' + keys['audio_key'] + f' ./downloads/vdocipher/{user_id}/Temp/audio.mp4 ./downloads/vdocipher/{user_id}/Temp/tempdecrypted_audio.mp4'

    try:
        # Run a command and raise an exception if it fails
        result = subprocess.run([path], capture_output=True, text=True, check=True, shell=True)
        print("Audio Decryption Success!")
        print()
        print('*' * terminal_size)
        return "Done"
    except subprocess.CalledProcessError as e:
        # Handle the error if the command returns a non-zero exit code
        print(Fore.LIGHTRED_EX + 'Error: Command failed with return code', e.returncode)
        print(Fore.LIGHTRED_EX + 'Error Output:', e.stderr)
        clear_temp_files(user_id)
        return "Error"
    except FileNotFoundError as e:
        # Handle the error if the command is not found
        print(Fore.LIGHTRED_EX + 'Error: Command not found', e)
        clear_temp_files(user_id)
        return "Error"
    except Exception as e:
        # Handle any other exceptions
        print(Fore.LIGHTRED_EX + 'An unexpected error occurred:', e)
        clear_temp_files(user_id)
        return "Error"