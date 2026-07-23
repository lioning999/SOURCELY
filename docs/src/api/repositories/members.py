"""members 表操作。自管连接生命周期，只抛 AppError 子类。"""

from typing import Optional

from database import AsyncDatabaseConnection
from utils.exceptions import DatabaseError
from utils.logger import get_logger, mask_openid

logger = get_logger(__name__)


class MemberRepository:
    """members 表 CRUD。每个方法自管连接。"""

    @staticmethod
    async def init_member(
        openid: str, nickname: Optional[str] = None, avatar_url: Optional[str] = None
    ) -> bool:
        """幂等初始化用户。原子 INSERT IGNORE，无竞态。
        返回 True=新用户，False=已存在。"""
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "INSERT IGNORE INTO members (openid, nickname, avatar_url) "
                "VALUES (%s, %s, %s)",
                (openid, nickname, avatar_url),
            )
            await conn.commit()
            is_new = cursor.rowcount == 1

            logger.info(
                f"MEMBER_INIT openid={mask_openid(openid)} is_new={is_new}"
            )
            return is_new
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="初始化用户") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def add_optimize_quota(openid: str, count: int) -> None:
        """给用户增加优化次数。先确保 member 行存在（兼容旧用户未初始化场景）。"""
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            # INSERT IGNORE 兼容 member 行不存在的旧用户
            await cursor.execute(
                "INSERT IGNORE INTO members (openid) VALUES (%s)",
                (openid,),
            )
            await cursor.execute(
                "UPDATE members SET optimize_remain = optimize_remain + %s "
                "WHERE openid = %s",
                (count, openid),
            )
            await conn.commit()

            logger.info(
                f"MEMBER_QUOTA_ADDED openid={mask_openid(openid)} count={count}"
            )
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="增加优化次数") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def get_by_openid(openid: str) -> dict | None:
        """查用户，返回配额等字段。不存在返回 None。"""
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "SELECT openid, nickname, avatar_url, optimize_remain, "
                "preview_remain, created_at "
                "FROM members WHERE openid = %s",
                (openid,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "openid": row[0],
                "nickname": row[1],
                "avatar_url": row[2],
                "optimize_remain": row[3],
                "preview_remain": row[4],
                "created_at": row[5],
            }
        except Exception as e:
            raise DatabaseError(operation="查询用户") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def deduct_optimize_quota(openid: str) -> bool:
        """扣减 1 次优化次数。原子 UPDATE WHERE optimize_remain > 0。

        Returns:
            True=扣减成功，False=次数不足
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "UPDATE members SET optimize_remain = optimize_remain - 1 "
                "WHERE openid = %s AND optimize_remain > 0",
                (openid,),
            )
            await conn.commit()
            deducted = cursor.rowcount == 1

            logger.info(
                f"MEMBER_OPTIMIZE_DEDUCT openid={mask_openid(openid)} "
                f"deducted={deducted}"
            )
            return deducted
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="扣减优化次数") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)
