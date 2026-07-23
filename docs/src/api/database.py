"""MySQL 异步连接池 — 仅连接池生命周期，DDL 见 db/schema.sql。"""

import aiomysql
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class AsyncDatabaseConnection:
    """异步数据库连接池（FastAPI 使用）。

    生命周期：
        startup  → get_pool()
        request  → get_connection() → use → close_connection()
        shutdown → close_pool()
    """

    _pool = None

    @staticmethod
    async def get_pool():
        if AsyncDatabaseConnection._pool is None:
            try:
                AsyncDatabaseConnection._pool = await aiomysql.create_pool(
                    host=Config.DATABASE_HOST,
                    port=Config.DATABASE_PORT,
                    user=Config.DATABASE_USER,
                    password=Config.DATABASE_PASSWORD,
                    db=Config.DATABASE_NAME,
                    charset='utf8mb4',
                    minsize=5,
                    maxsize=20,
                    autocommit=False,
                )
                logger.info(
                    f"DATABASE_POOL_CREATED host={Config.DATABASE_HOST} "
                    f"port={Config.DATABASE_PORT} db={Config.DATABASE_NAME}"
                )
            except Exception as e:
                logger.error(f"DATABASE_POOL_CREATE_ERROR error={str(e)}")
                raise
        return AsyncDatabaseConnection._pool

    @staticmethod
    async def get_connection():
        pool = await AsyncDatabaseConnection.get_pool()
        conn = await pool.acquire()
        # 清理残留事务：autocommit=False 下，连接可能携带前一次使用的未提交事务。
        # 如 Repository 层只读查询后未显式 commit/rollback，下一个拿到同连接的使用者
        # 会被卷入旧快照（REPEATABLE READ），INSERT → COMMIT → 重查看不到。
        try:
            await conn.rollback()
        except Exception:
            pass
        # 连接健康检查：AI 调用期间连接可能空闲 30-120s，
        # MySQL 可能关闭空闲连接，aiomysql 不会自动检测。
        # ping(reconnect=True) 确保拿到的是活连接。
        try:
            await conn.ping(reconnect=True)
        except Exception:
            # ping 失败（连接已断开且重连也失败），丢弃并从池中重新获取
            logger.warning("DATABASE_CONNECTION_STALE — 丢弃脏连接，重新获取")
            try:
                pool.release(conn)
            except Exception:
                pass
            conn = await pool.acquire()
            await conn.ping(reconnect=True)
        logger.debug("DATABASE_CONNECTION_ACQUIRED")
        return conn

    @staticmethod
    async def close_connection(conn):
        if AsyncDatabaseConnection._pool and conn:
            try:
                AsyncDatabaseConnection._pool.release(conn)
                logger.debug("DATABASE_CONNECTION_RELEASED")
            except Exception as e:
                logger.warning(f"DATABASE_CONNECTION_RELEASE_ERROR error={str(e)}")

    @staticmethod
    async def close_pool():
        if AsyncDatabaseConnection._pool:
            try:
                AsyncDatabaseConnection._pool.close()
                await AsyncDatabaseConnection._pool.wait_closed()
                AsyncDatabaseConnection._pool = None
                logger.info("DATABASE_POOL_CLOSED")
            except Exception as e:
                logger.error(f"DATABASE_POOL_CLOSE_ERROR error={str(e)}")
                raise
