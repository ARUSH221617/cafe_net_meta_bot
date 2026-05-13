from dataclasses import dataclass, field

from app.core.config import Settings
from app.services.github import GitHubRepositoryResult
from app.services.youtube import YouTubeVideoResult


@dataclass
class RuntimeState:
    settings: Settings
    github_results: dict[int, list[GitHubRepositoryResult]] = field(default_factory=dict)
    youtube_results: dict[int, list[YouTubeVideoResult]] = field(default_factory=dict)
    payment_due_by_chat: dict[int, int] = field(default_factory=dict)
    ticket_title_by_chat: dict[int, str] = field(default_factory=dict)
    ticket_reply_by_chat: dict[int, int] = field(default_factory=dict)
    admin_due_target_by_chat: dict[int, int] = field(default_factory=dict)
    admin_due_title_by_chat: dict[int, str] = field(default_factory=dict)
    admin_ticket_reply_by_chat: dict[int, int] = field(default_factory=dict)
