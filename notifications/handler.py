import logging
from typing import Optional
from aiogram import Bot
from database.models import Subscription
from monitoring.core import MarketData

logger = logging.getLogger(__name__)

class NotificationHandler:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_alert(self, user_id: int, symbol: str, event: dict,  MarketData) -> bool:
        try:
            await self.bot.send_message(chat_id=user_id, text=self._format_alert(symbol, event, market_data), parse_mode="HTML")
            return True
        except Exception as e:
            logger.error("Failed to send alert to user %d: %s", user_id, e)
            return False

    def _format_alert(self, symbol: str, event: dict,  MarketData) -> str:
        symbol_display = symbol.replace("_", "/")
        emoji = {"price_change_percent": "🔔", "price_level_reached": "🎯", "volume_spike": "📊", "orderbook_depth": "📚"}.get(event["type"], "⚡")
        lines = [f"{emoji} <b>Signal: {symbol_display}</b>", f"", f"💰 Price: <code>${data.last:.6f}</code>"]
        if event["type"] == "price_change_percent":
            lines.append(f"{'📈' if event['direction'] == 'up' else '📉'} Change: <b>{event['value']:+.2f}%</b>")
            lines.append(f"🕐 24h: <b>{data.change_24h:+.2f}%</b>")
        elif event["type"] == "volume_spike":
            lines.append(f"{'🔥' if event['direction'] == 'up' else '❄️'} Volume: <b>{event['value']:+.1f}%</b>")
            lines.append(f"📦 24h Vol: <code>{data.volume_24h:,.0f}</code>")
        elif event["type"] == "orderbook_depth":
            lines.append(f"{'🟢' if event['direction'] == 'bid' else '🔴'} Wall: <b>{event['value']:,.0f}</b>")
        if data.spread_pct > 0:
            lines.append(f"↔️ Spread: <b>{data.spread_pct:.3f}%</b>")
        lines.extend(["", f"<i>{event['message']}</i>", f"<small>Time: {data.timestamp.strftime('%H:%M:%S')}</small>"])
        return "\n".join(lines)

    async def send_welcome(self, user_id: int, username: Optional[str] = None):
        name = username or "Trader"
        await self.bot.send_message(chat_id=user_id, text=f"👋 Hello, {name}!\n\nNonKYC Monitor Bot is active.\n\n📋 Commands:\n/start, /subscribe, /list, /help\n\nExample:\n<code>/subscribe XLA/USDT +5%</code>", parse_mode="HTML")

    async def send_confirmation(self, user_id: int, sub: Subscription, action: str = "created"):
        symbol = sub.symbol.replace("_", "/")
        actions = {"created": "✅ Created", "updated": "🔄 Updated", "deleted": "🗑️ Deleted", "disabled": "⏸️ Disabled", "enabled": "▶️ Enabled"}
        direction = " 📈" if sub.direction == "up" else " 📉" if sub.direction else ""
        msg = f"{actions.get(action, '✓ Done')}\n\n📊 Pair: <b>{symbol}</b>\n🎯 Condition: <code>{sub.condition_type.value}</code>\n📐 Value: <code>{sub.condition_value}</code>{direction}\n⚡ Status: <b>{'Active' if sub.is_active else 'Inactive'}</b>"
        await self.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")

    async def send_list(self, user_id: int, subscriptions: list):
        if not subscriptions:
            await self.bot.send_message(chat_id=user_id, text="📭 No active subscriptions. Use /subscribe to add one.")
            return
        lines = ["📋 <b>Your Subscriptions:</b>", ""]
        for i, sub in enumerate(subscriptions, 1):
            symbol = sub.symbol.replace("_", "/")
            status = "✅" if sub.is_active else "⏸️"
            direction = " 📈" if sub.direction == "up" else " 📉" if sub.direction else ""
            lines.append(f"{i}. {status} <b>{symbol}</b>\n   ├─ {sub.condition_type.value}: {sub.condition_value}{direction}\n   └─ ID: <code>{sub.id}</code>")
            if i < len(subscriptions):
                lines.append("")
        lines.append("\n<i>Manage: /unsubscribe &lt;ID&gt;</i>")
        await self.bot.send_message(chat_id=user_id, text="\n".join(lines), parse_mode="HTML")
