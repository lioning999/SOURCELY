"""users 表数据访问 — Google 登录用户的增改查。"""

from typing import Any

import aiomysql  # type: ignore[import-untyped]

from database import AsyncDatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


class UserRepository:
    """users 表 CRUD。事务由 service 层控制。"""

    async def get_by_google_id(self, google_id: str) -> dict[str, Any] | None:
        """按 google_id 查用户，无记录返回 None。"""
        conn = await AsyncDatabaseConnection.get_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT id, google_id, email, name, avatar_url, created_at, last_login FROM users WHERE google_id=%s",
                    (google_id,),
                )
                return await cur.fetchone()
        finally:
            await AsyncDatabaseConnection.close_connection(conn)

    async def create(self, google_id: str, email: str | None = None,
                     name: str | None = None, avatar_url: str | None = None) -> int:
        """创建新用户，返回自增 ID。"""
        conn = await AsyncDatabaseConnection.get_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "INSERT INTO users (google_id, email, name, avatar_url) VALUES (%s, %s, %s, %s)",
                    (google_id, email, name, avatar_url),
                )
                await conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
        except Exception:
            await conn.rollback()
            raise
        finally:
            await AsyncDatabaseConnection.close_connection(conn)

    async def update_last_login(self, google_id: str, name: str | None = None,
                                avatar_url: str | None = None) -> None:
        """更新 last_login，同时刷新 name 和 avatar（Google 账号可能更新）。"""
        conn = await AsyncDatabaseConnection.get_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "UPDATE users SET last_login=NOW(), name=%s, avatar_url=%s WHERE google_id=%s",
                    (name, avatar_url, google_id),
                )
                await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        finally:
            await AsyncDatabaseConnection.close_connection(conn)
