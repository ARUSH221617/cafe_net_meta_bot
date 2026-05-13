from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    items: Sequence[T]
    page: int
    pages: int
    total: int


def paginate(items: Sequence[T], page: int, page_size: int = 5) -> Page[T]:
    safe_page = max(page, 1)
    total = len(items)
    pages = max(ceil(total / page_size), 1)
    start = (safe_page - 1) * page_size
    return Page(items=items[start : start + page_size], page=safe_page, pages=pages, total=total)
