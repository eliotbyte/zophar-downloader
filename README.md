# Zophar Music Downloader

A Python script to download game music and cover images from [Zophar's Domain](https://www.zophar.net/music), organized by console and game. The script navigates through the site, collects game music files in preferred formats, and saves them into a structured directory.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Automated Downloading**: Automatically downloads music files and cover images for games from Zophar's Domain.
- **Organized Structure**: Saves files in a structured directory (`./downloads/<Console>/<Game>/`).
- **Format Prioritization**: Downloads music files in preferred formats based on quality:
  - Original/Emulated formats
  - WAV
  - FLAC
  - MP3
- **Resume Capability**: Skips downloading files that already exist, allowing you to resume interrupted downloads.
- **Progress Display**: Displays download progress for each console and game.
- **Directory Validation**: Cleans up empty or incomplete game directories before downloading.

## Prerequisites

- **Python 3.6 or higher**: Ensure you have Python installed.
- **Google Chrome Browser**: The script uses Chrome for web scraping.
- **ChromeDriver**: Required for Selenium to control Chrome.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/eliotbyte/zophar_downloader.git
cd zophar-music-downloader
```

### 2. Install Python Dependencies

It's recommended to use a virtual environment.

#### Using

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Install ChromeDriver

#### Steps:

1. Check Chrome Version:
    - Open Google Chrome.
    - Navigate to chrome://settings/help.
    - Note the version number (e.g., 96.0.4664.45).
2. Download ChromeDriver:
    - Visit ChromeDriver Downloads.
    - Download the version that matches your Chrome browser version.
3. Install ChromeDriver:
    - Extract the downloaded archive.
    - Move the chromedriver executable to a directory in your system's PATH or specify its path in the script configuration.

### 4. Update Script Configuration

In the `download.py` script, update the path to your `chromedriver` executable in the `setup_browser()` function:

## Usage

Run the script using the command:

```bash
python download.py
```

The script will:

- Navigate to the Zophar's Domain music page.
- Retrieve the list of consoles.
- For each console:
    - Create a directory with the console's name under ./downloads/.
    - Retrieve all game links for that console.
    - For each game:
        - Create a directory with the game's name.
        - Download the cover image (if available).
        - Download and extract the music files in the preferred format.
        - Display progress in the console.