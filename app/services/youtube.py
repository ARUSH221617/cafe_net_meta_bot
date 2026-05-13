from dataclasses import dataclass
from typing import Optional
import asyncio
import yt_dlp


@dataclass(frozen=True)
class YouTubeVideoResult:
    video_id: str
    title: str
    description: str = ""
    channel_name: str = ""
    channel_url: str = ""
    duration: str = ""  # e.g. "3:25"
    views: int = 0
    published_at: str = ""  # ISO date (or ISO datetime)
    thumbnail_url: str = ""
    url: str = ""  # https://www.youtube.com/watch?v=...


class YouTubeService:
    """YouTube operations via yt-dlp (no API key required)."""

    def __init__(
        self,
        enabled: bool = True,
        cookies_file: Optional[str] = None,
    ) -> None:
        self.enabled = enabled
        self.cookies_file = cookies_file

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------
    async def search(
        self, query: str, max_results: int = 10
    ) -> list[YouTubeVideoResult]:
        """Search YouTube and return a list of video results."""
        if not self.enabled:
            return []
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._search_sync, query, max_results)

    async def get_video_info(self, video_id: str) -> Optional[YouTubeVideoResult]:
        """Return details for a single video by its ID."""
        if not self.enabled:
            return None
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_video_sync, video_id)

    # (These two methods already use yt-dlp – they stay unchanged)
    async def get_formats(self, video_url: str) -> list[dict]:
        """Return list of available download formats."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_formats, video_url)

    async def get_direct_url(self, video_url: str, format_id: str) -> Optional[str]:
        """Get a (temporary) direct download URL for a specific format."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_url, video_url, format_id)

    # ------------------------------------------------------------------
    # Synchronous helpers
    # ------------------------------------------------------------------
    def _base_ydl_opts(self) -> dict:
        """Common yt-dlp options, including optional cookies."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        return opts

    def _search_sync(self, query: str, max_results: int) -> list[YouTubeVideoResult]:
        ydl_opts = self._base_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        entries = info.get("entries", [])
        results = []
        for entry in entries:
            if not entry or not entry.get("id"):
                continue
            results.append(self._entry_to_result(entry))
        return results

    def _get_video_sync(self, video_id: str) -> Optional[YouTubeVideoResult]:
        ydl_opts = self._base_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
        if not info:
            return None
        return self._entry_to_result(info)

    def _entry_to_result(self, entry: dict) -> YouTubeVideoResult:
        """Map a yt-dlp info dict to a YouTubeVideoResult."""
        vid = entry["id"]
        title = entry.get("title") or ""
        description = entry.get("description") or ""
        channel_name = entry.get("channel") or entry.get("uploader") or ""
        channel_url = entry.get("channel_url") or ""
        duration = self._format_duration(entry.get("duration"))

        # Published date
        ts = entry.get("timestamp")
        if ts:
            from datetime import datetime, timezone

            published = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        else:
            upload_date = entry.get("upload_date")
            if upload_date and len(upload_date) == 8:
                published = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            else:
                published = ""

        views = int(entry.get("view_count") or 0)
        thumbnail = entry.get("thumbnail") or ""
        url = f"https://www.youtube.com/watch?v={vid}"

        return YouTubeVideoResult(
            video_id=vid,
            title=title,
            description=description,
            channel_name=channel_name,
            channel_url=channel_url,
            duration=duration,
            views=views,
            published_at=published,
            thumbnail_url=thumbnail,
            url=url,
        )

    @staticmethod
    def _format_duration(duration_secs: Optional[float]) -> str:
        """Convert seconds to H:MM:SS or M:SS."""
        if not duration_secs:
            return "0:00"
        secs = int(duration_secs)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    # ------------------------------------------------------------------
    # Download helpers (unchanged, already using yt-dlp + cookies)
    # ------------------------------------------------------------------
    def _extract_formats(self, video_url: str) -> list[dict]:
        ydl_opts = self._base_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        formats = []
        for f in info.get("formats", []):
            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                kind = "audio"
            elif f.get("vcodec") != "none" and f.get("acodec") != "none":
                kind = "video"
            else:
                continue
            formats.append(
                {
                    "format_id": f["format_id"],
                    "ext": f["ext"],
                    "resolution": f.get("resolution") or f.get("format_note") or kind,
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                    "kind": kind,
                }
            )
        formats.sort(
            key=lambda x: (
                0 if x["kind"] == "audio" else 1,
                -int(x.get("resolution", "0").replace("p", ""))
                if "p" in str(x.get("resolution", ""))
                else 0,
            )
        )
        return formats

    def _get_url(self, video_url: str, format_id: str) -> Optional[str]:
        ydl_opts = self._base_ydl_opts()
        ydl_opts["format"] = format_id
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        return info.get("url")
