import asyncio
import hashlib
import json
import shutil
from urllib.parse import urlparse

import telethon as bot
import os
import sqlite3
import yt_dlp
from concurrent.futures import ThreadPoolExecutor
import contact_mega
import encrypted_video_downloader
import get_keys_for_decryption
import token_get
import vdocipher_dl
import btn_create
import upload_handling
import video_and_audio_decrypting_and_merge_video_and_audio
import yt_dl_help

with open('./config/config.json') as configs:
    bot_config = json.load(configs)

API_ID = bot_config['api_id']
API_HASH = bot_config['api_hash']
BOT_TOKEN = bot_config['bot_token']

robot = bot.TelegramClient('UniStreamXtract', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

if os.path.exists('./db') == False:
    os.mkdir('./db')

# Database setup
conn_users = sqlite3.connect('./db/bot_clients_details.db')
cursor = conn_users.cursor()

# Create users tables

# users table create
cursor.execute(
    """CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT NOT NULL, full_name TEXT NOT NULL, state TEXT NOT NULL)""")
conn_users.commit()

# details of mega accounts
cursor.execute(
    """CREATE TABLE IF NOT EXISTS mega (user_id INTEGER PRIMARY KEY, email TEXT NOT NULL, password TEXT NOT NULL)""")
conn_users.commit()

device_path = './device_file/device.wvd'

# Global dictionary to keep track of users in the process of providing a YouTube URL
active_requests = {}

# ThreadPoolExecutor for running blocking tasks in a separate thread
executor = ThreadPoolExecutor(max_workers=10)  # Set the number of workers for handling tasks
semaphore = asyncio.Semaphore(10)  # Set the number of uploading workers for handling tasks

# Offload the blocking task to the thread pool using run_in_executor
loop = asyncio.get_event_loop()


# Supported Functions for Bot Processors

# Check Username & Name is Changed
async def check_username_fullname_change(user_id, username, fullname):
    cursor.execute("SELECT username, full_name FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result[0] != username:
        if result[1] != fullname:
            cursor.execute("UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                           (username, fullname, user_id))
            conn_users.commit()
        else:
            cursor.execute("UPDATE users SET username = ? WHERE user_id = ?",
                           (username, user_id))
            conn_users.commit()
    else:
        return


async def saved_mega_acc_handle(user_id, password, option: int):
    if option == 0:
        try:
            # Execute the DELETE statement
            cursor.execute("DELETE FROM mega WHERE user_id = ?", (user_id,))
            conn_users.commit()  # Commit the transaction
            return 0
        except sqlite3.Error as e:
            return e

    else:
        try:
            # Execute the DELETE statement
            cursor.execute("UPDATE mega SET password = ? WHERE user_id = ?", (password, user_id))
            conn_users.commit()  # Commit the transaction
            return 0
        except sqlite3.Error as e:
            return e


# Check if user is in group
async def check_user_in_group(username_to_check):
    group_username = "@Dev_CodeNexis"  # Replace with the group or channel username

    try:
        group = await robot.get_entity(group_username)
        participants = await robot.get_participants(group)

        for participant in participants:
            if participant.username == username_to_check or participant.id == int(username_to_check):
                return "grp_in"
        return "not_grp"

    except Exception as e:
        return f"Error: {e}"


# Hasing passwords
async def hash_password_sha256(password: str) -> str:
    # Create a SHA-256 hash object
    sha256 = hashlib.sha256()

    # Encode the password and update the hash object
    sha256.update(password.encode('utf-8'))

    # Return the hex representation of the hash
    return sha256.hexdigest()


# User Registeration
async def user_register(user_id, username, full_name):
    if user_id == bot_config['owner_user_id']:  # Special case for VIP user
        cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, full_name, state)
        VALUES (?, ?, ?, ?)
        """, (user_id, username, full_name, 'vip'))
    else:  # Regular user
        cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, full_name, state)
        VALUES (?, ?, ?, ?)
        """, (user_id, username, full_name, 'user'))

    conn_users.commit()


async def saving_mega_details(user_id, email, password):
    cursor.execute("""
        INSERT OR IGNORE INTO mega (user_id, email, password)
        VALUES (?, ?, ?, ?)
        """, (user_id, email, password))


async def uploading_mega_process(event, user_id, callback_event, video_title, from_zip, zip_dir, arg):
    # Ensure active_requests is thread-safe or use a proper data structure to track user-specific states
    active_requests[user_id] = True

    # Database access needs to be handled properly in a multi-user environment
    cursor.execute("SELECT user_id FROM mega WHERE user_id=?",
                   (user_id,))
    mega_user_exists = cursor.fetchone() is not None

    if not mega_user_exists:
        await callback_event.edit(
            "Please provide a Mega Email. ⏳📧⚡")
        try:
            async with robot.conversation(event.sender_id,
                                          timeout=300) as conv:
                email_response = await conv.wait_event(
                    bot.events.NewMessage(
                        from_users=event.sender_id))
                email = email_response.raw_text
                # Delete the email message after capturing it
                await email_response.delete()

                await event.reply(
                    "Please provide a Password. ⏳🔑💻")
                password_response = await conv.wait_event(
                    bot.events.NewMessage(
                        from_users=event.sender_id), timeout=300)
                password = password_response.raw_text
                # Delete the password message after capturing it
                await password_response.delete()

                # Authenticate with Mega using a background task to avoid blocking the event loop
                mega_auth_result = await loop.run_in_executor(
                    None, contact_mega.authorize, email, password)

                if mega_auth_result == 0:
                    await robot.send_message(user_id,
                                             "Authentication Successful. Your credentials have been saved securely. ✅🔒💾")
                    password_hash = await hash_password_sha256(
                        password)

                    # Make sure to handle database access correctly for multi-user scenarios
                    cursor.execute(
                        """INSERT OR IGNORE INTO mega (user_id, email, password) VALUES (?, ?, ?)""",
                        (user_id, email, password_hash))
                    conn_users.commit()

                    # Use asyncio.to_thread for blocking tasks like zipping and uploading
                    await loop.run_in_executor(
                        None, upload_handling.zipping, user_id,
                        zip_dir,
                        video_title,
                        from_zip,
                    )

                    result_uploading = await asyncio.to_thread(
                        contact_mega.file_upload,
                        user_id,
                        email, password,
                        zip_dir + f'{video_title}.zip')

                    upload = await robot.send_message(user_id, "Uploading... ⬆️📤")

                    if result_uploading == 0:
                        message_uploaded = await upload.edit(
                            user_id, "File Uploaded ✅📁")
                        link = await loop.run_in_executor(
                            None,
                            contact_mega.get_uploaded_file_public_link,
                            user_id, email,
                            password, f'{video_title}.zip')

                        if link != 1:
                            await message_uploaded.reply(
                                f"Public link 🔗🌍: {link}")

                        else:
                            await message_uploaded.reply(
                                "Failed to get the link. ❌🔗")

                    elif result_uploading == 999:
                        await robot.send_message(user_id,
                                                 "Mega Drive is almost full. ⚠️💾")

                    else:
                        await robot.send_message(user_id,
                                                 "An error occurred during file upload. ❌📤")


                else:
                    await robot.send_message(user_id,
                                             "Authentication Failed. Please try again with /connect_mega_cloud. ❌🔑🌐")

        except asyncio.TimeoutError:
            await event.reply(
                "You took too long to respond. Please try again by typing /connect_mega_cloud. ⏳❌🔄")
            shutil.rmtree(from_zip)
            shutil.rmtree(zip_dir)

        finally:
            # Remove the user from active_requests once the process is done
            del active_requests[user_id]
    else:
        # Retrieve the saved email from the database
        cursor.execute(
            "SELECT email FROM mega WHERE user_id = ?",
            (user_id,))
        mega_acc_details = cursor.fetchone()

        if mega_acc_details:
            email_saved = mega_acc_details[0]
            await callback_event.edit(
                f"Please provide your Mega account password for the email 🔑📧: {email_saved}")

        try:
            async with robot.conversation(event.sender_id,
                                          timeout=300) as conv:
                password_response = await conv.wait_event(
                    bot.events.NewMessage(
                        from_users=event.sender_id), timeout=300)
                mega_password = password_response.raw_text
                # Delete the password message after capturing it
                await password_response.delete()

                password_hash = await hash_password_sha256(
                    mega_password)

                # Make sure the database query is done asynchronously or using proper locking
                cursor.execute(
                    "SELECT email, password FROM mega WHERE user_id = ?",
                    (user_id,))
                mega_acc_details = cursor.fetchone()

                if mega_acc_details and mega_acc_details[1] == password_hash:
                    await robot.send_message(user_id,
                                             "Password Matched ✅🔑")

                    # Authenticate with Mega
                    auth = await loop.run_in_executor(None,
                                                      contact_mega.authorize,
                                                      mega_acc_details[
                                                          0],
                                                      mega_password)

                    if auth == 0:
                        await robot.send_message(user_id,
                                                 "Authentication Successful. Uploading to Mega Cloud. ✅☁️📤")

                        # Use asyncio.to_thread for blocking tasks like zipping and uploading
                        await loop.run_in_executor(
                            None, upload_handling.zipping, user_id,
                            zip_dir,
                            video_title,
                            from_zip)

                        result_uploading = await asyncio.to_thread(
                            contact_mega.file_upload,
                            user_id,
                            mega_acc_details[0], mega_password,
                            zip_dir + f'{video_title}.zip')

                        if result_uploading == 0:
                            message_uploaded = await robot.send_message(
                                user_id, "File Uploaded")
                            link = await loop.run_in_executor(
                                None,
                                contact_mega.get_uploaded_file_public_link,
                                user_id, mega_acc_details[0],
                                mega_password, f'{video_title}.zip')

                            if link != 1:
                                await message_uploaded.reply(f"Public link 🔗🌍: {link}")
                            else:
                                await message_uploaded.reply("Failed to get the link. ❌🔗")
                        elif result_uploading == 999:
                            await robot.send_message(user_id, "Mega Drive is almost full. ⚠️💾")
                        else:
                            await robot.send_message(user_id, "An error occurred during file upload. ❌📤")
                    else:
                        await robot.send_message(user_id, "Re-authentication failed. Please try again. ❌🔑🔄")
                else:

                    await robot.send_message(user_id, "Password not matched. Please try again. ❌🔑🔄")

                    try:
                        # Wait for the user to send the password again
                        password_response = await conv.wait_event(
                            bot.events.NewMessage(
                                from_users=event.sender_id), timeout=300
                        )
                        mega_password = password_response.raw_text
                        # Delete the second password message
                        await password_response.delete()
                        password_hash = await hash_password_sha256(mega_password)

                        # Check if the hashed password matches
                        if mega_acc_details[1] == password_hash:
                            await robot.send_message(user_id, "Password Matched ✅🔑")

                            # Proceed with authentication
                            auth = await loop.run_in_executor(
                                None,
                                contact_mega.authorize,
                                mega_acc_details[0],
                                mega_password
                            )

                            if auth == 0:
                                await robot.send_message(user_id,
                                                         "Authentication Successful. Uploading to Mega Cloud. ✅☁️📤")

                                # Proceed with zipping and uploading
                                await loop.run_in_executor(
                                    None, upload_handling.zipping, user_id,
                                    zip_dir, video_title, from_zip
                                )

                                result_uploading = await asyncio.to_thread(
                                    contact_mega.file_upload,
                                    user_id,
                                    mega_acc_details[0], mega_password,
                                    zip_dir + f'{video_title}.zip'
                                )

                                if result_uploading == 0:
                                    message_uploaded = await robot.send_message(
                                        user_id, "File Uploaded ✅📁"
                                    )
                                    link = await loop.run_in_executor(
                                        None,
                                        contact_mega.get_uploaded_file_public_link,
                                        user_id, mega_acc_details[0],
                                        mega_password, f'{video_title}.zip'
                                    )

                                    if link != 1:
                                        await message_uploaded.reply(f"Public link 🔗🌍: {link}")
                                    else:
                                        await message_uploaded.reply("Failed to get the link. ❌🔗")
                                elif result_uploading == 999:
                                    await robot.send_message(user_id, "Mega Drive is almost full.  ⚠️💾")
                                else:
                                    await robot.send_message(user_id, "An error occurred during file upload. ❌📤")
                            else:
                                await robot.send_message(user_id, "Re-authentication failed. Please try again. ❌🔑🔄")
                    except asyncio.TimeoutError:
                        await event.reply("You took too long to respond. Please try again. ⏳❌🔄")

        except Exception as e:
            await robot.send_message(user_id, f"An error occurred ❌⚠️: {e}")
            shutil.rmtree(from_zip)
            shutil.rmtree(zip_dir)

        finally:
            # Remove the user from active_requests once the process is done
            del active_requests[user_id]


# Bot Process

# Handler for the /youtube command
async def youtube(event):
    user_id = event.sender_id
    # Check if the user has already used the option
    if active_requests.get(user_id):
        await event.reply("You are already in progress. Please wait until the current task is completed. ⏳🔄")
        return

    # Ask user for YouTube URL
    yt_link = await event.reply("Please provide a YouTube URL or type /cancel to exit. ⏳📹🔗")

    # Create a conversation with a timeout of 5 minutes
    async with robot.conversation(event.sender_id) as conv:
        active_requests[user_id] = True
        try:
            response = await conv.wait_event(
                bot.events.NewMessage(from_users=event.sender_id),
                timeout=300  # 5 minutes timeout
            )

            # Check for cancellation
            if response.raw_text.strip().lower() == "/cancel":
                await yt_link.edit("🚫 You have canceled the request. Exiting the YouTube process.")
                active_requests.pop(user_id, None)  # Safely remove the user from active requests
                return

            youtube_url = response.raw_text
            if youtube_url.startswith('http') and ('youtube.com' in youtube_url or 'youtu.be' in youtube_url):
                video_info = await loop.run_in_executor(executor, yt_dl_help.fetch_youtube_video_info,
                                                        youtube_url)

                if "error" in video_info:
                    await event.reply(f"Failed to fetch video details: {video_info['error']} ❌📹⚠️")
                else:
                    # Format the response
                    response_text = (
                        f"**Title:** {video_info['title']}\n"
                        f"**Uploader:** {video_info['uploader']}\n"
                        f"**Duration:** {video_info['duration']} seconds\n"
                        f"**URL:** [Watch on YouTube]({video_info['url']})\n"
                        f"**Thumbnail:** ![Thumbnail]({video_info['thumbnail']})\n"
                        f"**View Count:** {video_info['view_count']}\n"
                        f"**Like Count:** {video_info['like_count']}\n"
                        f"**Dislike Count:** {video_info['dislike_count']}\n"
                        f"**Category:** {', '.join(video_info['category']) if video_info['category'] else 'No'}\n"
                        f"**Channel URL:** [View YouTube Channel]({video_info['channel_url']})\n"
                        f"**Tags:** {', '.join(video_info['tags']) if video_info['tags'] else 'No'}\n"
                        f"**Is Live:** {'Yes' if video_info['is_live'] else 'No'}\n"
                        f"**Age Limit:** {video_info['age_limit']}\n"
                        f"**Playlist Title:** {video_info['playlist_title'] if video_info['playlist_title'] else 'No'}\n"
                        f"**Playlist URL:** {video_info['playlist_url'] if video_info['playlist_url'] else 'No'}\n"
                    )
                    await event.reply(response_text)
                    # Get Video Resolution & Bitrate with buttons
                    video_id = await asyncio.create_task(
                        btn_create.select_format(event, robot, video_info['formats'], 'mp4', 'vid'))
                    audio_id = await asyncio.create_task(
                        btn_create.select_format(event, robot, video_info['formats'], 'm4a', 'aud'))

                    # Download Video
                    yt_dl_respond = await loop.run_in_executor(executor, yt_dl_help.yt_dl, user_id, youtube_url,
                                                               audio_id, video_id)

                    if yt_dl_respond == 'Done':
                        if video_id == '0':
                            if os.path.exists(f'./downloads/yt/{user_id}/{video_info["title"]}.m4a') == True:

                                upload = await asyncio.create_task(
                                    upload_handling.send_file(user_id, BOT_TOKEN, semaphore,
                                                              f'./downloads/yt/{user_id}/',
                                                              f'{video_info["title"]}.m4a',
                                                              f'{video_info["title"]}', 'aud'))

                            else:

                                file_res, file_search_res = await upload_handling.search_file_name('.m4a',
                                                                  f'./downloads/yt/{user_id}/')
                                if file_search_res == "Done":
                                    upload = await asyncio.create_task(
                                        upload_handling.send_file(user_id, BOT_TOKEN, semaphore,
                                                                  f'./downloads/yt/{user_id}/',
                                                                  file_res,
                                                                  f'{video_info["title"]}', 'aud'))
                                else:
                                    await robot.send_message(user_id, "❌ File not found. ⚠️")
                                    return

                            if upload == 'Done':
                                await event.reply("Done")
                            elif upload == 201:
                                await robot.send_message(user_id, "Your video size is too large. ⚠️🎥📦")
                                buttons = [[bot.Button.inline('Mega', b'mega')]]
                                message = await event.respond('Choose one of the options: 📝🔘',
                                                              buttons=buttons)

                                # Listener for callback queries (button presses)
                                @robot.on(bot.events.CallbackQuery)
                                async def handle_button_click(callback_event):
                                    try:
                                        if callback_event.data == b'mega':
                                            await uploading_mega_process(event, user_id, callback_event,
                                                                         video_info['title'],
                                                                         f'./downloads/yt/{user_id}/',
                                                                         f'./downloads/yt/mega{user_id}/',
                                                                         'M')
                                    except Exception as e:
                                        await robot.send_message(user_id, f"Error: {e}")
                                    finally:
                                        # Remove the handler after processing
                                        robot.remove_event_handler(handle_button_click,
                                                                   bot.events.CallbackQuery)
                                        shutil.rmtree(f'./downloads/yt/{user_id}/')
                                        shutil.rmtree(f'./downloads/yt/mega{user_id}/')

                                # Ensure handler is added only once
                                robot.add_event_handler(handle_button_click, bot.events.CallbackQuery)

                            await event.reply(upload)
                        elif video_id == None or audio_id == None:
                            await robot.send_message(user_id,
                                                     "You took too long to select the video quality. Please try again by typing /youtube. ⏳❌🎥")
                            return
                        else:
                            if user_id == bot_config['owner_user_id']:
                                if os.path.exists(f'./downloads/yt/{user_id}/{video_info["title"]}.mp4') == True:

                                    upload = await asyncio.create_task(
                                        upload_handling.send_file(user_id, BOT_TOKEN, semaphore,
                                                                  f'./downloads/yt/{user_id}/',
                                                                  f'{video_info["title"]}.mp4',
                                                                  f'{video_info["title"]}', 'doc'))

                                else:

                                    file_res, file_search_res = await upload_handling.search_file_name('.mp4',
                                                                                                       f'./downloads/yt/{user_id}/')
                                    if file_search_res == "Done":
                                        upload = await asyncio.create_task(
                                            upload_handling.send_file(user_id, BOT_TOKEN, semaphore,
                                                                      f'./downloads/yt/{user_id}/',
                                                                      file_res,
                                                                      f'{video_info["title"]}', 'doc'))
                                    else:
                                        await robot.send_message(user_id, "❌ File not found. ⚠️")
                                        return
                                if upload == 'Done':
                                    await event.reply("Done")
                                elif upload == 201:
                                    await robot.send_message(user_id, "Your video size is too large. ⚠️🎥📦")
                                    buttons = [[bot.Button.inline('Mega', b'mega')]]
                                    message = await event.respond('Choose one of the options: 📝🔘',
                                                                  buttons=buttons)

                                    # Listener for callback queries (button presses)
                                    @robot.on(bot.events.CallbackQuery)
                                    async def handle_button_click(callback_event):
                                        try:
                                            if callback_event.data == b'mega':
                                                await uploading_mega_process(event, user_id, callback_event,
                                                                             video_info['title'],
                                                                             f'./downloads/yt/{user_id}/',
                                                                             f'./downloads/yt/mega{user_id}/',
                                                                             'M')
                                        except Exception as e:
                                            await robot.send_message(user_id, f"Error: {e}")
                                        finally:
                                            # Remove the handler after processing
                                            robot.remove_event_handler(handle_button_click,
                                                                       bot.events.CallbackQuery)
                                            shutil.rmtree(f'./downloads/yt/{user_id}/')
                                            shutil.rmtree(f'./downloads/yt/mega{user_id}/')

                                    # Ensure handler is added only once
                                    robot.add_event_handler(handle_button_click, bot.events.CallbackQuery)
                            else:
                                if os.path.exists(f'./downloads/yt/{user_id}/{video_info["title"]}.mp4') == True:

                                    upload = await asyncio.create_task(
                                        upload_handling.send_file(user_id, BOT_TOKEN, semaphore,
                                                                  f'./downloads/yt/{user_id}/',
                                                                  f'{video_info["title"]}.mp4',
                                                                  f'{video_info["title"]}', 'vid'))

                                else:

                                    file_res, file_search_res = await upload_handling.search_file_name('.mp4',
                                                                                                       f'./downloads/yt/{user_id}/')
                                    if file_search_res == "Done":
                                        upload = await asyncio.create_task(
                                            upload_handling.send_file(user_id, BOT_TOKEN, semaphore,
                                                                      f'./downloads/yt/{user_id}/',
                                                                      file_res,
                                                                      f'{video_info["title"]}', 'vid'))
                                    else:
                                        await robot.send_message(user_id, "❌ File not found. ⚠️")
                                        return
                                if upload == 'Done':
                                    await event.reply("Done")
                                elif upload == 201:
                                    await robot.send_message(user_id, "Your video size is too large. ⚠️🎥📦")
                                    buttons = [[bot.Button.inline('Mega', b'mega')]]
                                    message = await event.respond('Choose one of the options: 📝🔘',
                                                                  buttons=buttons)

                                    # Listener for callback queries (button presses)
                                    @robot.on(bot.events.CallbackQuery)
                                    async def handle_button_click(callback_event):
                                        try:
                                            if callback_event.data == b'mega':
                                                await uploading_mega_process(event, user_id, callback_event,
                                                                             video_info['title'],
                                                                             f'./downloads/yt/{user_id}/',
                                                                             f'./downloads/yt/mega{user_id}/',
                                                                             'M')

                                        except Exception as e:
                                            await robot.send_message(user_id, f"Error: {e}")
                                        finally:
                                            # Remove the handler after processing
                                            robot.remove_event_handler(handle_button_click,
                                                                       bot.events.CallbackQuery)
                                            shutil.rmtree(f'./downloads/yt/{user_id}/')
                                            shutil.rmtree(f'./downloads/yt/mega{user_id}/')

                                    # Ensure handler is added only once
                                    robot.add_event_handler(handle_button_click, bot.events.CallbackQuery)

                    else:
                        await robot.send_message(user_id, yt_dl_respond)

            else:
                await event.reply("The URL you provided is not a valid YouTube URL. ❌🔗📹")
                return

        except asyncio.TimeoutError:
            await event.reply(
                "You took too long to provide a YouTube URL. Please try again by typing /youtube. ⏳❌🔗")
            return
        finally:
            active_requests.pop(user_id, None)  # Safely remove the user from active requests after completion
            return


# Change User State
async def change_user_state(event):
    user_id = event.sender_id

    if event.sender_id != bot_config['owner_user_id']:  # Replace with your admin user ID
        await event.reply("You are not authorized to change user state. ❌🔒")
        return

    # Check if the user has already used the option
    if active_requests.get(user_id, False):
        await event.reply("You are already using me. 🔄🤖")
        return

    user_id_msg = await robot.send_message(event.sender_id, "Send User ID 🆔📲:")
    active_requests[user_id] = True
    chosen_button = None
    user_response = {"text": None}

    # Create a custom asyncio event to wait for the user's response
    response_event = asyncio.Event()

    # Event handler for the user's response (user ID input)
    @robot.on(bot.events.NewMessage(from_users=user_id))
    async def handle_response(response):
        # Save the response text (user ID input)
        user_response["text"] = response.text
        response_event.set()  # Set the event so we can proceed
        # Remove this event handler after capturing the response
        robot.remove_event_handler(handle_response, bot.events.NewMessage)

    try:
        # Wait for the user's response within the timeout period
        await asyncio.wait_for(response_event.wait(), timeout=120)

        user_input_id = user_response["text"]

        # Check if the input is valid (numeric user ID)
        if user_input_id.strip().lower() == "/cancel":
            await user_id_msg.edit("🚫 Request cancelled. You have exited the user state change.")
            # Ensure the user_id exists before trying to remove from active_requests
            active_requests.pop(user_id, None)
            return

        if not user_input_id.isdigit():
            await user_id_msg.edit("Invalid input. Please provide a valid user ID. ❌🆔")
            return

        user_input_id = int(user_input_id)

        # Prepare the inline buttons
        buttons = [
            [bot.Button.inline('V.VIP', b'v.vip')],
            [bot.Button.inline('E.VIP', b'e.vip')],
            [bot.Button.inline('VIP', b'vip')],
            [bot.Button.inline('User', b'user')]
        ]
        # Send the message with buttons to choose state
        message = await event.respond('Choose one of the options: 📝🔘', buttons=buttons)

        # Now, we set up a listener for callback queries (button presses)
        @robot.on(bot.events.CallbackQuery)
        async def handle_button_click(callback_event):
            nonlocal chosen_button

            # Check if the user clicked on 'V.VIP', 'E.VIP', 'VIP' or 'User'
            if callback_event.data == b'v.vip':
                chosen_button = 'v.vip'
            elif callback_event.data == b'e.vip':
                chosen_button = 'e.vip'
            elif callback_event.data == b'vip':
                chosen_button = 'vip'
            else:
                chosen_button = 'user'

            cursor.execute("SELECT full_name, state FROM users WHERE user_id = ?", (user_input_id,))
            result = cursor.fetchone()

            if result[1] != 'user':
                if chosen_button == 'user':
                    msg = f"Hello {result[0]}. Your state has been downgraded to {chosen_button} by the bot owner. 👋🔻"
            else:
                msg = f"Hello {result[0]}. Your state has been upgraded to {chosen_button} by the bot owner. 👋🚀🔧🤖"

            # Edit the message and remove the buttons by using reply_markup=None (correct method)
            if result[1] != 'user':
                if chosen_button == 'user':
                    await callback_event.edit('Your State Downgrade VIP to USER ⚠️🔽')
            else:
                await callback_event.edit('Your State Upgrade USER to VIP 🎉👑')

            # Update the user's state in the database
            cursor.execute("UPDATE users SET state = ? WHERE user_id = ?", (chosen_button, user_input_id))
            conn_users.commit()

            # Send confirmation to the user whose state was changed
            await event.reply("User State Change Successful ✅🔄")
            await robot.send_message(user_input_id, msg)

            # Remove the handler after the callback is processed
            robot.remove_event_handler(handle_button_click, bot.events.CallbackQuery)

    except asyncio.TimeoutError:
        # If the user doesn't respond within the timeout period, notify them
        await user_id_msg.edit("You took too long to respond. Please try again. ⏳❌🔄")
        return
    except Exception as e:
        # Handle any other exceptions and print the error
        await user_id_msg.edit(f"An error occurred: {str(e)} ❌⚠️")
        return
    finally:
        # Safely remove the user from active_requests if they exist
        active_requests.pop(user_id, None)
        return


# VIP
async def vip(event):
    user_id = event.sender_id
    cursor.execute("SELECT state FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result[0] == 'vip':
        vip_panel = await event.reply(
            '''Available Commands :-\n/vdocipher - Download Video From Vdocipher Server 📹🔽\n/edumix - Download Video From Databoxtech Server 🎓📥\n/get_stock - Download All Stocked Videos from the Server 📂📥\n\nAvailable Extensions:-\n/license_catcher_for_vdocipher 🔑💻''')
        await asyncio.sleep(120)
        await vip_panel.delete()
        await event.delete()

    elif result[0] == 'v.vip':
        vip_panel = await event.reply(
            '''Available Commands :-\n/vdocipher - Download Video From Vdocipher Server 📹🔽\n\nAvailable Extensions:-\n/license_catcher_for_vdocipher 🔑💻''')
        await asyncio.sleep(120)
        await vip_panel.delete()
        await event.delete()
    else:
        await event.reply(
            f"You don't have permission because you are not a VIP user. Your current state is: {result[0]} ❌🔒👤")


# Broadcast with conversation and cancel functionality
async def broadcast(event):
    user_id = event.sender_id

    if user_id == bot_config['owner_user_id']:  # Ensure that only the owner can send the broadcast
        broadcast_message = await event.respond(
            "✨ Please send the message you want to broadcast to all users, or type /cancel to exit. ✨")

        # Create a conversation with a timeout of 5 minutes
        async with robot.conversation(event.sender_id) as conv:
            active_requests[user_id] = True  # Mark the owner as in a conversation
            try:
                # Wait for the owner's response, allow for cancellation
                response = await conv.wait_event(
                    bot.events.NewMessage(from_users=user_id),
                    timeout=300  # 5 minutes timeout
                )

                # Check for cancellation command
                if response.raw_text.strip().lower() == "/cancel":
                    await broadcast_message.edit("🚫 Broadcast cancelled. Exiting the broadcast process.")
                    return

                # Fetch all user IDs from the 'users' table
                cursor.execute("SELECT user_id FROM users")
                saved_user_ids = [row[0] for row in cursor.fetchall()]  # Get all user IDs into a list
                conn_users.close()

                # Broadcast the message to all saved user IDs
                for user_id in saved_user_ids:
                    try:
                        await robot.send_message(user_id, f"📢 {response.text} 📢")
                        print(f"Message sent to {user_id}")
                    except Exception as e:
                        print(f"Failed to send message to {user_id}: {e}")

                # Notify the owner that the broadcast is complete
                await event.respond("✅ Broadcast message sent to all users! ✅")

            except asyncio.TimeoutError:
                await event.respond("⏳ You took too long to send the broadcast message. Process cancelled. ⏳")
            except sqlite3.Error as e:
                print(f"SQLite error: {e}")
                await event.respond("⚠️ An error occurred while accessing the database. Please try again. ⚠️")
            finally:
                # Safely clean up the active_requests dictionary
                active_requests.pop(user_id, None)  # Removes the key if it exists, prevents KeyError

    else:
        # If the sender is not the owner, deny permission
        await event.respond("❌ Permission Denied. Only the owner can use this command. ❌")


# Admin_panel
async def admin_panel(event):
    user_id = event.sender_id

    # Check if the user is an admin
    if user_id != bot_config['owner_user_id']:
        await event.reply("**Access Denied** ❌🔒")
        return

    # Mark the user as having an active request
    active_requests[user_id] = True

    try:
        # Ask for the secret code
        ask_secret_code = await event.reply(
            "Please enter the secret code to access the admin panel or type /cancel to exit. 🔑🛠️"
        )

        # Define a filter for capturing the user's next message
        def user_filter(e):
            return e.sender_id == user_id and e.chat_id == event.chat_id

        # Use an event handler to wait for the user's next message
        @event.client.on(bot.events.NewMessage(func=user_filter))
        async def secret_code_listener(response_event):
            # Remove the listener after capturing the message
            event.client.remove_event_handler(secret_code_listener, bot.events.NewMessage)

            # Function to delete the message asynchronously
            async def delete_message(message):
                try:
                    await message.delete()
                except Exception as e:
                    # Log failure but don't block the main flow
                    await event.reply(f"Failed to delete the message: {e} ❌🗑️⚠️")

            # Create a task for deleting the response message without blocking other operations
            asyncio.create_task(delete_message(response_event.message))

            # Check for cancellation
            if response_event.text.strip().lower() == "/cancel":
                active_requests.pop(user_id, None)
                await ask_secret_code.edit("🚫 Request cancelled. You have exited the admin panel.")
                return

            # Verify the secret code
            if response_event.text == bot_config['secret_code']:
                # Show the admin panel for 30 seconds
                active_requests.pop(user_id, None)

                admin_panel_message = await ask_secret_code.edit(
                    "🎉 **Welcome to the Admin Panel!** 🎉\n\n"
                    "📋 Please choose an action:\n\n"
                    "1️⃣ /change_user_state - 🔄 Change user state (VIP to User or User to VIP)\n"
                    "2️⃣ /broadcast - 📢 Broadcast a message to all registered users\n"
                    "3️⃣ /list_users - 🧑‍🤝‍🧑 Show the list of all registered users\n"
                    "4️⃣ /send_msg_for_grp - 📨 Send a message to a group\n"
                    "5️⃣ /send_msg_for_client - 📩 Send a message to a specific client",
                    parse_mode='Markdown'
                )
                await asyncio.sleep(30)
                await admin_panel_message.delete()
            else:
                # Notify the user if the code is incorrect
                await event.reply("❌ Incorrect code. Access denied. ❌")

        # Wait for the listener to finish, with a timeout of 30 seconds
        await asyncio.sleep(30)  # Timeout in case no response is received
    except Exception as e:
        await event.reply(f"❌ An error occurred: {e} ❌")
    finally:
        # Delete the original command message asynchronously without blocking
        async def delete_initial_message():
            try:
                await event.delete()
            except:
                pass

        # Create a task for deleting the initial message asynchronously
        asyncio.create_task(delete_initial_message())


# Help
async def help(event):
    user_id = event.sender_id
    username = event.sender.username or 'No username'
    full_name = event.sender.first_name + (f" {event.sender.last_name}" if event.sender.last_name else "")
    await event.reply('''
        /start\n🔹 **Purpose:** This command starts the bot. It initializes the bot and sends a welcome message or sets up the first interactions with the user.\n🔹 **Usage:** When the user sends /start, the bot will reply with a greeting and basic instructions on how to use the bot.\n\n
        /help\n🔹 **Purpose:** This command provides users with a list of available commands and an explanation of what they do.\n🔹 **Usage:** When users send /help, the bot replies with a list of commands and their descriptions so users know how to interact with the bot.\n\n
        /youtube\n🔹 **Purpose:** This command allows users to download YouTube videos. It will prompt the user to select the quality (like 720p, 1080p, etc.) they want for the video.\n🔹 **Usage:** The user sends /youtube, followed by a YouTube video URL. The bot will ask for the video quality and then start the download process based on the user’s selection.\n\n
        /vip\n🔹 **Purpose:** This command is intended for VIP users. It unlocks exclusive features that are only available to users who are marked as VIP.\n🔹 **Usage:** When a VIP user sends /vip, they may gain access to special functionalities, content, or privileges that regular users don’t have.\n\n
        /get_my_id\n🔹 **Purpose:** This command allows users to get their Telegram user ID.\n🔹 **Usage:** When users send /get_my_id, the bot responds with the user’s unique Telegram ID, which is often needed for support, configuration, or custom services.\n\n
        /contact_admin\n🔹 **Purpose:** This command provides users a way to contact the bot's admin.\n🔹 **Usage:** When users send /contact_admin, the bot either provides an admin’s contact information or forwards the user’s message to the admin for direct communication.\n\n
        /connect_mega_cloud\n🔹 **Purpose:** This command allows users to link their Mega cloud drive account to the bot.\n🔹 **Usage:** When the user sends /connect_mega_cloud, they will be prompted to authenticate or provide connection details for their Mega account. Once connected, they can upload or download files from their Mega cloud drive.\n\n
        /about_me\n🔹 **Purpose:** This command provides detailed information about the bot and its features.\n🔹 **Usage:** When users send /about_me, the bot will respond with a comprehensive description of its functionalities, commands, and security features.\n\n
        🔒 **Security Note:** When you send a password, it is not stored in plain text. It is securely hashed using SHA-256 to ensure your data remains safe.\n\n
        💡 **Note:** The bot **only uploads to Mega** and currently does not support other cloud services.

    ''')


# Get Client ID
async def get_my_id(event):
    user_id = event.sender_id
    await event.reply(f"🆔 **Your User ID:** `{user_id}`", parse_mode='markdown')


async def contact_admin(event):
    user_id = event.sender_id
    active_requests[user_id] = True  # Mark the user as active
    username = event.sender.username or 'No username'
    full_name = event.sender.first_name + (f" {event.sender.last_name}" if event.sender.last_name else "")

    # Prompt the user to send a message
    await event.reply("📤 **Send the message** 📨 (Type /cancel to cancel)")
    user_response = {"text": None}
    response_event = asyncio.Event()

    # Handler for new messages from the user
    @robot.on(bot.events.NewMessage(from_users=user_id))
    async def handle_response(response):
        # Check if the user's message is a reply to the bot's message
        if response.is_reply and response.reply_to_msg_id == event.message.id:
            await response.reply("✅ **Your message has been reported.** 📩")
            return

        # Handle cancellation
        if response.raw_text.strip() == "/cancel":
            await response.reply("❌ **Your report submission has been canceled.** 😊")
            response_event.set()
            robot.remove_event_handler(handle_response, bot.events.NewMessage)
            return

        # Save user response
        user_response["text"] = response.text
        response_event.set()

        # Reply with the user's sent message
        await response.reply(f"✅ **Your message has been received:**\n{response.text}")
        robot.remove_event_handler(handle_response, bot.events.NewMessage)

    try:
        # Wait for user response with a timeout
        await asyncio.wait_for(response_event.wait(), timeout=600)
        user_report_msg = user_response["text"]

        if user_report_msg is not None:
            client_report_grp = bot_config['reports_channel']
            # Send report to the admin group
            await robot.send_message(
                client_report_grp,
                f"📩 **New User Report**\n\n👤 **User ID:** `{user_id}`\n👤 **Username:** @{username}\n👤 **Full Name:** {full_name}\n\n📝 **Report:**\n`{user_report_msg}`"
            )
            # No need to reply here, the reply was already sent in handle_response

    except asyncio.TimeoutError:
        await event.reply("⏳ **You took too long to respond with your report.** Please try again. 🔄")

    finally:
        del active_requests[user_id]  # Cleanup after completion
    return


async def send_msg_for_client(event):
    user_id = event.sender_id

    if user_id != bot_config['owner_user_id']:
        await event.reply("🚫 You don't have permission to access the command. 🔒")
        return

    check_user = await check_user_in_group(user_id)
    username = event.sender.username or 'No username'
    full_name = event.sender.first_name + (f" {event.sender.last_name}" if event.sender.last_name else "")
    await check_username_fullname_change(user_id, username, full_name)

    active_requests[user_id] = True  # Mark the request as active
    awaiting_message = await event.reply("🆔 **Client ID:**\n\nType /cancel to abort the operation.")

    # Start a conversation with the user and wait for client_id response
    async with robot.conversation(event.sender_id, timeout=600) as conv:
        # Wait for the client_id message from the owner
        client_id_response = await conv.wait_event(bot.events.NewMessage(from_users=event.sender_id))

        # Check for cancellation
        if client_id_response.raw_text.strip().lower() == '/cancel':
            await awaiting_message.edit("🚫 You have canceled the operation.")
            del active_requests[user_id]  # Clean up active requests
            return

        try:
            # Parse the client_id as an integer
            client_id = int(client_id_response.raw_text.strip())
        except ValueError:
            await event.reply("❌ Invalid client ID. Please try again. 🔄")
            del active_requests[user_id]  # Clean up active requests
            return

        # Prompt user for the message to send to the client
        await event.reply("📩 Message for Client:\n\nType /cancel to abort the operation.")

        # Wait for the actual message to send to the client
        message_for_client = await conv.wait_event(bot.events.NewMessage(from_users=event.sender_id), timeout=600)

        # Check for cancellation
        if message_for_client.raw_text.strip().lower() == '/cancel':
            await conv.send_message("🚫 You have canceled the operation.")
            del active_requests[user_id]  # Clean up active requests
            return

        message = message_for_client.raw_text.strip()

        # Fetch the client's full name from the database
        cursor.execute("SELECT full_name FROM users WHERE user_id = ?", (client_id,))
        result = cursor.fetchone()

        if result is None:
            await event.reply(f"❌ Error: No user found with ID {client_id}. Please check the ID and try again. 🔍")
            del active_requests[user_id]  # Clean up active requests
            return

        # Send the message to the client
        await robot.send_message(client_id, f"👋 Hi {result[0]}!\n\n📩 {message}")

        # Notify the bot owner that the message has been sent
        await robot.send_message(user_id, f"✅ Your message has been successfully sent to {result[0]}. 📤")

    # Clean up the active request after processing
    del active_requests[user_id]


# Send message for group
async def send_msg_for_grp(event):
    user_id = event.sender_id

    active_requests[user_id] = True  # Mark the user as using the bot

    if user_id == bot_config['owner_user_id']:
        grp_msg = await event.reply("📤 Send the message 📨 Or type /cancel to cancel the process.")
        user_response = {"text": None}
        response_event = asyncio.Event()

        @robot.on(bot.events.NewMessage(from_users=user_id))
        async def handle_response(response):
            # If the user sends '/cancel', cancel the process
            if response.text.strip().lower() == '/cancel':
                await grp_msg.edit("🚫 You have canceled the message sending process.")
                active_requests.pop(user_id, None)  # Remove the user from active requests
                response_event.set()
                return

            user_response["text"] = response.text
            response_event.set()
            robot.remove_event_handler(handle_response, bot.events.NewMessage)

        try:
            await asyncio.wait_for(response_event.wait(), timeout=300)  # Wait for response with timeout
            if user_response["text"]:  # If the user sent a valid message
                msg_for_grp = user_response["text"]
                group = bot_config['bot_channel']
                await robot.send_message(group, msg_for_grp)  # Send message to the group
                await robot.send_message(user_id, "✅ Your message has been sent to the group. 📤")
            else:
                await robot.send_message(user_id, "⚠️ No valid message was provided.")

        except asyncio.TimeoutError:
            await grp_msg.edit("⏳ You took too long to respond and send the message. Please try again. 🔄")
        finally:
            # Safely clean up the active_requests dictionary
            active_requests.pop(user_id, None)  # Removes the key if it exists, prevents KeyError
            return

    else:
        await event.reply("🚫 You don't have permission to use this command! 🔒")


# List users
async def list_users(event):
    if event.sender_id != bot_config['owner_user_id']:  # Replace with your admin user ID
        await event.reply("🚫 You are not authorized to view the user list. 🔒")
        return

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    if not users:
        await event.reply("❌ No users found. 🔍")
        return

    user_list = "\n".join(
    [f"`{i}. {u[0]}` - {u[3]} - {u[2]} (@{u[1]})" for i, u in enumerate(users, start=1) if u[3] == 'user']
    )
    vip_list = "\n".join(
        [f"`{i}. {u[0]}` - {u[3]} - {u[2]} (@{u[1]})" for i, u in enumerate(users, start=1) if u[3] != 'user']
    )

    # Provide default messages if lists are empty
    if not vip_list:
        vip_list = "❌ No VIP users found. 🔍"
    if not user_list:
        user_list = "❌ No regular users found. 🔍"

    # Send the message
    await event.reply(
        f"📝 **Registered Users:**\n\n"
        f"**VIP Users**\n{vip_list}\n\n"
        f"**Other Users**\n{user_list}"
    )


async def vdocipher(event):
    user_id = event.sender_id

    # Fetch user's state from the database
    cursor.execute("SELECT state FROM users WHERE user_id = ?", (user_id,))
    user_state = cursor.fetchone()

    if user_state[0] not in ['vip', 'v.vip']:
        await event.reply(f"🚫 You don't have permission. Your current state is: {user_state[0]} 🔒")
        del active_requests[user_id]
        return

    # Step 1: Request VdoCipher token URL
    ask_token = await event.reply("📩 Please provide the VdoCipher token URL. 🔑")
    try:
        async with robot.conversation(user_id, timeout=300) as conv:
            active_requests[user_id] = True
            response = await conv.wait_event(bot.events.NewMessage(from_users=user_id))

            # Check for cancellation
            if response.raw_text.strip().lower() == "/cancel":
                await ask_token.edit("❌ Process canceled by user. 🛑")
                del active_requests[user_id]
                return

            token_url = response.raw_text.strip()

        if not token_url:
            await event.reply("❌ Invalid URL. Please try again. 🔄")
            del active_requests[user_id]
            return

    except asyncio.TimeoutError:
        await event.reply("⏳ You took too long to provide the URL. Please try again by typing /vdocipher. 🔄")
        del active_requests[user_id]
        raise

    # Step 2: Process the VdoCipher token
    try:
        # Use run_in_executor for synchronous processing
        token = await loop.run_in_executor(executor, token_get.token, token_url, user_id)
        keys_status, mpd_url = await loop.run_in_executor(executor, get_keys_for_decryption.main, device_path, token,
                                                          user_id)

        if keys_status != "Done":
            await event.reply("❌ Failed to retrieve decryption keys. 🔑")
            del active_requests[user_id]
            return

        await event.reply("✅ Decryption keys retrieved successfully. 🔑 Proceeding with the download... 📥")
    except Exception as e:
        await event.reply(f"❌ Error processing token: {e} ⚠️")
        del active_requests[user_id]
        raise

    # Step 3: Download encrypted video and audio
    try:
        download_status = await loop.run_in_executor(executor, encrypted_video_downloader.main, mpd_url, user_id)
        if download_status != "Done":
            await event.reply("❌ Failed to download encrypted video/audio. 🎬🔒")
            del active_requests[user_id]
            return

        await event.reply("✅ Encrypted video and audio downloaded successfully. 🎥🔊")
    except Exception as e:
        await event.reply(f"❌ Error during download: {e} ⬇️⚠️")
        del active_requests[user_id]
        raise

    # Step 4: Decrypt audio and video
    try:
        audio_status = await loop.run_in_executor(executor,
                                                  video_and_audio_decrypting_and_merge_video_and_audio.audio_decrypt,
                                                  user_id)
        if audio_status != "Done":
            await event.reply("❌ Audio decryption failed. 🎧🔒")
            del active_requests[user_id]
            return

        video_status = await loop.run_in_executor(executor,
                                                  video_and_audio_decrypting_and_merge_video_and_audio.video_decrypt,
                                                  user_id)
        if video_status != "Done":
            await event.reply("❌ Video decryption failed. 🎬🔒")
            del active_requests[user_id]
            return

        await event.reply("✅ Audio and video decryption successful. 🎧🎬")
    except Exception as e:
        await event.reply(f"❌ Error during decryption: {e} 🔓⚠️")
        del active_requests[user_id]
        raise

    # Step 5: Ask for video title and merge audio/video
    ask_title = await event.reply("📩 Please provide a title for the video. 🎥")
    try:
        async with robot.conversation(user_id, timeout=300) as conv:
            response = await conv.wait_event(bot.events.NewMessage(from_users=user_id))

            # Check for cancellation
            if response.raw_text.strip().lower() == "/cancel":
                await ask_title.edit("❌ Process canceled by user. 🛑")
                shutil.rmtree(f'./downloads/vdocipher/{user_id}/')
                del active_requests[user_id]
                return

            video_title = response.raw_text.strip()

        if not video_title:
            await event.reply("❌ Invalid title. Please try again. 🔄")
            del active_requests[user_id]
            return

        merge_status = await loop.run_in_executor(executor,
                                                  video_and_audio_decrypting_and_merge_video_and_audio.audio_video_merge,
                                                  f'"{video_title}"', user_id)
        if merge_status != "Done":
            await event.reply("❌ Merging audio and video failed. 🎧🎬⚠️")
            del active_requests[user_id]
            return

        await event.reply("✅ Audio and video merged successfully. 🎧🎬✨")
    except asyncio.TimeoutError:
        await event.reply("⏳ You took too long to provide the title. Please try again by typing /vdocipher. 🔄")
        del active_requests[user_id]
        raise
    except Exception as e:
        await event.reply(f"❌ Error during merge: {e} ⚠️🔄")
        del active_requests[user_id]
        raise

    # Step 6: Upload the decrypted video
    try:
        await robot.send_message(user_id, "📤 Uploading the decrypted video... 🎬🔓")
        # upload_status = await loop.run_in_executor(executor, upload_handling.send_file_drm, user_id, BOT_TOKEN, semaphore, video_title, 'doc')
        upload_status = await upload_handling.send_file_drm(user_id, BOT_TOKEN, semaphore, video_title, 'doc')
        if upload_status == "Done":
            await event.reply("✅ Your decrypted video has been uploaded successfully. 🎬🔓📤")
        elif upload_status == 201:
            await robot.send_message(user_id, "❌ Your video size is too large. 📏🎥")
            buttons = [[bot.Button.inline('☁️ Upload Mega Drive 🌐', b'mega')]]
            message = await event.respond('⚡ Choose one of the options: 📝', buttons=buttons)

            # Listener for callback queries (button presses)
            @robot.on(bot.events.CallbackQuery)
            async def handle_button_click(callback_event):
                try:
                    if callback_event.data == b'mega':
                        await uploading_mega_process(event, user_id, callback_event,
                                                     video_title, f'./downloads/vdocipher/{user_id}/OUT/',
                                                     f'./downloads/vdocipher/{user_id}/DRM/', 'D')
                except Exception as e:
                    await robot.send_message(user_id, f"Error: {e}")
                finally:
                    # Remove the handler after processing
                    robot.remove_event_handler(handle_button_click,
                                               bot.events.CallbackQuery)
                    shutil.rmtree(f'./downloads/vdocipher/{user_id}/')

            # Ensure handler is added only once
            robot.add_event_handler(handle_button_click, bot.events.CallbackQuery)

    except Exception as e:
        await event.reply(f"❌ Error during upload: {e} ⚠️🔄")
        raise
    finally:
        # Clean up active request
        del active_requests[user_id]


async def about_me(event):
    user_id = event.sender_id

    await robot.send_message(user_id, '''About @UniStreamXtract_bot\n
        \n
        👨‍💻 Powered by: CodeNexis Team\n
        🐍 Programmed Language: Python\n
        📚 Main Library: Telethon (for bot operations)\n
        📝 Bot Name: UniStreamXtract\n
        🔧 Bot Version: 1.0\n
        💻 Hosted on: My private remote computer\n
        \n
        Key Features:\n
        - ⚡ Fast Processing: Optimized for speed and efficiency\n
        - 🔒 Secure & Reliable: Your data is handled securely with top-grade protocols\n
        - 🛠 Easy-to-Use Commands: Intuitive interface for smooth user experience\n
        - 🔄 Constant Updates: We're always adding new features and improving the bot\n
        - 👥 Multi-User Handling: Supports multiple users simultaneously with smooth operation for each\n
        \n
        About the Developer:\n
        - UniStreamXtract: Created and maintained by the CodeNexis Team, dedicated to making your file management easy and efficient.\n
        - Available 24/7: Hosted on a private, secure remote server to ensure constant availability.\n
        \n
        We appreciate your use of @UniStreamXtract_bot. Expect even more features coming soon! Stay tuned.\n

    ''')


#  - 🗂 File Splitting & Merging: Handle large files seamlessly\n


async def connect_mega_cloud(event):
    user_id = event.sender_id

    cursor.execute("SELECT user_id FROM mega WHERE user_id=?", (user_id,))
    mega_user_exists = cursor.fetchone() is not None
    active_requests[user_id] = True

    if not mega_user_exists:
        # Prompt user for Mega Email
        ask_email = await event.reply("📩 Please provide a Mega email. ☁️(Type /cancel to cancel)")

        try:
            async with robot.conversation(event.sender_id, timeout=300) as conv:
                # Capture the email
                response = await conv.wait_event(bot.events.NewMessage(from_users=event.sender_id))

                # Check for cancellation
                if response.raw_text.strip().lower() == "/cancel":
                    await ask_email.edit("❌ Process canceled by user. 🛑")
                    active_requests.pop(user_id, None)  # Safely remove from active_requests
                    return

                email = response.raw_text

                # Delete the email message
                try:
                    await response.delete()
                except Exception as e:
                    await event.reply(f"❌ Failed to delete the email message: {e} ✉️⚠️")

                # Prompt user for Mega Password
                ask_password = await event.reply("🔐 Please provide a password. 📝(Type /cancel to cancel)")
                password_response = await conv.wait_event(bot.events.NewMessage(from_users=event.sender_id))

                # Check for cancellation
                if password_response.raw_text.strip().lower() == "/cancel":
                    await ask_password.edit("❌ Process canceled by user. 🛑")
                    active_requests.pop(user_id, None)  # Safely remove from active_requests
                    return

                # Capture the password
                password = password_response.raw_text

                # Delete the password message
                try:
                    await password_response.delete()
                except Exception as e:
                    await event.reply(f"❌ Failed to delete the password message: {e} 🔒⚠️")

                # Authenticate with Mega
                mega_auth_result = await loop.run_in_executor(None, contact_mega.authorize, email, password)
                if mega_auth_result == 0:
                    await robot.send_message(user_id,
                                             "✅ Authentication Success. Your email and password have been saved securely. 🔐📧")
                    password_hash = await hash_password_sha256(password)
                    cursor.execute("""INSERT OR IGNORE INTO mega (user_id, email, password) VALUES (?, ?, ?)""",
                                   (user_id, email, password_hash))
                    conn_users.commit()
                else:
                    await robot.send_message(user_id,
                                             "❌ Authentication Failed. Please try again with /connect_mega_cloud. 🔑⚠️")
        except asyncio.TimeoutError:
            await event.reply("⏳ You took too long to respond. Please try again by typing /connect_mega_cloud. 🔄")
        finally:
            # Safely remove the user from active_requests if it's present
            active_requests.pop(user_id, None)


    else:
        # Display options to the user
        buttons = [
            [bot.Button.inline('🗑️ Delete Mega Account ☁️', b'delete')],
            [bot.Button.inline('🔑 Change Password 📝', b'change')]
        ]
        message = await event.respond("⚡ Choose one of the options: 📝", buttons=buttons)

        @robot.on(bot.events.CallbackQuery)
        async def handle_button_click(callback_event):
            if callback_event.data == b'delete':
                await handle_delete_account(callback_event, user_id)
                # Clean up active request
                del active_requests[user_id]
            elif callback_event.data == b'change':
                await handle_change_password(callback_event, user_id)
                # Clean up active request
                del active_requests[user_id]

            # Remove the handler after processing
            robot.remove_event_handler(handle_button_click, bot.events.CallbackQuery)


async def handle_delete_account(callback_event, user_id):
    try:
        async with robot.conversation(callback_event.sender_id, timeout=300) as conv:
            # Prompt the user for their current password
            ask_password = await callback_event.edit(
                "🔐 Please provide your current password. 📝(Type /cancel to cancel)")

            # Wait for the user's password response
            password_response = await conv.wait_event(bot.events.NewMessage(from_users=callback_event.sender_id),
                                                      timeout=300)

            # Check for cancellation
            if password_response.raw_text.strip().lower() == "/cancel":
                await ask_password.edit("❌ Process canceled by user. 🛑")
                return  # End the process

            password = password_response.raw_text

            # Delete the user's password message for security
            try:
                await password_response.delete()
            except Exception as e:
                await callback_event.reply(f"❌ Failed to delete the password message: {e} 🔒⚠️")

            # Retrieve the stored hashed password from the database
            cursor.execute("SELECT password FROM mega WHERE user_id = ?", (user_id,))
            old_password = cursor.fetchone()

            # Verify the provided password
            if old_password and await hash_password_sha256(password) == old_password[0]:
                await robot.send_message(
                    user_id,
                    "✅ Password matched. Your Mega account has been removed. ☁️🗑️"
                )
                # Remove the Mega account from the database or handle the process
                await saved_mega_acc_handle(user_id, '', 0)
            else:
                await robot.send_message(
                    user_id,
                    "❌ Password does not match. Cannot remove the account. 🔒⚠️ Contact admin if needed. 💬")
    except asyncio.TimeoutError:
        # Handle timeout if the user takes too long to respond
        await callback_event.reply("⏳ You took too long to respond. Please try again by typing /delete_account. 🔄")
    except Exception as e:
        # General error handling
        await callback_event.reply(f"❌ An error occurred: {e} ⚠️")


async def handle_change_password(callback_event, user_id):
    try:
        async with robot.conversation(callback_event.sender_id, timeout=300) as conv:
            # Prompt for the current password
            ask_current_password = await callback_event.edit(
                "🔐 Please provide your current password. 📝(Type /cancel to cancel)")
            password_response = await conv.wait_event(bot.events.NewMessage(from_users=callback_event.sender_id),
                                                      timeout=300)

            # Check for cancellation
            if password_response.raw_text.strip().lower() == "/cancel":
                await ask_current_password.edit("❌ Process canceled by user. 🛑")
                return  # End the process

            current_password = password_response.raw_text

            # Delete the user's current password message
            try:
                await password_response.delete()
            except Exception as e:
                await callback_event.reply(f"❌ Failed to delete the password message: {e} 🔒⚠️")

            # Fetch the stored hashed password from the database
            cursor.execute("SELECT password FROM mega WHERE user_id = ?", (user_id,))
            old_password = cursor.fetchone()

            # Validate the current password
            if old_password and await hash_password_sha256(current_password) == old_password[0]:
                await robot.send_message(user_id, "✅ Current password matched. Now enter a new password. 🔑📝")

                # Prompt for the new password
                ask_new_password = await callback_event.edit(
                    "🔑 Please provide your new password. 📝(Type /cancel to cancel)")
                new_password_response = await conv.wait_event(
                    bot.events.NewMessage(from_users=callback_event.sender_id),
                    timeout=300)

                # Check for cancellation
                if new_password_response.raw_text.strip().lower() == "/cancel":
                    await ask_new_password.edit("❌ Process canceled by user. 🛑")
                    return  # End the process

                new_password = new_password_response.raw_text

                # Delete the user's new password message
                try:
                    await new_password_response.delete()
                except Exception as e:
                    await callback_event.reply(f"❌ Failed to delete the new password message: {e} 🔑⚠️")

                # Ensure the new password is not the same as the current password
                if new_password != current_password:
                    hashed_new_password = await hash_password_sha256(new_password)

                    # Fetch the user's email for authentication
                    cursor.execute("SELECT email FROM mega WHERE user_id = ?", (user_id,))
                    email = cursor.fetchone()
                    if email:
                        # Authenticate with Mega
                        mega_auth = await loop.run_in_executor(
                            None, contact_mega.authorize, email[0], new_password
                        )
                        if mega_auth == 0:
                            await robot.send_message(user_id, "✅ Authentication successful. 🔐")
                            await robot.send_message(user_id, "✅ Your password has been changed successfully. 🔑✔️")
                            # Update the password in the database
                            await saved_mega_acc_handle(user_id, hashed_new_password, 1)
                        else:
                            await robot.send_message(user_id,
                                                     "❌ Authentication failed. Your password was not changed. 🔑⚠️")
                    else:
                        await robot.send_message(user_id, "❌ No email found for your account. Contact support. 📧💬")
                else:
                    await robot.send_message(
                        user_id,
                        "❌ New password cannot be the same as the current password. Try again. 🔑⚠️"
                    )
            else:
                await robot.send_message(
                    user_id,
                    "❌ Current password does not match. Cannot change the password. 🔒⚠️")
    except asyncio.TimeoutError:
        await callback_event.reply("⏳ You took too long to respond. Please try again by typing /change_password. 🔄")
    except Exception as e:
        await callback_event.reply(f"❌ An error occurred: {e} ⚠️")


# Start
async def start(event):
    user_id = event.sender_id
    check_user = await check_user_in_group(user_id)
    username = event.sender.username or 'No username'
    full_name = event.sender.first_name + (f" {event.sender.last_name}" if event.sender.last_name else "")

    # Check if the user exists in the database
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()

    if result:
        await check_username_fullname_change(user_id, username, full_name)
        await event.reply(f"👋 Hello {full_name}! How can I help you? 😊")


async def quick_mode_dl(event, url, output_folder):
    user_id = event.sender_id
    try:
        # Ensure the folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Define options for yt-dlp
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',  # Only MP4 video and M4A audio
            'merge_output_format': 'mp4',  # Output in MP4 format after merging
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),  # Output template
            'quiet': True,  # Suppress output
            'no_warnings': True,  # Suppress warnings
        }

        # Use asyncio.to_thread to ensure yt_dlp download runs in a separate thread
        async def info(url):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Extract the video info without downloading it
                    info = await asyncio.to_thread(ydl.extract_info, url, False)
                    return {
                        "title": info.get("title")
                    }
            except Exception as e:
                return {"error": str(e)}

        # Use asyncio.to_thread for downloading
        async def download_with_yt_dlp(url, options):
            with yt_dlp.YoutubeDL(options) as ydl:
                return await asyncio.to_thread(ydl.download, [url])

        # Get video info asynchronously in a separate thread
        video_info = await info(url)

        if "error" in video_info:
            return f"Error: {video_info['error']}"

        # Start the download process
        await download_with_yt_dlp(url, ydl_opts)
        return "Done", video_info
    except Exception as e:
        return f"Error: {e}"  # Convert exception to string


async def quick_mode_yt(event, message, user_id):
    active_requests[user_id] = True
    await event.reply("⏳ Wait...")
    output_dir = f'./downloads/yt/{user_id}/'
    if os.path.exists(output_dir) == False:
        os.makedirs(output_dir, exist_ok=True)
    try:
        res, video_info = await quick_mode_dl(event, message, output_dir)
        if res == "Done":
            if os.path.exists(f'./downloads/yt/{user_id}/{video_info["title"]}.mp4') == True:

                upload = await asyncio.create_task(
                    upload_handling.send_file(user_id, BOT_TOKEN, semaphore,
                                              f'./downloads/yt/{user_id}/',
                                              f'{video_info["title"]}.mp4',
                                              f'{video_info["title"]}', 'vid'))

            else:

                file_res, file_search_res = await upload_handling.search_file_name('.mp4',
                                                                  f'./downloads/yt/{user_id}/')
                if file_search_res == "Done":
                    upload = await asyncio.create_task(
                        upload_handling.send_file(user_id, BOT_TOKEN, semaphore,
                                                  f'./downloads/yt/{user_id}/',
                                                  file_res,
                                                  f'{video_info["title"]}', 'vid'))
                else:
                    await robot.send_message(user_id, f"❌ File not found.{file_res} ⚠️")
                    return
            await robot.send_message(user_id, "🎥 Here is your video! 🎉")
            if upload == 201:
                await event.reply(
                    "❌ Your video is too large. Quick option not supported for downloading large videos. Use /youtube and try it. 🎥🔄")
                return
        else:
            await event.reply("❌ An error occurred. ⚠️")
    except Exception as e:
        await event.reply(f"❌ An error occurred: {e} ⚠️")
    finally:
        # Clean up active request
        del active_requests[user_id]


# Cancel Command
async def cancel(event):
    user_id = event.sender_id
    # Check if the user is in the middle of an active request
    if user_id in active_requests:
        del active_requests[user_id]  # Remove the user from active requests
        await event.reply("❌ Your current request has been canceled. Feel free to send a new command! 😊")
    else:
        await event.reply("⚠️ You have no active requests to cancel.")


async def instagram(event):
    user_id = event.sender_id
    


async def facebok(event):
    user_id = event.sender_id


async def tiktok(event):
    user_id = event.sender_id


async def message_filter(event, message, user_id):
    url_hosts = {'youtube.com': quick_mode_yt,
                 'youtu.be': quick_mode_yt,
                 'instagram.com': instagram,
                 'facebook.com': facebok,
                 'tiktok.com': tiktok
                 }

    parsed_url = urlparse(message)
    domain = parsed_url.netloc

    if domain in url_hosts:
        asyncio.create_task(url_hosts[domain](event, message, user_id))
        return
    else:
        await event.reply(f"💬 You said: {message} 🗣️")
        return


@robot.on(bot.events.NewMessage)
async def handle_message(event):
    try:
        user_id = None
        message_text = event.raw_text.strip()

        # Handle channel messages
        if event.is_channel:
            if event.chat.broadcast:
                await event.reply("This message is from a broadcast channel.")
            else:
                await event.reply("This message is from a group or discussion channel.")
            return

        # Handle private messages
        if event.is_private:
            # Check if the sender is a bot
            if event.sender.bot:
                return

            user_id = event.sender_id
            full_name = f"{event.sender.first_name} {event.sender.last_name or ''}".strip()
            username = event.sender.username or 'No username'

            if username == 'No username':
                await event.reply("📝 Please set a username for your Telegram account. 📱")
                return

            # Check user existence in the database
            try:
                cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
                user_exists = cursor.fetchone() is not None
            except Exception as e:
                print(f"Database error: {e}")
                await event.reply("⚠️ A technical issue occurred. Please try again later.")
                return

            # Handle new users
            if not user_exists:
                await robot.send_message(
                    user_id,
                    '''🎉 Welcome to the UniStreamXtract Bot! 🎉\n\n🚀 Here’s what I can do for you:\n
                    - Download YouTube Videos 📹 (up to 24-hour videos!)\n
                    - Extract Audio from YouTube Videos 🎵\n
                    - Upload Large Videos to Mega Cloud ☁️\n
                    \n✨ And the best part? It’s totally FREE! 💸\n'''
                )
                await user_register(user_id, username, full_name)

            if await check_user_in_group(user_id) == 'not_grp':
                await event.reply(
                    f"👋 Hello {full_name}!\n🎉 Welcome to the bot! \n📢 Please subscribe to {bot_config['bot_channel']} to get started."
                )
                return

            # Ignore messages sent by the bot itself
            if event.out:
                return

            # Command processing
            commands = {
                '/start': start,
                '/help': help,
                '/youtube': youtube,
                '/vip': vip,
                '/change_user_state': change_user_state,
                '/broadcast': broadcast,
                '/admin_panel': admin_panel,
                '/list_users': list_users,
                '/get_my_id': get_my_id,
                '/send_msg_for_grp': send_msg_for_grp,
                '/send_msg_for_client': send_msg_for_client,
                '/contact_admin': contact_admin,
                '/vdocipher': vdocipher,
                '/connect_mega_cloud': connect_mega_cloud,
                '/about_me': about_me,
                '/cancel': cancel
            }

            # Handle active requests
            if user_id in active_requests:
                if message_text in ['/cancel', bot_config['secret_code']]:
                    return  # Cancel ongoing requests
                await event.reply("⏳ You are already in progress. Please wait until the current task is completed. 🔄")
                return

            # Execute commands
            if message_text in commands:
                asyncio.create_task(commands[message_text](event))
                return
            else:
                # Handle non-command messages
                await message_filter(event, message_text, user_id)

    except Exception as e:
        print(f"Error in handle_message: {e}")
        await event.reply("⚠️ An unexpected error occurred. Please try again later.")



# Start the client and run until disconnected
async def main():
    print("🤖 Bot is running... ⏳")
    await robot.run_until_disconnected()


if __name__ == "__main__":
    # Start the bot
    robot.loop.run_until_complete(main())