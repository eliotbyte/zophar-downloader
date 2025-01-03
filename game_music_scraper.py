import os
import sys
import json
from bs4 import BeautifulSoup
import requests
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    # Disable loading of images, styles, and plugins
    chrome_prefs = {
        "profile.default_content_setting_values": {
            "images": 2,  # Disable image loading
            "stylesheets": 2,  # Disable CSS loading
            "plugins": 2,
            "popups": 2,
            # If the site is not critical to JS, you can disable it as well:
            # "javascript": 2
        }
    }
    chrome_options.experimental_options["prefs"] = chrome_prefs

    service = Service(r"/path/to/chromedriver")  # Specify the path to your chromedriver
    browser = webdriver.Chrome(service=service, options=chrome_options)

    # Set a general implicit wait time
    browser.implicitly_wait(5)

    return browser


def sanitize_console_name(console_name):
    # If the name contains "/", take only what comes before "/"
    if "/" in console_name:
        console_name = console_name.split("/")[0].strip()
    return console_name


def get_console_list(browser):
    """
    Retrieve the list of consoles from the main "Music" section page.
    Returns a dictionary in the format { 'consoleName': 'consoleUrl', ... }.
    """
    url = "https://www.zophar.net/music"
    browser.get(url)

    # Wait for the h2 header "Consoles" to appear
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "h2"))
    )
    soup = BeautifulSoup(browser.page_source, "lxml")

    console_list = {}
    h2_elements = soup.find_all("h2")
    consoles_section = None
    for h2 in h2_elements:
        if h2.string == "Consoles":
            consoles_section = h2.find_next_sibling("ul")
            break

    if consoles_section is None:
        print("Failed to find the 'Consoles' section.")
        return console_list  # Empty dictionary

    for li in consoles_section.find_all("li"):
        a_tag = li.find("a")
        if a_tag:
            console_name = a_tag.text.strip()
            console_url = f"https://www.zophar.net{a_tag['href']}"
            sanitized_name = sanitize_console_name(console_name)
            console_list[sanitized_name] = console_url

    return console_list


def parse_console_page(console_url, console_name, browser):
    """
    Parse the page for a specific console, collect links to games, and
    visit each game's page to gather necessary information.
    Returns a list with all the game data for the given console.
    """
    games_data = []
    page = 1

    while True:
        browser.get(f"{console_url}?page={page}")
        # Wait for the #gamelist container to appear (or confirm its absence)
        try:
            WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#gamelist"))
            )
        except:
            # If the element is not present, there are no more pages
            break

        soup = BeautifulSoup(browser.page_source, "lxml")

        games = soup.select("#gamelist .regularrow, #gamelist .regularrow_image")

        # Exit if no games are found
        if not games:
            break

        for game in games:
            name_td = game.find("td", class_="name")
            if name_td:
                a_tag = name_td.find("a")
                if a_tag:
                    game_name = a_tag.text.strip()
                    game_link = f"https://www.zophar.net{a_tag['href']}"

                    print(f"Processing game: {game_name} from {console_name}")

                    # Visit the game page
                    game_info = parse_game_page(
                        game_link, console_name, game_name, browser
                    )
                    if game_info:
                        games_data.append(game_info)
                else:
                    print("Game link not found.")
            else:
                print("Game name not found.")
        page += 1

    return games_data


def parse_game_page(game_url, console_name, game_name, browser):
    """
    Parse the game's page: cover, release date, developer, publisher,
    and download links.
    Returns a data structure for saving to JSON.
    """
    browser.get(game_url)
    # Wait for the #music_info or #mass_download block (if needed)
    try:
        WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#music_info"))
        )
    except:
        pass

    soup = BeautifulSoup(browser.page_source, "lxml")

    # Cover
    cover_img_tag = soup.select_one("#music_cover img")
    cover_url = ""
    if cover_img_tag and cover_img_tag.get("src"):
        cover_url = cover_img_tag["src"]

    # Main information
    release_date = ""
    developer = ""
    publisher = ""
    console = console_name  # Already known

    music_info_div = soup.select_one("#music_info")
    if music_info_div:
        p_tags = music_info_div.find_all("p")
        for p in p_tags:
            label_span = p.find("span", class_="infoname")
            data_span = p.find("span", class_="infodata")
            if label_span and data_span:
                label_text = label_span.get_text(strip=True).lower()
                data_text = data_span.get_text(strip=True)
                if "release date" in label_text:
                    release_date = data_text
                elif "developer" in label_text:
                    developer = data_text
                elif "publisher" in label_text:
                    publisher = data_text

    # Download links
    download_links = []
    mass_download_div = soup.select_one("#mass_download")
    if mass_download_div:
        links = mass_download_div.find_all("a")
        for link in links:
            link_url = link.get("href", "")
            link_text_tag = link.find("p")
            link_text = link_text_tag.get_text(strip=True) if link_text_tag else ""
            download_links.append({"name": link_text, "url": link_url})

    return {
        "name": game_name,
        "image_url": cover_url,
        "game_page_url": game_url,
        "release_date": release_date,
        "console": console,
        "developer": developer,
        "publisher": publisher,
        "download_links": download_links,
    }


def main():
    browser = setup_browser()
    all_data = []
    try:
        consoles = get_console_list(browser)
        if not consoles:
            print("No consoles found.")
            return

        for console_name, console_url in consoles.items():
            print(f"Processing console: {console_name}")
            console_games_data = parse_console_page(console_url, console_name, browser)
            all_data.extend(console_games_data)
    finally:
        browser.quit()

    with open("downloads_list.json", "w", encoding="utf-8") as outfile:
        json.dump(all_data, outfile, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
