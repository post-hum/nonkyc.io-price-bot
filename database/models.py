import aiosqlite
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ConditionType(str, Enum):
    PRICE_CHANGE_PERCENT = "price_change_percent"
    PRICE_LEVEL_REACHED = "price_level_reached"
    VOLUME_SPIKE = "volume_spike"
    ORDERBOOK_DEPTH = "orderbook_depth"

@dataclass
class Subscription:
    id: Optional[int] = None
    user_id: int = 0
    username: Optional[str] = None
    symbol: str = "XLA/USDT"
    condition_type: ConditionType = ConditionType.PRICE_CHANGE_PERCENT
    condition_value: float = 5.0
    direction: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None

    def __post_init__(self):
        self.symbol = self.symbol.replace("/", "_").upper()

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path.replace("sqlite:///", "") if db_path.startswith("sqlite:///") else db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    symbol TEXT NOT NULL DEFAULT 'XLA_USDT',
                    condition_type TEXT NOT NULL DEFAULT 'price_change_percent',
                    condition_value REAL NOT NULL DEFAULT 5.0,
                    direction TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, symbol, condition_type, condition_value, direction)
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sub_user ON subscriptions(user_id, is_active)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sub_symbol ON subscriptions(symbol, is_active)")
            await db.commit()

    async def add_subscription(self, sub: Subscription) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO subscriptions 
                    (user_id, username, symbol, condition_type, condition_value, direction, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sub.user_id, sub.username, sub.symbol, sub.condition_type.value, sub.condition_value, sub.direction, 1 if sub.is_active else 0))
                await db.commit()
                return True
        except Exception as e:
            logger.error("Error adding subscription: %s", e)
            return False

    async def get_active_subscriptions(self, symbol: Optional[str] = None) -> List[Subscription]:
        subscriptions = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                query = "SELECT * FROM subscriptions WHERE is_active=1"
                params = ()
                if symbol:
                    query += " AND symbol=?"
                    params = (symbol.replace("/", "_").upper(),)
                cursor = await db.execute(query, params)
                async for row in cursor:
                    subscriptions.append(Subscription(
                        id=row["id"], user_id=row["user_id"], username=row["username"],
                        symbol=row["symbol"], condition_type=ConditionType(row["condition_type"]),
                        condition_value=row["condition_value"], direction=row["direction"],
                        is_active=bool(row["is_active"]), created_at=row["created_at"]
                    ))
        except Exception as e:
            logger.error("Error fetching subscriptions: %s", e)
        return subscriptions

    async def toggle_subscription(self, sub_id: int, is_active: bool) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE subscriptions SET is_active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (1 if is_active else 0, sub_id))
                await db.commit()
                return True
        except Exception as e:
            logger.error("Error toggling subscription: %s", e)
            return False

    async def get_user_subscriptions(self, user_id: int) -> List[Subscription]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM subscriptions WHERE user_id=? ORDER BY created_at DESC", (user_id,))
                return [Subscription(id=r["id"], user_id=r["user_id"], username=r["username"], symbol=r["symbol"],
                    condition_type=ConditionType(r["condition_type"]), condition_value=r["condition_value"],
                    direction=r["direction"], is_active=bool(r["is_active"]), created_at=r["created_at"]) for r in await cursor.fetchall()]
        except Exception as e:
            logger.error("Error fetching user subscriptions: %s", e)
            return []
