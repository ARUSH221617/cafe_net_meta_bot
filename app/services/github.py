from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx


@dataclass(frozen=True)
class GitHubRepositoryResult:
    full_name: str
    description: str | None
    stars: int
    language: str | None
    html_url: str
    forks_count: int = 0
    watchers_count: int = 0
    open_issues_count: int = 0
    default_branch: str = "main"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    topics: list[str]|None = None
    license: Optional[str] = None
    owner_login: str = ""
    owner_type: str = "User"
    
    def __post_init__(self):
        if self.topics is None:
            object.__setattr__(self, 'topics', [])


class GitHubService:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    async def search_repositories(self, query: str, limit: int = 5) -> list[GitHubRepositoryResult]:
        if not self.enabled:
            return []
        if not query.strip():
            raise ValueError("Search query is required")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
                    headers={"Accept": "application/vnd.github+json"},
                )
                response.raise_for_status()
                payload = response.json()
            
            return [
                GitHubRepositoryResult(
                    full_name=item["full_name"],
                    description=item.get("description"),
                    stars=item.get("stargazers_count", 0),
                    language=item.get("language"),
                    html_url=item["html_url"],
                    forks_count=item.get("forks_count", 0),
                    watchers_count=item.get("watchers_count", 0),
                    open_issues_count=item.get("open_issues_count", 0),
                    default_branch=item.get("default_branch", "main"),
                    created_at=self._parse_datetime(item.get("created_at")),
                    updated_at=self._parse_datetime(item.get("updated_at")),
                    topics=item.get("topics", []),
                    license=self._extract_license(item.get("license")),
                    owner_login=item.get("owner", {}).get("login", ""),
                    owner_type=item.get("owner", {}).get("type", "User"),
                )
                for item in payload.get("items", [])[:limit]
            ]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise Exception("GitHub API rate limit exceeded. Please try again later.")
            elif e.response.status_code == 422:
                raise ValueError("Invalid search query.")
            raise Exception(f"GitHub API error: {e.response.status_code}")
        except httpx.RequestError:
            raise Exception("Unable to connect to GitHub. Please check your internet connection.")

    async def get_repository(self, repo_url: str) -> Optional[GitHubRepositoryResult]:
        """Fetch detailed information about a specific repository."""
        if not self.enabled:
            return None
        
        # Extract owner/repo from URL
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://api.github.com/repos/{repo_path}",
                    headers={"Accept": "application/vnd.github+json"},
                )
                response.raise_for_status()
                repo_data = response.json()
            
            return GitHubRepositoryResult(
                full_name=repo_data["full_name"],
                description=repo_data.get("description"),
                stars=repo_data.get("stargazers_count", 0),
                language=repo_data.get("language"),
                html_url=repo_data["html_url"],
                forks_count=repo_data.get("forks_count", 0),
                watchers_count=repo_data.get("watchers_count", 0),
                open_issues_count=repo_data.get("open_issues_count", 0),
                default_branch=repo_data.get("default_branch", "main"),
                created_at=self._parse_datetime(repo_data.get("created_at")),
                updated_at=self._parse_datetime(repo_data.get("updated_at")),
                topics=repo_data.get("topics", []),
                license=self._extract_license(repo_data.get("license")),
                owner_login=repo_data.get("owner", {}).get("login", ""),
                owner_type=repo_data.get("owner", {}).get("type", "User"),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None  # Repository not found
            elif e.response.status_code == 403:
                raise Exception("GitHub API rate limit exceeded. Please try again later.")
            raise Exception(f"GitHub API error: {e.response.status_code}")
        except httpx.RequestError:
            raise Exception("Unable to connect to GitHub. Please check your internet connection.")

    async def get_repository_tags(self, repo_url: str, limit: int = 10) -> list[dict]:
        """Fetch tags/releases for a repository."""
        if not self.enabled:
            return []
        
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://api.github.com/repos/{repo_path}/tags",
                    params={"per_page": limit},
                    headers={"Accept": "application/vnd.github+json"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError:
            return []

    async def get_repository_issues(self, repo_url: str, limit: int = 5, state: str = "open") -> list[dict]:
        """Fetch issues for a repository."""
        if not self.enabled:
            return []
        
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://api.github.com/repos/{repo_path}/issues",
                    params={"state": state, "per_page": limit, "sort": "updated"},
                    headers={"Accept": "application/vnd.github+json"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError:
            return []

    async def get_repository_commits(self, repo_url: str, limit: int = 5) -> list[dict]:
        """Fetch recent commits for a repository."""
        if not self.enabled:
            return []
        
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://api.github.com/repos/{repo_path}/commits",
                    params={"per_page": limit},
                    headers={"Accept": "application/vnd.github+json"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError:
            return []

    async def get_latest_release(self, repo_url: str) -> Optional[dict]:
        """Fetch the latest release for a repository."""
        if not self.enabled:
            return None
        
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://api.github.com/repos/{repo_path}/releases/latest",
                    headers={"Accept": "application/vnd.github+json"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError:
            return None
    
    async def get_releases(self, repo_url: str, limit: int = 5) -> list[dict]:
        """Fetch recent releases for a repository."""
        if not self.enabled:
            return []
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo_path}/releases",
                params={"per_page": limit},
                headers={"Accept": "application/vnd.github+json"},
            )
            response.raise_for_status()
            return response.json()

    async def get_release(self, repo_url: str, release_id: int) -> Optional[dict]:
        """Fetch a specific release by its ID."""
        if not self.enabled:
            return None
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo_path}/releases/{release_id}",
                headers={"Accept": "application/vnd.github+json"},
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def get_release_asset(self, repo_url: str, asset_id: int) -> Optional[dict]:
        """Fetch a specific release asset by ID (public repos only). Returns asset metadata."""
        if not self.enabled:
            return None
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo_path}/releases/assets/{asset_id}",
                headers={"Accept": "application/vnd.github+json"},  # ← اصلاح شده
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def download_file(self, url: str) -> bytes:
        """Download a file from a URL and return its content."""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    @staticmethod
    def _extract_repo_path(url: str) -> Optional[str]:
        """Extract owner/repo from GitHub URL."""
        import re
        # Match patterns like:
        # https://github.com/owner/repo
        # https://github.com/owner/repo.git
        # https://github.com/owner/repo/
        pattern = r'github\.com/([^/]+/[^/]+?)(?:\.git)?(?:/.*)?$'
        match = re.search(pattern, url)
        return match.group(1) if match else None

    @staticmethod
    def _parse_datetime(date_string: Optional[str]) -> Optional[datetime]:
        """Parse ISO format datetime string."""
        if not date_string:
            return None
        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _extract_license(license_data: Optional[dict]) -> Optional[str]:
        """Extract license name from license data."""
        if not license_data:
            return None
        return license_data.get("spdx_id") or license_data.get("name")