"""resumes 表操作。自管连接生命周期，只抛 AppError 子类。"""

import uuid
from typing import Optional

from database import AsyncDatabaseConnection
from utils.exceptions import DatabaseError, ResourceNotFoundError, AuthorizationError
from utils.logger import get_logger, mask_openid

logger = get_logger(__name__)


class ResumeRepository:
    """resumes 表 CRUD。每个方法自管连接。"""

    @staticmethod
    async def create(openid: str, filename: str, raw_text: str, file_size: int) -> str:
        """插入简历，返回 resume_id (UUID)。"""
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()
            resume_id = str(uuid.uuid4())

            await cursor.execute(
                "INSERT INTO resumes (id, openid, filename, raw_text, file_size) "
                "VALUES (%s, %s, %s, %s, %s)",
                (resume_id, openid, filename, raw_text, file_size),
            )
            await conn.commit()

            logger.info(
                f"RESUME_CREATED resume_id={resume_id} "
                f"openid={mask_openid(openid)} "
                f"filename={filename} size={file_size}"
            )
            return resume_id
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="创建简历") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def get_by_id(resume_id: str, openid: str) -> dict:
        """读简历 + 校验归属。一条 SQL 完成归属校验。

        Raises:
            ResourceNotFoundError: 简历不存在
            AuthorizationError: 简历不属于当前用户
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            # 一条 SQL 查归属
            await cursor.execute(
                "SELECT id, openid, filename, raw_text, file_size, created_at "
                "FROM resumes WHERE id = %s AND openid = %s",
                (resume_id, openid),
            )
            row = await cursor.fetchone()

            if row is None:
                # 区分 404 vs 403：单独查 id 是否存在
                await cursor.execute(
                    "SELECT id FROM resumes WHERE id = %s", (resume_id,)
                )
                exists = await cursor.fetchone()
                if exists:
                    raise AuthorizationError(message="无权访问该简历")
                raise ResourceNotFoundError(resource_type="简历", resource_id=resume_id)

            logger.debug(
                f"RESUME_READ resume_id={resume_id} openid={mask_openid(openid)}"
            )
            return {
                "id": row[0],
                "openid": row[1],
                "filename": row[2],
                "raw_text": row[3],
                "file_size": row[4],
                "created_at": row[5],
            }
        except (ResourceNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            raise DatabaseError(operation="读取简历") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)
