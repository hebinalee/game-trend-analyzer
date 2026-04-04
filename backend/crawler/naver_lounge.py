"""
네이버 게임 라운지 크롤러

네이버 라운지 페이지 구조가 변경될 경우 아래 SELECTORS 상수를 업데이트하세요.
선택자 실패 시 명확한 에러 메시지와 함께 로그를 출력합니다.
"""
import logging
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.game import Game
from models.post import Post
from crawler.utils import random_delay, clean_text, parse_date

logger = logging.getLogger(__name__)

# CSS 선택자 상수 - 네이버 업데이트 시 이 부분을 수정하세요
SELECTORS = {
    "post_list": ".article_list",
    "post_item": ".article_item",
    "post_title": ".title",
    "post_author": ".nickname",
    "post_date": ".date",
    "post_like": ".like_count",
    "post_comment": ".comment_count",
    "post_link": "a",
    "post_content": ".article_content, .se-main-container",
    "next_page": ".btn_next:not([disabled])",
}

LOUNGE_BOARD_URL = "https://game.naver.com/lounge/{lounge_id}/board/all"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def crawl_game_lounge(game: Game, days_back: int = 1) -> list[dict]:
    """
    특정 게임의 라운지에서 최근 days_back일 게시글을 수집한다.
    반환: Post 생성에 필요한 dict 리스트
    """
    posts = []
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    url = LOUNGE_BOARD_URL.format(lounge_id=game.lounge_id)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()

            logger.info(f"[{game.name}] 크롤링 시작: {url}")
            await page.goto(url, timeout=30000)
            await random_delay(1, 2)

            page_num = 0
            stop = False
            while not stop:
                page_num += 1
                try:
                    await page.wait_for_selector(SELECTORS["post_list"], timeout=10000)
                except PlaywrightTimeoutError:
                    logger.error(
                        f"[{game.name}] 선택자 '{SELECTORS['post_list']}' 를 찾을 수 없습니다. "
                        "네이버 라운지 페이지 구조가 변경되었을 수 있습니다."
                    )
                    break

                items = await page.query_selector_all(SELECTORS["post_item"])
                if not items:
                    logger.warning(f"[{game.name}] 게시글 목록이 비어 있습니다 (page {page_num}).")
                    break

                for item in items:
                    try:
                        # 날짜 파싱
                        date_el = await item.query_selector(SELECTORS["post_date"])
                        date_text = await date_el.inner_text() if date_el else None
                        posted_at = parse_date(date_text)

                        if posted_at and posted_at < cutoff:
                            stop = True
                            break

                        # 링크 및 post_id
                        link_el = await item.query_selector(SELECTORS["post_link"])
                        href = await link_el.get_attribute("href") if link_el else None
                        post_id = href.split("/")[-1] if href else None
                        if not post_id:
                            continue

                        # 제목
                        title_el = await item.query_selector(SELECTORS["post_title"])
                        title = await title_el.inner_text() if title_el else None

                        # 작성자
                        author_el = await item.query_selector(SELECTORS["post_author"])
                        author = await author_el.inner_text() if author_el else None

                        # 좋아요/댓글 수
                        like_el = await item.query_selector(SELECTORS["post_like"])
                        like_count = int((await like_el.inner_text()).strip() or "0") if like_el else 0

                        comment_el = await item.query_selector(SELECTORS["post_comment"])
                        comment_count = int((await comment_el.inner_text()).strip() or "0") if comment_el else 0

                        posts.append({
                            "game_id": game.id,
                            "post_id": f"{game.lounge_id}_{post_id}",
                            "title": clean_text(title),
                            "content": "",  # 상세 페이지 크롤링은 생략 (부하 최소화)
                            "author": clean_text(author, 100),
                            "like_count": like_count,
                            "comment_count": comment_count,
                            "post_type": "게시글",
                            "posted_at": posted_at,
                            "crawled_at": datetime.utcnow(),
                        })
                    except Exception as e:
                        logger.warning(f"[{game.name}] 게시글 파싱 오류: {e}")
                        continue

                if stop:
                    break

                # 다음 페이지
                next_btn = await page.query_selector(SELECTORS["next_page"])
                if not next_btn:
                    break

                await next_btn.click()
                await random_delay(1, 3)

            await browser.close()

    except Exception as e:
        logger.error(f"[{game.name}] 크롤링 중 오류 발생: {e}")

    logger.info(f"[{game.name}] 수집 완료: {len(posts)}개 게시글")
    return posts


async def crawl_all_games(db_session: AsyncSession) -> None:
    """
    DB의 모든 active 게임에 대해 crawl_game_lounge를 순차 실행하고 DB에 저장한다.
    """
    result = await db_session.execute(select(Game).where(Game.is_active == True))
    games = result.scalars().all()

    for game in games:
        try:
            posts_data = await crawl_game_lounge(game, days_back=1)

            # 중복 제외하고 저장
            for post_dict in posts_data:
                existing = await db_session.execute(
                    select(Post).where(Post.post_id == post_dict["post_id"])
                )
                if existing.scalar_one_or_none():
                    continue
                db_session.add(Post(**post_dict))

            await db_session.commit()
            logger.info(f"[{game.name}] DB 저장 완료")

        except Exception as e:
            await db_session.rollback()
            logger.error(f"[{game.name}] DB 저장 오류: {e}")
            continue

        await random_delay(2, 4)
