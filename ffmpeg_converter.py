import ffmpeg

def convert_to_mp4(input_file, output_file):
    try:
        # Use ffmpeg to convert the video
        ffmpeg.input(input_file).output(output_file, vcodec='libx264', acodec='aac', strict='experimental', loglevel='quiet').run()
        return 0
    except ffmpeg.Error as e:
        return e