import asyncio
import telethon as tl

async def select_format(event, robot, formats, desired_ext, format_type):
    buttons = []

    # Process the formats and add buttons
    for fmt in formats:
        format_id = fmt.get("format_id", "N/A")
        ext = fmt.get("ext", "N/A")
        filesize = fmt.get("filesize", None)
        res = fmt.get("resolution", None)
        resolution = res.split('x')[-1]
        fps = fmt.get("fps", "N/A")
        acodec = fmt.get('acodec')  # Audio codec
        vcodec = fmt.get('vcodec')  # Video codec
        bitrate = str(fmt.get('tbr'))
        lang = fmt.get('language', 'unknown')
        filesize_mb = f"{filesize / 1024 / 1024:.2f} MB" if filesize else "Unknown"

        if ext == desired_ext and filesize_mb != "Unknown" and lang != 'unknown':
            if format_type == "vid":
                button_text = f"Resolution: {resolution}p | FPS: {fps} | Size: {filesize_mb}"
            else:  # audio
                button_text = f"Bitrate: {bitrate.split('.')[0]}kbps | Lang: {lang} | Size: {filesize_mb}"
            if format_type == "vid":
                buttons.append([tl.Button.inline(button_text, data=f"{resolution}p_{format_id}")])
            else:
                buttons.append([tl.Button.inline(button_text, data=f"{bitrate.split('.')[0]}kbps_{format_id}")])
    if desired_ext == 'mp4':
        buttons.append([tl.Button.inline("Audio Only", data='Audio_0')])

    if not buttons:
        await event.reply(f"No {format_type} ({resolution}p) formats available.")
        return None
    if format_type == 'vid':
        message = await event.reply(f"Select a video quality:", buttons=buttons)
    else:
        message = await event.reply(f"Select a audio bitrate:", buttons=buttons)
    selection_event = asyncio.Event()
    selected_format_id = {"id": None}

    async def on_callback(callback_event):
        format_id = callback_event.data.decode("utf-8").split("_")[1]
        selected_format_id["id"] = format_id
        if format_id == '0':
            await callback_event.respond(f"You selected Download Audio Only.")
        else:
            if format_type == 'vid':
                await callback_event.respond(f"You selected Video quality: {callback_event.data.decode("utf-8").split("_")[0]}")
            else:
                await callback_event.respond(f"You selected Audio bitrate: {callback_event.data.decode("utf-8").split("_")[0]}")

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