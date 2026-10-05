# 🎬 AP-DLP Python Downloader

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/yt--dlp-Powered-red.svg?logo=youtube&logoColor=white" alt="ap-dlp">
  <img src="https://img.shields.io/badge/FFmpeg-Auto--Bundled-green.svg" alt="FFmpeg Bundled">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Cross-Platform">
</p>

An interactive, feature-rich command-line YouTube and media downloader built in Python using **`ap-dlp`**. 

Developed by **Abhijeet Pandey**, **AP-DLP** simplifies media downloads with interactive quality selection, automatic audio extraction, live terminal progress bars, playlist management, and built-in **FFmpeg** path resolution without messy environment configurations.

---

## ✨ Features

- 🎯 **Interactive Video Quality Selector**: Choose between **Best Available**, **1080p Full HD**, **720p HD**, **480p SD**, or **360p Data Saver**.
- 🎵 **High-Quality Audio Extraction**: Directly extract clean **192kbps MP3** audio from any video.
- 📑 **Full Playlist Downloads**: Download entire YouTube playlists with structured folder organization (`Playlist Name / Index - Video Title`).
- 💬 **Embedded Subtitles**: Automatically fetch and embed subtitles into media files (`.mkv` / `.mp4`).
- ⚡ **Auto-Bundled FFmpeg**: Powered by `static-ffmpeg`—no need to manually download FFmpeg binaries or configure Windows PATH.
- 📊 **Real-Time Terminal Progress Bar**: Custom dynamic progress meter showing:
  - Percentage completed (`[=======>.......] 45.2%`)
  - Transferred data / Total file size (`14.5 MB / 32.1 MB`)
  - Live download speed (`MB/s`)
  - Estimated time remaining (ETA in seconds)
- 📁 **Configurable Download Destination**: View your current download directory at a glance and change it on the fly from the menu.
- 🛡️ **Encoding-Safe & Robust**: Engineered to avoid Windows console `cp1252` encoding crashes and YouTube JavaScript engine throttling.

---

## 🖥️ Menu Interface Preview

```text
=======================================================
             AP-DLP PYTHON DOWNLOADER (BY Abhijeet Pandey)
=======================================================
[Status] FFmpeg is active! High quality video & audio merging enabled.
-------------------------------------------------------
Active Download Directory:
  -> C:\Users\YourUser\Desktop\downloads
-------------------------------------------------------
1. Download Video (Select Quality: 1080p, 720p, 480p, 360p, Best)
2. Download Audio Only (Extract MP3 / Audio)
3. Download Entire Playlist
4. Download Video with Subtitles
5. Change Download Directory
6. Exit
Select an option (1-6): 
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** installed on your system.
- **Node.js** (Optional but recommended for YouTube JavaScript signature decryption).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/abhijeetrentpur/ap-dlp.git
   cd ap-dlp
   ```

2. **(Optional) Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 📖 Usage

Run the script using Python:

```bash
python downloader.py
```

### Download Workflow

1. **Choose an option** from `1` to `6`.
2. **If downloading a video (Option 1, 3, or 4)**:
   - Select resolution:
     - `1` : Best Available (Highest resolution, e.g. 1080p / 2K / 4K)
     - `2` : 1080p (Full HD)
     - `3` : 720p (HD)
     - `4` : 480p (Standard)
     - `5` : 360p (Low / Data Saver)
3. **Paste the URL** (Video or Playlist).
4. Watch the live progress bar:
   ```text
   Progress: [=================>........] 68.4% | 34.2 MB/50.0 MB | 8.24 MB/s | ETA: 2s
   ```
5. Your file will be saved in the `downloads/` folder (or your custom directory).

---

## 📂 Project Structure

```text
├── downloader.py       # Main interactive CLI application
├── requirements.txt    # Project dependencies (ap-dlp, static-ffmpeg)
├── .gitignore          # Git exclusion rules for media files & pycache
└── README.md           # Documentation
```

---

## ⚙️ Configuration & Under the Hood

- **Engine**: Built upon [`ap-dlp`](https://github.com/abhijeetrentpur/ap-dlp), the gold-standard command-line audio/video downloader.
- **Stream Merging**: Separate DASH video and audio streams are automatically merged into clean, playback-ready MP4 containers using bundled `static-ffmpeg`.
- **Cross-Platform Compatibility**: Tested and optimized for Windows (PowerShell/CMD), Linux, and macOS.

---

## 📜 License

This project is licensed under the **MIT License** - feel free to use, modify, and distribute for personal and educational use.

---

## 👤 Author

**Abhijeet Pandey**
- GitHub: [@abhijeetrentpur](https://github.com/abhijeetrentpur)

---

⭐ *If you found this project helpful, please consider giving it a star on GitHub!*
