import asyncio
import os
import subprocess
import shutil
import re

terminal_size = os.get_terminal_size().columns


def main(user_id, vdocipher_url):
    if os.path.exists(f'./downloads/vdocipher/{user_id}/Temp/') == False:
        shutil.rmtree(f'./downloads/vdocipher/{user_id}/Temp/')
        os.makedirs(f'./downloads/vdocipher/{user_id}/Temp/', exist_ok=True)


    if os.path.exists(f'./downloads/vdocipher/{user_id}/OUT/') == False:
        os.makedirs(f'./downloads/vdocipher/{user_id}/OUT/', exist_ok=True)

    if os.path.exists(f'./downloads/vdocipher/{user_id}/DRM/') == False:
        os.makedirs(f'./downloads/vdocipher/{user_id}/DRM/', exist_ok=True)