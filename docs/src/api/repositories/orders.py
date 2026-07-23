"""orders 表操作。自管连接生命周期，只抛 AppError 子类。"""

import uuid

from database import AsyncDatabaseConnection
from utils.exceptions import DatabaseError
from utils.logger import get_logger, mask_openid

logger = get_logger(__name__)


class OrderRepository:
    """orders 表 CRUD。每个方法自管连接。"""

    @staticmethod
    async def create(
        openid: str, out_trade_no: str, plan: int, amount: int, times: int,
        diagnosis_id: str | None = None,
    ) -> str:
        """INSERT 订单，返回 order_id (UUID)。

        diagnosis_id 可选——关联具体诊断，用于支付回调标记 is_paid。
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()
            order_id = str(uuid.uuid4())

            await cursor.execute(
                "INSERT INTO orders (id, openid, out_trade_no, plan, times, amount, diagnosis_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (order_id, openid, out_trade_no, plan, times, amount, diagnosis_id),
            )
            await conn.commit()

            logger.info(
                f"ORDER_CREATED order_id={order_id} out_trade_no={out_trade_no} "
                f"openid={mask_openid(openid)} plan={plan} amount={amount}"
            )
            return order_id
        except Exception as e:
            if conn:
                await conn.rollback()
            raise DatabaseError(operation="创建订单") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def get_by_out_trade_no(out_trade_no: str) -> dict | None:
        """按商户订单号查订单，返回 dict 或 None。"""
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                "SELECT id, openid, resume_id, out_trade_no, transaction_id, "
                "plan, times, status, amount, diagnosis_id, created_at, paid_at "
                "FROM orders WHERE out_trade_no = %s",
                (out_trade_no,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "openid": row[1],
                "resume_id": row[2],
                "out_trade_no": row[3],
                "transaction_id": row[4],
                "plan": row[5],
                "times": row[6],
                "status": row[7],
                "amount": row[8],
                "diagnosis_id": row[9],
                "created_at": row[10],
                "paid_at": row[11],
            }
        except Exception as e:
            raise DatabaseError(operation="查询订单") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)

    @staticmethod
    async def mark_paid(
        out_trade_no: str, transaction_id: str
    ) -> dict | None:
        """标记订单已支付，返回 {(openid, times)} 用于发放次数。

        幂等：同 transaction_id 已 paid → 返回 None（不重复发放）。
        乐观锁：仅 status='pending' 时可更新。

        Returns:
            {"openid": str, "times": int} — 用于后续发放次数
            None — 幂等（同 transaction_id 已 paid）
        """
        conn = None
        cursor = None
        try:
            conn = await AsyncDatabaseConnection.get_connection()
            cursor = await conn.cursor()
            await cursor.execute("START TRANSACTION")

            # 行锁读
            await cursor.execute(
                "SELECT openid, times, status, transaction_id, diagnosis_id "
                "FROM orders WHERE out_trade_no = %s FOR UPDATE",
                (out_trade_no,),
            )
            order = await cursor.fetchone()
            if not order:
                raise DatabaseError(operation="标记支付", details={"context": f"订单不存在: {out_trade_no}"})

            openid, times, status, existing_txn_id, diagnosis_id = order

            # 幂等：已支付 + 同 transaction_id
            if status == "paid" and existing_txn_id == transaction_id:
                logger.info(
                    f"ORDER_ALREADY_PAID out_trade_no={out_trade_no} "
                    f"transaction_id={transaction_id}"
                )
                await conn.commit()
                return None

            if status != "pending":
                raise DatabaseError(
                    operation="标记支付",
                    details={"context": f"订单状态异常: {status}"},
                )

            await cursor.execute(
                "UPDATE orders SET status = 'paid', transaction_id = %s, "
                "paid_at = NOW() "
                "WHERE out_trade_no = %s AND status = 'pending'",
                (transaction_id, out_trade_no),
            )

            if cursor.rowcount == 0:
                # 并发冲突：重新检查是否已由其他请求处理
                await cursor.execute(
                    "SELECT status, transaction_id FROM orders "
                    "WHERE out_trade_no = %s",
                    (out_trade_no,),
                )
                check = await cursor.fetchone()
                if check and check[0] == "paid" and check[1] == transaction_id:
                    logger.info(
                        f"ORDER_CONCURRENT_PAID out_trade_no={out_trade_no}"
                    )
                    await conn.commit()
                    return None
                raise DatabaseError(
                    operation="标记支付",
                    details={"context": "并发冲突或状态异常"},
                )

            await conn.commit()
            logger.info(
                f"ORDER_PAID out_trade_no={out_trade_no} "
                f"transaction_id={transaction_id} "
                f"openid={mask_openid(openid)} times={times}"
            )
            return {"openid": openid, "times": times, "diagnosis_id": diagnosis_id}
        except Exception as e:
            if conn:
                await conn.rollback()
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(operation="标记支付") from e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                await AsyncDatabaseConnection.close_connection(conn)
