import asyncio
import random
import re
from datetime import datetime


async def random_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
    """요청 간 랜덤 딜레이를 적용한다."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


def clean_text(text: str | None, max_length: int = 1000) -> str:
    """텍스트를 정제하고 최대 길이로 자른다."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length]


def parse_date(date_str: str | None) -> datetime | None:
    """다양한 날짜 형식을 파싱한다."""
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        "%Y.%m.%d %H:%M",
        "%Y.%m.%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None
