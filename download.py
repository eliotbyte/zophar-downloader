import os
import sys
import time
import requests
import zipfile
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Setting up Selenium
def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run without browser GUI
    chrome_options.add_argument("--disable-gpu")
    service = Service(r'/path/to/chromedriver')  # Update this path
    browser = webdriver.Chrome(service=service, options=chrome_options)
    return browser

# Create a directory if it does not exist
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Download a file
def download_file(url, save_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Check for HTTP errors
    with open(save_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)

# Extract the archive
def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

# Validate game directories before downloading
def validate_game_directories(console_name):
    console_folder = os.path.join('downloads', console_name)
    if not os.path.exists(console_folder):
        return

    existing_game_folders = [name for name in os.listdir(console_folder)
                             if os.path.isdir(os.path.join(console_folder, name))]

    for game_folder_name in existing_game_folders:
        game_folder_path = os.path.join(console_folder, game_folder_name)
        files_in_game_folder = os.listdir(game_folder_path)
        if not files_in_game_folder:
            # Empty directory, delete it
            os.rmdir(game_folder_path)
        elif len(files_in_game_folder) == 1 and files_in_game_folder[0].startswith('cover'):
            # Only cover file, delete it
            os.remove(os.path.join(game_folder_path, files_in_game_folder[0]))
            os.rmdir(game_folder_path)

# Parse console page
def parse_console_page(console_url, console_name, browser, consoles_left):
    create_directory(os.path.join('downloads', console_name))
    page = 1
    all_games = []

    # Collect all game links and names
    while True:
        browser.get(f"{console_url}?page={page}")
        time.sleep(2)  # Wait for the page to load
        soup = BeautifulSoup(browser.page_source, 'lxml')

        games = soup.select('#gamelist .regularrow, #gamelist .regularrow_image')

        # Check if the page is empty (only header, no games)
        if not games:
            break  # End of list

        for game in games:
            name_td = game.find('td', class_='name')
            if name_td:
                a_tag = name_td.find('a')
                if a_tag:
                    game_link = a_tag['href']
                    game_name = a_tag.text.strip()
                    all_games.append((game_name, f"https://www.zophar.net{game_link}"))
            else:
                print("Game name not found.")

        page += 1

    total_games = len(all_games)
    print(f"Found {total_games} games for console {console_name}")

    # Validate existing game directories
    validate_game_directories(console_name)

    # Create a list of games to download (exclude already downloaded)
    games_to_download = []
    for game_name, game_url in all_games:
        game_folder = os.path.join('downloads', console_name, game_name)
        if os.path.exists(game_folder) and os.listdir(game_folder):
            # Directory exists and is not empty, skip
            continue
        else:
            games_to_download.append((game_name, game_url))

    total_games_to_download = len(games_to_download)
    print(f"{total_games_to_download} games to download for console {console_name}")

    # Now process each game, with progress display
    for idx, (game_name, game_url) in enumerate(games_to_download, start=1):
        parse_game_page(game_url, console_name, game_name, browser)

        # Display progress after downloading
        progress_message = f"{console_name} {idx} of {total_games_to_download} downloaded"
        print(progress_message, end='\r', flush=True)

    # After finishing
    print(f"\n{console_name} completed")
    print(f"{consoles_left} consoles left to download\n")

# Parse game page
def parse_game_page(game_url, console_name, game_name, browser):
    game_folder = os.path.join('downloads', console_name, game_name)
    create_directory(game_folder)

    browser.get(game_url)
    time.sleep(2)
    soup = BeautifulSoup(browser.page_source, 'lxml')

    # Find archive links with priority
    music_links = soup.select('#mass_download a')

    # Initialize variables for priority selection
    original_format_url = None
    wav_format_url = None
    flac_format_url = None
    mp3_format_url = None

    # Determine format priority
    for link in music_links:
        link_text = link.text.lower()
        if 'original' in link_text or 'emu' in link_text:
            original_format_url = link['href']
        elif 'wav' in link_text:
            wav_format_url = link['href']
        elif 'flac' in link_text:
            flac_format_url = link['href']
        elif 'mp3' in link_text:
            mp3_format_url = link['href']

    # Determine the most preferred URL
    preferred_format = original_format_url or wav_format_url or flac_format_url or mp3_format_url

    if preferred_format:
        archive_url = preferred_format
        archive_name = os.path.join(game_folder, "music.zip")
        try:
            download_file(archive_url, archive_name)
            extract_zip(archive_name, game_folder)
            os.remove(archive_name)  # Delete the archive after extraction
        except Exception as e:
            print(f"Error downloading or extracting archive for {game_name}: {e}")

    # Download the cover image after extracting the archive
    cover_img = soup.select_one('#music_cover img')
    if cover_img:
        cover_url = cover_img['src']
        cover_extension = os.path.splitext(cover_url)[1]  # Get the file extension
        cover_path = os.path.join(game_folder, f"cover{cover_extension}")
        try:
            download_file(cover_url, cover_path)  # Download the cover image into the music folder
        except Exception as e:
            print(f"Error downloading cover image for {game_name}: {e}")

# Function to sanitize console names
def sanitize_console_name(console_name):
    # If there is a "/" in the name, take only the part before "/"
    if "/" in console_name:
        console_name = console_name.split("/")[0].strip()
    return console_name

# Get the list of consoles from the site
def get_console_list(browser):
    url = "https://www.zophar.net/music"
    browser.get(url)
    time.sleep(2)  # Wait for the page to load
    soup = BeautifulSoup(browser.page_source, 'lxml')

    console_list = {}
    # Find all <h2> elements and locate the one with string 'Consoles'
    h2_elements = soup.find_all('h2')
    consoles_section = None
    for h2 in h2_elements:
        if h2.string == 'Consoles':
            consoles_section = h2.find_next_sibling('ul')
            break

    if consoles_section is None:
        print("Could not find the 'Consoles' section on the page.")
        return console_list  # Return empty list to avoid further errors

    for li in consoles_section.find_all('li'):
        a_tag = li.find('a')
        if a_tag:
            console_name = a_tag.text.strip()
            console_url = f"https://www.zophar.net{a_tag['href']}"
            # Sanitize console name for safe filesystem usage
            sanitized_name = sanitize_console_name(console_name)
            console_list[sanitized_name] = console_url

    return console_list

# Main downloader function
def download_music():
    browser = setup_browser()
    try:
        consoles = get_console_list(browser)
        if not consoles:
            print("No consoles found. Exiting.")
            return
        total_consoles = len(consoles)
        console_list = list(consoles.items())
        for idx, (console, url) in enumerate(console_list, start=1):
            consoles_left = total_consoles - idx
            print(f"Downloading for console: {console}")
            parse_console_page(url, console, browser, consoles_left)
    finally:
        browser.quit()

if __name__ == "__main__":
    download_music()
