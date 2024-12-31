import requests
import requests
import os

def token(token_url, user_id):
     # URL of the file to download

    if os.path.exists(f'./downloads/vdocipher/{user_id}/Temp/') == False:
        os.makedirs(f'./downloads/vdocipher/{user_id}/Temp/', exist_ok=True)


    if os.path.exists(f'./downloads/vdocipher/{user_id}/OUT/') == False:
        os.makedirs(f'./downloads/vdocipher/{user_id}/OUT/', exist_ok=True)

    if os.path.exists(f'./downloads/vdocipher/{user_id}/DRM/') == False:
        os.makedirs(f'./downloads/vdocipher/{user_id}/DRM/', exist_ok=True)
     
    # Send an HTTP GET request to the URL
    response = requests.get(token_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Open a file in write-binary mode and save the content
        with open(f'./downloads/vdocipher/{user_id}/Temp/token.txt', 'wb') as f:
            f.write(response.content)
        print("File downloaded successfully.")
    else:
        print(f"Failed to download file. Status code: {response.status_code}")

    file = open(f'./downloads/vdocipher/{user_id}/Temp/token.txt', 'r')
    get = file.read()
    file.close()
    get_token_start_character = get.find('token')
    token = ''
    for i in range(get_token_start_character+8, len(get)):
        if get[i] != '"':
            token += get[i]
        else:
            break

    return token