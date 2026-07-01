"""
플랫폼 크롤러 공통 인터페이스

새 플랫폼 크롤러를 추가할 때 이 추상 클래스를 상속하여 구현합니다.
"""
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from models.game import Game


class BaseCrawler(ABC):
    """플랫폼별 크롤러의 공통 인터페이스."""

    # 서브클래스에서 반드시 선언 (예: "steam", "naver")
    platform: str

    def _games_query(self):
        """크롤링 대상 게임 조회 쿼리. 서브클래스에서 필요 시 오버라이드."""
        from sqlalchemy import select
        return select(Game).where(Game.platform == self.platform, Game.is_active == True)

    @abstractmethod
    async def crawl_game(self, game: Game, days_back: int = 1) -> list[dict]:
        """
        특정 게임의 최근 게시글을 수집하고 Post 생성에 필요한 dict 리스트를 반환한다.

        반환하는 각 dict는 다음 키를 포함해야 합니다:
          - post_id (str): 전역 고유 식별자
          - source (str): 플랫폼 식별자 (self.platform 사용)
          - title (str | None)
          - content (str | None)
          - author (str | None)
          - like_count (int)
          - comment_count (int)
          - post_type (str): "review" | "news" | "community" 등
          - posted_at (datetime | None)
        """

    async def crawl_all_games(self, db_session: AsyncSession, days_back: int = 1) -> None:
        """
        DB의 해당 플랫폼 active 게임 전체를 순회하며 크롤링하고 DB에 저장한다.
        공통 저장 로직은 여기서 처리하므로 서브클래스는 crawl_game만 구현하면 됩니다.
        """
        import logging
        from datetime import datetime

        from sqlalchemy import select

        from models.post import Post
        from crawler.utils import random_delay

        logger = logging.getLogger(self.__class__.__name__)

        result = await db_session.execute(self._games_query())
        games = result.scalars().all()

        for game in games:
            try:
                posts_data = await self.crawl_game(game, days_back=days_back)

                for post_dict in posts_data:
                    existing = await db_session.execute(
                        select(Post).where(Post.post_id == post_dict["post_id"])
                    )
                    if existing.scalar_one_or_none():
                        continue
                    db_session.add(Post(
                        game_id=game.id,
                        crawled_at=datetime.utcnow(),
                        **post_dict,
                    ))

                await db_session.commit()
                logger.info(f"[{game.name}] DB 저장 완료 ({len(posts_data)}건)")

            except Exception as e:
                await db_session.rollback()
                logger.error(f"[{game.name}] DB 저장 오류: {e}")

            await random_delay(1, 3)
