# VIDEO DOWNLOADER BOT

A polished Telegram interface around yt-dlp, based on the supplied AP-DLP project.

## Included
- Beautiful `/start` dashboard
- New Download flow with quality buttons
- Best / 1080p / 720p / 480p / 360p / MP3 / Playlist
- Live progress with percentage, speed and ETA
- Parallel fragment downloads for faster supported downloads
- Automatic upload as video/document
- User download counters
- SQLite user database
- User settings/help/history screens
- Admin panel with statistics and user count
- `/broadcast` admin announcement command
- `/cancel`
- Temporary download cleanup

## Setup

1. Create a Telegram bot with @BotFather and copy the token.
2. Install dependencies:
```bash
python -m pip install -r requirements.txt
```
3. Set environment variables:
```bash
export BOT_TOKEN="YOUR_BOT_TOKEN"
export ADMIN_IDS="123456789"
```
Windows PowerShell:
```powershell
$env:BOT_TOKEN="YOUR_BOT_TOKEN"
$env:ADMIN_IDS="123456789"
```
4. Run:
```bash
python bot.py
```

## Speed
`CONCURRENT_FRAGMENTS=8` enables parallel fragment downloading where the extractor/server supports it. Increase cautiously (for example 12 or 16); higher is not always faster and can trigger server throttling.

## Admin
Admin IDs are numeric Telegram user IDs in `ADMIN_IDS`, separated by commas. Admins get the Admin Panel and can use `/broadcast`.

## Notes
- Actual supported sites and formats depend on the current yt-dlp extractors.
- DRM-protected services generally cannot be downloaded by yt-dlp.
- Telegram/API upload limits and your hosting bandwidth/storage still apply.
- Only download media you are authorized to download.


## Video playback fix
This version bundles FFmpeg through `imageio-ffmpeg` and converts downloaded video to Telegram-compatible **H.264 video + AAC audio in MP4** before upload. This prevents black-screen, missing-audio, and unsupported-codec playback on Telegram clients.
