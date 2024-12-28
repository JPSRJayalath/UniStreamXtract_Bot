import json
import os
import time

import mega

# Log into MEGA
mega = mega.Mega()

def authorize(email, password):
    try:
        # Login
        m = mega.login(email, password)
        return 0
    except Exception as e:
        return e

def get_storage_info(user_id, m):

    # Get storage info
    storage_info = m.get_storage_space()

    # Extract total and used storage
    total_storage = storage_info['total']  # Total storage in bytes
    used_storage = storage_info['used']  # Used storage in bytes

    # Calculate available space
    available_storage = total_storage - used_storage

    # Convert to MB or GB for easier reading
    available_storage_mb = available_storage / (1024 * 1024)  # in MB
    available_storage_gb = available_storage / (1024 * 1024 * 1024)  # in GB

    print(f"[USER:{user_id}] Available Storage: {available_storage_gb:.2f} GB")

    return available_storage_gb

def file_upload(user_id, email, password, local_file_path):
    file_size = os.path.getsize(local_file_path)
    MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1GB

    m = mega.login(email, password)

    # Ensure storage info retrieval is handled asynchronously
    available_mega_space = get_storage_info(user_id, m)

    if file_size / MAX_FILE_SIZE < available_mega_space:
        custom_folder_path = '/Downloading Bot/'

        # Check if the custom folder exists in MEGA, create it if it doesn't
        folder = m.find(custom_folder_path)
        if folder is None:
            print(f"[USER:{user_id}] Folder '{custom_folder_path}' does not exist. Creating it...")
            folder = m.create_folder(custom_folder_path)

        folder = m.find(custom_folder_path)
        file = m.upload(local_file_path, folder[0])  # folder[0] is the folder ID
        print(f"[USER:{user_id}] File uploaded successfully to {custom_folder_path}")
        return 0

    else:
        print(f'[USER:{user_id}] Mega Drive Almost Full')
        return 999

def get_uploaded_file_public_link(user_id, email, password, filename):

    m = mega.login(email, password)

    # Define the path to your file in MEGA
    file_path_in_mega = f"/Downloading Bot/{filename}"  # Replace with your MEGA file path

    # Get the file and its link
    file = m.find(file_path_in_mega)
    if file:
        # Generate a public link
        public_link = str(m.get_link(file))
        print(public_link)
        return public_link
    else:
        print("File not found at specified path.")
        return 1