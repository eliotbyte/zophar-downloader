import os
import json
import requests
import zipfile
import time
import re

# File containing the list of games
DOWNLOADS_LIST_FILE = "./downloads_list.json"

# Settings file
SETTINGS_FILE = "./settings.json"

# File with download status
DOWNLOAD_STATUS_FILE = "./download_status.json"

# File with the list of failed downloads (now JSON)
FAILED_DOWNLOADS_FILE = "./failed_downloads.json"


def create_directory(path):
    """Create a directory if it does not exist."""
    if not os.path.exists(path):
        os.makedirs(path)


def download_file_with_retry(url, save_path, retry_count, retry_delay_seconds):
    """
    Attempts to download the file from a URL up to 'retry_count' times.
    Delays 'retry_delay_seconds' between attempts. Raises an exception if all retries fail.
    """
    last_exception = None
    for attempt in range(retry_count):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(save_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            # If download succeeded, return
            return
        except Exception as e:
            last_exception = e
            if attempt < retry_count - 1:
                print(
                    f"Download failed (attempt {attempt+1}/{retry_count}). "
                    f"Retrying in {retry_delay_seconds} seconds..."
                )
                time.sleep(retry_delay_seconds)
    # If we get here, all attempts failed
    raise last_exception


def extract_zip(zip_path, extract_to):
    """Extract a zip archive into the specified directory."""
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)


def validate_game_directories(console_name):
    """
    Check each game folder under 'console_name' in 'downloads' and remove it
    if it's empty or only contains a cover file.
    """
    console_folder = os.path.join("downloads", console_name)
    if not os.path.exists(console_folder):
        return

    existing_game_folders = [
        name
        for name in os.listdir(console_folder)
        if os.path.isdir(os.path.join(console_folder, name))
    ]

    for game_folder_name in existing_game_folders:
        game_folder_path = os.path.join(console_folder, game_folder_name)
        files_in_game_folder = os.listdir(game_folder_path)
        if not files_in_game_folder:
            # Empty directory
            os.rmdir(game_folder_path)
        elif len(files_in_game_folder) == 1 and files_in_game_folder[0].startswith(
            "cover"
        ):
            # Only a cover image
            os.remove(os.path.join(game_folder_path, files_in_game_folder[0]))
            os.rmdir(game_folder_path)


def sanitize_console_name(console_name):
    """
    If the console name contains '/', take the part before '/'.
    Returns a sanitized console name.
    """
    if "/" in console_name:
        console_name = console_name.split("/")[0].strip()
    # Remove any invalid path characters in the console name if needed
    console_name = re.sub(r'[<>:"/\\|?*]', "_", console_name)
    return console_name


def sanitize_folder_name(folder_name):
    """
    Remove or replace invalid path characters for Windows and ensure
    there are no trailing dots or spaces. This helps avoid directory
    creation issues.
    """
    # Replace invalid filename characters: < > : " / \ | ? *
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", folder_name)
    # Remove trailing spaces and periods
    sanitized = sanitized.rstrip(" .")
    return sanitized


def select_download_link(download_links, format_priority):
    """
    Select a download link from 'download_links' based on the priority in 'format_priority'.
    For instance, if format_priority is ["mp3", "flac"], it will return the first link
    whose 'name' contains 'mp3', otherwise 'flac', and so on.
    """
    for priority in format_priority:
        for link_info in download_links:
            link_name_lower = link_info["name"].lower()
            if priority.lower() in link_name_lower:
                return link_info["url"]
    return None


def load_download_status():
    """
    Load the download status from DOWNLOAD_STATUS_FILE if it exists.
    Returns a dictionary of statuses.
    """
    if os.path.exists(DOWNLOAD_STATUS_FILE):
        with open(DOWNLOAD_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_download_status(status_data):
    """Save the download status to DOWNLOAD_STATUS_FILE."""
    with open(DOWNLOAD_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=4)


def load_failed_downloads():
    """
    Load the failed downloads from FAILED_DOWNLOADS_FILE if it exists.
    Returns a dictionary of failed downloads.
    """
    if os.path.exists(FAILED_DOWNLOADS_FILE):
        with open(FAILED_DOWNLOADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_failed_downloads(failed_data):
    """Save the failed downloads to FAILED_DOWNLOADS_FILE."""
    with open(FAILED_DOWNLOADS_FILE, "w", encoding="utf-8") as f:
        json.dump(failed_data, f, ensure_ascii=False, indent=4)


def main():
    # Load settings
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)

    download_consoles = [c.lower() for c in settings["download_consoles"]]
    format_priority = [f.lower() for f in settings["format_priority"]]
    need_to_extract = settings["need_to_extract"]
    redownload_failed_files = settings.get("redownload_failed_files", False)
    retry_count = settings.get("retry_count", 3)
    retry_delay_seconds = settings.get("retry_delay_seconds", 5)

    # Load the list of games
    with open(DOWNLOADS_LIST_FILE, "r", encoding="utf-8") as f:
        games_list = json.load(f)

    # Group games by console
    console_to_games = {}
    for game_entry in games_list:
        console_name = game_entry.get("console", "").lower()
        if console_name not in console_to_games:
            console_to_games[console_name] = []
        console_to_games[console_name].append(game_entry)

    # Load the current download status of games
    download_status = load_download_status()

    # Load the current failed downloads
    failed_downloads = load_failed_downloads()

    # Process only the necessary consoles
    for console_lower in download_consoles:
        # Find all games for the current console
        games_for_console = console_to_games.get(console_lower, [])

        # Sanitize console name and create a folder
        sanitized_console_name = sanitize_console_name(console_lower)
        create_directory(os.path.join("downloads", sanitized_console_name))

        # Validate existing folders for empty or broken game folders
        validate_game_directories(sanitized_console_name)

        # Iterate through all games for this console
        for game_data in games_for_console:
            game_name = game_data.get("name", "Untitled Game")
            download_links = game_data.get("download_links", [])
            image_url = game_data.get("image_url", "")
            game_url = game_data.get("game_page_url", "")

            # Determine if this game has a recorded status
            current_status = download_status.get(game_url, {}).get("status")

            # Skip if already downloaded
            if current_status == "done":
                print(f"Skipping already downloaded game: {game_name}")
                continue

            # Skip if it failed previously and we're not re-downloading
            if current_status == "fail" and not redownload_failed_files:
                print(
                    f"Skipping previously failed game (redownload disabled): {game_name}"
                )
                continue

            # Sanitize the game folder name
            safe_game_name = sanitize_folder_name(game_name)
            game_folder = os.path.join(
                "downloads", sanitized_console_name, safe_game_name
            )
            create_directory(game_folder)

            # Let the user know which game is starting to download
            print(f"Now downloading: {game_name}")

            # Select the best download link
            best_link = select_download_link(download_links, format_priority)

            if best_link:
                zip_path = os.path.join(game_folder, "music.zip")
                try:
                    # Use retry logic for download
                    download_file_with_retry(
                        best_link, zip_path, retry_count, retry_delay_seconds
                    )

                    if need_to_extract:
                        extract_zip(zip_path, game_folder)
                        os.remove(zip_path)  # Delete the archive after extraction

                        # Download the cover image if an image URL is provided
                        if image_url:
                            cover_extension = os.path.splitext(image_url)[1]
                            cover_path = os.path.join(
                                game_folder, f"cover{cover_extension}"
                            )
                            download_file_with_retry(
                                image_url, cover_path, retry_count, retry_delay_seconds
                            )
                    # If extraction is not needed, leave the archive as is (no cover download)

                    # Success: record the game status as "done"
                    download_status[game_url] = {"status": "done", "comment": ""}
                    save_download_status(download_status)

                except Exception as e:
                    print(f"Error processing game {game_name}: {e}")
                    # Save failed download status
                    download_status[game_url] = {"status": "fail", "comment": str(e)}
                    save_download_status(download_status)

                    # Don't add a duplicate to failed_downloads if the entry already exists
                    if game_url not in failed_downloads:
                        failed_downloads[game_url] = {
                            "status": "fail",
                            "comment": str(e),
                        }
                        save_failed_downloads(failed_downloads)

            else:
                print(f"No suitable link for game {game_name}. Skipping.")
                download_status[game_url] = {
                    "status": "fail",
                    "comment": "No suitable link",
                }
                save_download_status(download_status)

                if game_url not in failed_downloads:
                    failed_downloads[game_url] = {
                        "status": "fail",
                        "comment": "No suitable link",
                    }
                    save_failed_downloads(failed_downloads)


if __name__ == "__main__":
    main()
