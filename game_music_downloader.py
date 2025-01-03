import os
import json
import requests
import zipfile

# File containing the list of games
DOWNLOADS_LIST_FILE = "./downloads_list.json"

# Settings file
SETTINGS_FILE = "./settings.json"

# File with download status
DOWNLOAD_STATUS_FILE = "./download_status.json"

# File with the list of failed downloads
FAILED_DOWNLOADS_FILE = "./failed_downloads.txt"


# Create a directory if it does not exist
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


# Download a file from a URL
def download_file(url, save_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(save_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)


# Extract a zip archive
def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)


# Check and delete empty game directories
def validate_game_directories(console_name):
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


# Transform console name (if needed)
def sanitize_console_name(console_name):
    # If the console name contains '/', take the part before '/'
    if "/" in console_name:
        console_name = console_name.split("/")[0].strip()
    return console_name


# Select the download link based on priority
def select_download_link(download_links, format_priority):
    for priority in format_priority:
        for link_info in download_links:
            link_name_lower = link_info["name"].lower()
            if priority.lower() in link_name_lower:
                return link_info["url"]
    return None


# Load download status (if the file exists)
def load_download_status():
    if os.path.exists(DOWNLOAD_STATUS_FILE):
        with open(DOWNLOAD_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}  # If the file does not exist, return an empty dictionary


# Save download status
def save_download_status(status_data):
    with open(DOWNLOAD_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=4)


def main():
    # Load settings
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)

    download_consoles = [c.lower() for c in settings["download_consoles"]]
    format_priority = [f.lower() for f in settings["format_priority"]]
    need_to_extract = settings["need_to_extract"]

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

    # Process only the necessary consoles
    for console_lower in download_consoles:
        # Find all games for the current console
        games_for_console = console_to_games.get(console_lower, [])

        # Sanitize console name and create a folder
        sanitized_console_name = sanitize_console_name(console_lower)
        create_directory(os.path.join("downloads", sanitized_console_name))

        # Check for empty/broken folders
        validate_game_directories(sanitized_console_name)

        # Iterate through all games
        for game_data in games_for_console:
            game_name = game_data.get("name", "Untitled Game")
            download_links = game_data.get("download_links", [])
            image_url = game_data.get("image_url", "")
            game_url = game_data.get("game_page_url", "")

            # Check if the game is already downloaded (status "done")
            if (
                game_url in download_status
                and download_status[game_url].get("status") == "done"
            ):
                print(f"Skipping already downloaded game: {game_name}")
                continue

            game_folder = os.path.join("downloads", sanitized_console_name, game_name)
            create_directory(game_folder)

            # Select the best download link
            best_link = select_download_link(download_links, format_priority)

            if best_link:
                zip_path = os.path.join(game_folder, "music.zip")
                try:
                    download_file(best_link, zip_path)
                    if need_to_extract:
                        extract_zip(zip_path, game_folder)
                        os.remove(zip_path)  # Delete the archive

                        # Download the cover image, if needed
                        if image_url:
                            cover_extension = os.path.splitext(image_url)[1]
                            cover_path = os.path.join(
                                game_folder, f"cover{cover_extension}"
                            )
                            download_file(image_url, cover_path)
                    # If extraction is not needed, leave the archive as is (no cover download)

                    # Success: record the game status
                    download_status[game_url] = {"status": "done", "comment": ""}
                    save_download_status(download_status)  # Save after each game

                except Exception as e:
                    print(f"Error processing game {game_name}: {e}")
                    # Save failed download status
                    download_status[game_url] = {"status": "fail", "comment": str(e)}
                    save_download_status(download_status)

                    # Log the failed download URL
                    with open(
                        FAILED_DOWNLOADS_FILE, "a", encoding="utf-8"
                    ) as fail_file:
                        fail_file.write(game_url + "\n")

            else:
                print(f"No suitable link for game {game_name}. Skipping.")
                # Optionally record status indicating no suitable link
                download_status[game_url] = {
                    "status": "fail",
                    "comment": "No suitable link",
                }
                save_download_status(download_status)


if __name__ == "__main__":
    main()
