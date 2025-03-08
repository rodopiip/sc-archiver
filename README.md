# SC archiver

Download all of your soundcloud uploads quickly. Requires **Python 3.12**.

# Obtaining your client id and token

## Client id

1. Open the network tab in Chrome dev tools
2. Go to Network
3. Filter for `?client_id=`
4. Refresh the soundcloud page
5. Copy the client_id from one of the API calls that contain it

## Auth Token

1. Open the application tab in Chrome dev tools
2. Go to Cookies
3. Open the soundcloud cookies
4. Find the `oauth_token` cookie and copy it's value


# Running the script 

## Basic usage:

```shell
python3 sc-archiver.py --client_id <CLIENT_ID> --auth-token <OAUTH_TOKEN>
```

## All options
```shell
usage: sc-archiver.py [-h] --client-id CLIENT_ID --auth-token AUTH_TOKEN [--download-folder DOWNLOAD_FOLDER] [--num-parallel-downloads NUM_PARALLEL_DOWNLOADS]

SoundCloud Archive Downloader

options:
  -h, --help            show this help message and exit
  --client-id CLIENT_ID
                        SoundCloud Client ID
  --auth-token AUTH_TOKEN
                        SoundCloud Authentication Token
  --download-folder DOWNLOAD_FOLDER
                        Folder where tracks will be downloaded (default: soundcloud_archive)
  --num-parallel-downloads NUM_PARALLEL_DOWNLOADS
                        Number of parallel downloads (default: 5)
```
