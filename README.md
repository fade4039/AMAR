# AMAR - Apple Music API Ripper

AMAR downloads artist, album, music video, and radio station assets from Apple Music. It extracts artwork, editorial videos, preview frames, and metadata (INFO files) across any or all of Apple Music's ~130 storefronts.

Available as both a **command-line interface (CLI)** and a **graphical desktop application (GUI/EXE)**.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Token Setup](#token-setup)
- [Usage - GUI (EXE)](#usage---gui-exe)
- [Usage - CLI](#usage---cli)
- [Building the EXE](#building-the-exe)
- [Configuration](#configuration)
- [Supported Content Types](#supported-content-types)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Artist assets** - Hero images, editorial artwork, editorial videos, general artwork, and biography info
- **Album assets** - Editorial videos, editorial artwork, cover artwork, track listings, and album metadata
- **Music video assets** - Preview frames and video metadata
- **Radio station assets** - Station artwork and metadata
- **Multi-storefront** - Download from one storefront or all ~130 at once
- **Search** - Search the Apple Music catalog by songs, albums, artists, or music videos
- **Charts** - Browse top songs, albums, and music video charts
- **Queue system** - Select multiple items from search/charts and batch download them
- **Dark/Light theme** - Toggle between dark and light mode in the Settings tab
- **Real-time progress** - Three progress bars: overall, current item, and per-file download
- **Automatic token extraction** - Uses Selenium to grab a developer token automatically on first launch

---

## Requirements

- **Python 3.10+** (tested on 3.13)
- **Google Chrome** (for automatic token extraction via Selenium)
- **ChromeDriver** (auto-managed by Selenium 4+)

### Python Dependencies

```
aiohttp>=3.9
aiofiles>=23.0
selenium>=4.0 (optional - required only for automatic token extraction)
```

Install them with:

```bash
pip install aiohttp aiofiles selenium
```

---

## Installation

### From Source

```bash
git clone <repository-url>
cd AMAR
pip install aiohttp aiofiles selenium
```

### Standalone EXE

Download `AMAR.exe` from the releases page. No Python installation required. Place it in any folder and double-click to run.

---

## Token Setup

AMAR requires an Apple Music developer token to access the API. There are three ways to obtain one:

### Option 1: Automatic (Recommended)

On first launch, if no `token.txt` file is found, AMAR will automatically:
1. Open a headless Chrome browser
2. Navigate to music.apple.com
3. Extract the developer token from MusicKit
4. Save it to `token.txt`

A splash screen will appear showing the progress. This requires Google Chrome to be installed.

### Option 2: CLI Extraction

```bash
python -m amar --extract-token
```

This runs the same Selenium extraction from the command line.

### Option 3: Manual

1. Open https://music.apple.com in your browser
2. Open Developer Tools (F12)
3. In the Console tab, run: `MusicKit.getInstance().developerToken`
4. Copy the output
5. Create a file called `token.txt` in the same directory as AMAR (or the EXE) and paste the token into it

> **Note:** Tokens expire periodically. If you see "Token expired" errors, refresh the token using the Settings tab in the GUI, option 5 in the CLI, or by re-running `--extract-token`.

---

## Usage - GUI (EXE)

### Launching

- **EXE:** Double-click `AMAR.exe`. It opens the GUI automatically.
- **From source:** Run `python -m amar --gui`

### Tabs

#### Download Tab

The main download interface.

1. Paste an Apple Music URL into the input field (or use the **Paste** button)
2. The URL is automatically detected and parsed (artist, album, music video, or station)
3. Configure options:
   - **Info only** - Download only metadata text files (no images/videos)
   - **Include albums** / **Include music videos** - (artist URLs only) toggle whether to also rip all albums and music videos for that artist
   - **Storefronts** - Choose "Current storefront only" or "All storefronts (~130)"
4. Click **Start Download**
5. Monitor progress via the three progress bars:
   - **Overall Progress** - Tracks storefront completion
   - **Current Item** - Tracks the current album/video being processed
   - **File Download** - Shows real-time KB downloaded for the current file
6. Click **Cancel** to stop at any time

#### Queue Tab

Batch download multiple items.

1. Use the **Search** or **Charts** tab to find items
2. Select one or more results (Ctrl+Click for multi-select)
3. Click **Add to Queue** - items are added to the Queue tab
4. Switch to the Queue tab to review your items
5. Configure storefront and info-only options
6. Click **Process Queue** to download everything sequentially
7. Use **Remove Selected** or **Clear Completed** to manage the list

#### Search Tab

Search the Apple Music catalog.

1. Enter a search query
2. Select a type filter: All, Songs, Albums, Artists, or Music Videos
3. Press Enter or click **Search**
4. Results appear in the table with Name, Artist, Type, and URL
5. Select items and use:
   - **Add to Queue** - Batch download later
   - **Copy URL** - Copy the Apple Music URL to clipboard
   - **Download** - Jump to the Download tab with the URL pre-filled

#### Charts Tab

Browse current Apple Music charts.

1. Select a chart type: Songs, Albums, Both, or Music Videos
2. Set a limit (10, 20, or 50)
3. Click **Refresh**
4. Results appear in the table
5. Same actions as Search: Add to Queue, Copy URL, Download

#### Storefront Tab

Browse and change the active storefront (country/region).

- View the current storefront and its details
- Browse all ~130 available storefronts
- Click to select a new default storefront

#### Settings Tab

Configure application settings.

- **Appearance** - Toggle between Dark Mode and Light Mode
- **Save Location** - Choose where downloaded assets are saved
- **Token Management** - Refresh the token via Selenium or paste one manually
- **Performance** - Tune concurrency, rate limits, chunk size, cache TTL, and retries
- **Default Storefront** - Set the default country/region for API requests
- Click **Save Settings** to persist changes
- Click **Reset to Defaults** to restore default performance values

---

## Usage - CLI

### Launching

```bash
python -m amar
```

On first launch, you will be prompted to select a save location.

### Main Menu

```
============================================================
  APPLE MUSIC API RIPPER (AMAR) V2
============================================================
  1. Download from URL (Artist/Album/Music Video/Station)
  2. Search Catalog
  3. View Charts
  4. View Storefront Info
  5. Extract New Token (Selenium)
  6. Change Storefront
  7. Exit
============================================================
```

### Option 1: Download from URL

Paste any Apple Music URL. AMAR auto-detects the content type.

```
  Enter Apple Music URL: https://music.apple.com/us/artist/taylor-swift/159260351
  Detected: artist | ID: 159260351 | Storefront: us
  Download only INFO files? (y/n): n
  Rip all albums? (y/n): y
  Rip all music videos? (y/n): y
  Country code (current: us, 'all' for every storefront, Enter to keep): us
```

**Supported URL formats:**
```
https://music.apple.com/{storefront}/artist/{name}/{id}
https://music.apple.com/{storefront}/album/{name}/{id}
https://music.apple.com/{storefront}/music-video/{name}/{id}
https://music.apple.com/{storefront}/station/{name}/{id}
```

### Option 2: Search Catalog

Search by songs, albums, artists, music videos, or all at once.

```
  Enter search query: Kendrick Lamar
  Search types:
  1. All (songs, albums, artists)
  2. Songs only
  3. Albums only
  4. Artists only
  5. Music videos
  6. Custom
  Select option (1-6): 1
```

### Option 3: View Charts

Browse the current top charts for the active storefront.

### Option 5: Extract New Token

Re-extract the developer token using Selenium (requires Chrome).

### Option 6: Change Storefront

Switch the active storefront by entering a 2-letter country code (e.g., `us`, `gb`, `jp`, `kr`).

---

## Building the EXE

To build a standalone Windows executable:

```bash
pip install pyinstaller

python -m PyInstaller --name AMAR --onefile --windowed \
  --hidden-import aiohttp --hidden-import aiofiles \
  --hidden-import selenium --hidden-import asyncio \
  --collect-all aiohttp --noconfirm launcher.py
```

The EXE will be created at `dist/AMAR.exe`.

**Optional flags:**
- `--icon=icon.ico` - Add a custom application icon
- Replace `--onefile` with `--onedir` for faster startup (creates a folder instead of a single file)

> **Important:** The EXE uses `launcher.py` as its entry point (not `__main__.py`), because PyInstaller requires absolute imports.

---

## Configuration

AMAR stores its configuration in the application directory:

| File | Purpose |
|---|---|
| `token.txt` | Apple Music developer token |
| `amar_config.json` | Saved settings (storefront, theme, performance, etc.) |
| `dest.path` | Saved download location (legacy compatibility) |

### Default Settings

| Setting | Default | Description |
|---|---|---|
| Storefront | `us` | Default country/region |
| Theme | `dark` | Dark or light mode |
| Max Concurrency | `10` | Maximum simultaneous connections |
| Rate Limit | `18 req/s` | API requests per second (Apple's limit is ~20) |
| Chunk Size | `64 KB` | Download buffer size |
| Cache TTL | `300s` | How long API responses are cached |
| Max Retries | `3` | Number of retry attempts on failure |

---

## Supported Content Types

### Artist

Downloads from the artist's catalog page:
- Hero artwork (wide banner image)
- Editorial videos (animated artist page videos) + preview frames
- Editorial artwork (curated images)
- General artwork (profile image)
- INFO.txt (name, genres, origin, bio, Apple Music URL)

### Album

Downloads from the album's page:
- Editorial videos + preview frames
- Editorial artwork
- Cover artwork
- INFO.txt (track listing with durations, composers, ISRCs, release date, UPC, editorial notes)

### Music Video

Downloads from the music video's page:
- Preview frame (thumbnail artwork)
- INFO.txt (title, artist, album, release date, duration, URL)

### Radio Station

Downloads from the station's page:
- Station artwork
- INFO.txt (name, description, URL)

---

## Project Structure

```
AMAR/
  launcher.py           # EXE entry point (absolute imports)
  amar/
    __main__.py          # CLI/GUI entry point (python -m amar)
    config.py            # Configuration management + country codes
    utils.py             # URL parsing, filename sanitization
    api/
      client.py          # Async HTTP client with rate limiting + retry
      pagination.py      # API pagination helpers
      token.py           # Token extraction via Selenium
    core/
      artist.py          # Artist asset ripper
      album.py           # Album asset ripper
      music_video.py     # Music video asset ripper
      radio_station.py   # Radio station asset ripper
      downloader.py      # CDN file downloader with progress callbacks
      m3u8.py            # HLS/M3U8 video URL resolver
      search.py          # Catalog search
      charts.py          # Charts fetching
    cli/
      menu.py            # Interactive CLI menu
    gui/
      app.py             # Main GUI application + async bridge
      theme.py           # Dark/light theme system
      queue_manager.py   # Download queue with observer pattern
      tabs/
        download_tab.py  # URL download interface
        queue_tab.py     # Queue management interface
        search_tab.py    # Search interface
        charts_tab.py    # Charts browser
        storefront_tab.py # Storefront browser
        settings_tab.py  # Settings + theme toggle
      widgets/
        log_panel.py     # Scrollable log with color-coded levels
        progress.py      # Progress bar with percentage display
        results_view.py  # Multi-select treeview for search/chart results
```

---

## Troubleshooting

### "No token found" on launch

- Make sure `token.txt` is in the same directory as `AMAR.exe` (or the project root for CLI)
- If automatic extraction fails, ensure Google Chrome is installed
- Try manual token extraction (see [Token Setup](#token-setup))

### "Token expired" errors during download

Tokens expire periodically. Refresh via:
- **GUI:** Settings tab > "Refresh Token (Selenium)" or "Paste Token Manually"
- **CLI:** Option 5 from the main menu
- **Command:** `python -m amar --extract-token`

### HTTP 400 errors on downloads

This is usually caused by an invalid or expired token. Refresh the token and try again.

### Selenium / ChromeDriver errors

- Ensure Google Chrome is installed and up to date
- Selenium 4+ auto-manages ChromeDriver, but if you see driver errors, try updating: `pip install --upgrade selenium`

### EXE crashes immediately

- Run from a terminal to see the error: open Command Prompt, navigate to the EXE directory, and run `AMAR.exe`
- Check that `token.txt` exists and contains a valid token

### "Rate limit" warnings

AMAR defaults to 18 requests/second (Apple's limit is ~20). If you see rate limit warnings, reduce the rate in Settings > Performance.

### Downloads are slow

- Increase "Max concurrent connections" in Settings (default: 10, max: 20)
- Increase "Download chunk size" to 128 KB or 256 KB
- Downloading from "All storefronts" involves ~130 separate API calls per item

---

## License

This tool is for personal and educational use only. Respect Apple's Terms of Service and the rights of content creators.
