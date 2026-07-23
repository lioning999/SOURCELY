"""diagnoses 表操作。自管连接生命周期，只抛 AppError 子类。"""

import json
import uuid

from database import AsyncDatabaseConnection
from utils.exceptions import DatabaseError
from utils.logger import get_logger, mask_openid

logger = get_logger(__name__)


class DiagnosisRepository:
    """diagnoses 表 CRUD。每个方法自管连接。"""

    @staticmethod
    async def create(resume_id: str, openid: str, diagnose_result: str) -> str:
        """INSERT 诊断结果，返回 diagnosis_id (UUID)。

        写入: id, resume_id, openid, diagnose_result
        不写: optimized_text(NULL), interview_qa(NULL) — 等 optimize 阶段 UPDATE
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()
            diagnosis_id = str(uuid.uuid4())

            await cursor.execute(
                "INSERT INTO diagnoses (id, resume_id, openid, diagnose_result) "
                "VALUES (%s, %s, %s, %s)",
                (diagnosis_id, resume_id, openid, diagnose_result),
            )
            await conn.commit()

            logger.info(
                f"DIAGNOSIS_CREATED diagnosis_id={diagnosis_id} "
                f"resume_id={resume_id} openid={mask_openid(openid)} "
                f"result_len={len(diagnose_result)}"
            )
            return diagnosis_id
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="保存诊断结果") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def upsert(openid: str, resume_id: str, diagnose_result: str) -> tuple[str, bool]:
        """写入新诊断。仅清理 unpaid + incomplete 的旧记录，保留已付费或已完成的。

        返回 (diagnosis_id, is_rediagnosis)。
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()
            await cursor.execute("START TRANSACTION")

            # 只删没付过钱且没走完流程的记录（保护已付费和已完成记录）
            await cursor.execute(
                "DELETE FROM diagnoses WHERE openid = %s "
                "AND interview_questions IS NULL AND is_paid = 0",
                (openid,),
            )
            deleted = cursor.rowcount

            # 写入新记录
            diagnosis_id = str(uuid.uuid4())
            await cursor.execute(
                "INSERT INTO diagnoses (id, resume_id, openid, diagnose_result) "
                "VALUES (%s, %s, %s, %s)",
                (diagnosis_id, resume_id, openid, diagnose_result),
            )
            await conn.commit()

            logger.info(
                f"DIAGNOSIS_UPSERTED diagnosis_id={diagnosis_id} "
                f"openid={mask_openid(openid)} resume_id={resume_id} "
                f"deleted_old={deleted} result_len={len(diagnose_result)}"
            )
            return diagnosis_id, deleted > 0
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="覆盖诊断结果") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def get_by_id(diagnosis_id: str) -> dict | None:
        """按 diagnosis_id 查诊断，返回完整 dict。不存在返回 None。"""
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "SELECT id, resume_id, openid, diagnose_result, optimized_text, "
                "before_after_pairs, interview_qa, interview_questions, "
                "is_paid, created_at, optimized_at "
                "FROM diagnoses WHERE id = %s",
                (diagnosis_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            def _safe_json(val):
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except json.JSONDecodeError:
                        pass
                return val

            return {
                "id": row[0],
                "resume_id": row[1],
                "openid": row[2],
                "diagnose_result": _safe_json(row[3]),
                "optimized_text": row[4],
                "before_after_pairs": _safe_json(row[5]),
                "interview_qa": _safe_json(row[6]),
                "interview_questions": _safe_json(row[7]),
                "is_paid": row[8],
                "created_at": row[9],
                "optimized_at": row[10],
            }
        except Exception as e:
            raise DatabaseError(operation="查询诊断") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def update_optimized_text(
        diagnosis_id: str, openid: str, optimized_text: str,
        before_after_pairs: str | None = None,
    ) -> bool:
        """更新优化文本 + before/after 对比对。校验归属。

        Returns:
            True=更新成功，False=诊断不存在或不属于该用户
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "UPDATE diagnoses SET optimized_text = %s, "
                "before_after_pairs = %s, optimized_at = NOW() "
                "WHERE id = %s AND openid = %s",
                (optimized_text, before_after_pairs, diagnosis_id, openid),
            )
            await conn.commit()

            updated = cursor.rowcount == 1
            if updated:
                logger.info(
                    f"DIAGNOSIS_OPTIMIZED diagnosis_id={diagnosis_id} "
                    f"openid={mask_openid(openid)} text_len={len(optimized_text)}"
                )
            return updated
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="更新优化文本") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def update_interview_qa(
        diagnosis_id: str, openid: str, interview_qa: str
    ) -> bool:
        """更新诊断记录的追问预判。校验归属（openid 必须匹配）。

        Returns:
            True=更新成功，False=诊断不存在或不属于该用户
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "UPDATE diagnoses SET interview_qa = %s "
                "WHERE id = %s AND openid = %s",
                (interview_qa, diagnosis_id, openid),
            )
            await conn.commit()

            updated = cursor.rowcount == 1
            if updated:
                logger.info(
                    f"DIAGNOSIS_QA_UPDATED diagnosis_id={diagnosis_id} "
                    f"openid={mask_openid(openid)}"
                )
            return updated
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="更新追问预判") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def update_interview_questions(
        diagnosis_id: str, openid: str, interview_questions: str
    ) -> bool:
        """更新诊断记录的模拟面试题。校验归属（openid 必须匹配）。

        Returns:
            True=更新成功，False=诊断不存在或不属于该用户
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "UPDATE diagnoses SET interview_questions = %s "
                "WHERE id = %s AND openid = %s",
                (interview_questions, diagnosis_id, openid),
            )
            await conn.commit()

            updated = cursor.rowcount == 1
            if updated:
                logger.info(
                    f"DIAGNOSIS_INTERVIEW_QUESTIONS_UPDATED diagnosis_id={diagnosis_id} "
                    f"openid={mask_openid(openid)}"
                )
            return updated
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="更新模拟面试题") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def mark_paid(diagnosis_id: str, openid: str) -> bool:
        """标记诊断已付费。原子 UPDATE，校验归属。

        Returns:
            True=标记成功，False=诊断不存在或不属于该用户
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "UPDATE diagnoses SET is_paid = 1 "
                "WHERE id = %s AND openid = %s AND is_paid = 0",
                (diagnosis_id, openid),
            )
            await conn.commit()

            updated = cursor.rowcount == 1
            if updated:
                logger.info(
                    f"DIAGNOSIS_PAID diagnosis_id={diagnosis_id} "
                    f"openid={mask_openid(openid)}"
                )
            return updated
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="标记诊断付费") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def delete_other_diagnoses(openid: str, keep_id: str) -> int:
        """删除该用户除 keep_id 外的所有诊断记录。流程走完时调用。

        Returns:
            删除的记录数
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "DELETE FROM diagnoses WHERE openid = %s AND id != %s",
                (openid, keep_id),
            )
            await conn.commit()
            deleted = cursor.rowcount

            if deleted > 0:
                logger.info(
                    f"DIAGNOSIS_CLEANUP openid={mask_openid(openid)} "
                    f"keep_id={keep_id} deleted={deleted}"
                )
            return deleted
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="清理旧诊断") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def get_latest_by_openid(openid: str) -> dict | None:
        """按 openid 查最近一条已付费诊断（首页记录）。

        未付费记录不进首页。返回摘要 dict，不存在返回 None。
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "SELECT id, created_at, diagnose_result, optimized_text, "
                "interview_qa, interview_questions "
                "FROM diagnoses WHERE openid = %s AND is_paid = 1 "
                "ORDER BY created_at DESC LIMIT 1",
                (openid,),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            def _safe_json(val):
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except json.JSONDecodeError:
                        pass
                return val

            return {
                "id": row[0],
                "created_at": row[1],
                "diagnose_result": _safe_json(row[2]),
                "optimized_text": row[3],
                "interview_qa": _safe_json(row[4]),
                "interview_questions": _safe_json(row[5]),
            }
        except Exception as e:
            raise DatabaseError(operation="查询最新诊断") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)
