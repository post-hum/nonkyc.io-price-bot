import re
from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from database import Database, Subscription, ConditionType
from notifications import NotificationHandler

router = Router()

def register_commands(dp, db: Database, notifier: NotificationHandler):
    dp["db"] = db
    dp["notifier"] = notifier
    dp.include_router(router)

@router.message(CommandStart())
async def cmd_start(message: types.Message, **kwargs):
    dp = kwargs["dp"]
    await dp["notifier"].send_welcome(message.from_user.id, message.from_user.username)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("📚 <b>Help</b>\n\n/subscribe &lt;pair&gt; &lt;condition&gt;\nExamples:\n• <code>/subscribe XLA/USDT +5%</code>\n• <code>/subscribe XLA/USDT price=0.15</code>\n• <code>/subscribe XLA/USDT volume+50%</code>\n\n/list\n/unsubscribe &lt;ID&gt;\n/toggle &lt;ID&gt;\n/price &lt;pair&gt;\n/status &lt;pair&gt;", parse_mode="HTML")

@router.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message, **kwargs):
    dp = kwargs["dp"]
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ Format: <code>/subscribe XLA/USDT +5%</code>", parse_mode="HTML")
        return
    symbol = args[1].strip().upper()
    condition_raw = args[2].strip().lower()
    parsed = _parse_condition(condition_raw)
    if not parsed:
        await message.answer("❌ Invalid condition. Supported: +5%, -3%, price=0.15, volume+50%", parse_mode="HTML")
        return
    cond_type, cond_value, direction = parsed
    sub = Subscription(user_id=message.from_user.id, username=message.from_user.username, symbol=symbol, condition_type=cond_type, condition_value=cond_value, direction=direction)
    if await dp["db"].add_subscription(sub):
        await dp["notifier"].send_confirmation(message.from_user.id, sub, "created")
    else:
        await message.answer("❌ Failed to save subscription.")

@router.message(Command("list"))
async def cmd_list(message: types.Message, **kwargs):
    dp = kwargs["dp"]
    await dp["notifier"].send_list(message.from_user.id, await dp["db"].get_user_subscriptions(message.from_user.id))

@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: types.Message, **kwargs):
    dp = kwargs["dp"]
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Usage: <code>/unsubscribe 123</code>", parse_mode="HTML")
        return
    sub_id = int(args[1])
    user_subs = await dp["db"].get_user_subscriptions(message.from_user.id)
    if not any(s.id == sub_id for s in user_subs):
        await message.answer("❌ Subscription not found.")
        return
    if await dp["db"].toggle_subscription(sub_id, False):
        await dp["notifier"].send_confirmation(message.from_user.id, Subscription(id=sub_id, is_active=False), "deleted")

@router.message(Command("toggle"))
async def cmd_toggle(message: types.Message, **kwargs):
    dp = kwargs["dp"]
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Usage: <code>/toggle 123</code>", parse_mode="HTML")
        return
    sub_id = int(args[1])
    user_subs = await dp["db"].get_user_subscriptions(message.from_user.id)
    target = next((s for s in user_subs if s.id == sub_id), None)
    if not target:
        await message.answer("❌ Subscription not found.")
        return
    new_state = not target.is_active
    if await dp["db"].toggle_subscription(sub_id, new_state):
        await dp["notifier"].send_confirmation(message.from_user.id, target, "enabled" if new_state else "disabled")

@router.message(Command("price"))
async def cmd_price(message: types.Message, **kwargs):
    from monitoring import NonKYCClient
    from config import Config
    symbol = message.text.split()[1].strip().upper() if len(message.text.split()) > 1 else Config.DEFAULT_SYMBOL
    await message.answer(f"🔍 Fetching {symbol}...")
    client = NonKYCClient(Config.NONKYC_API_BASE_URL, Config.NONKYC_API_TIMEOUT)
    ticker = client.get_ticker(symbol)
    if ticker:
        last = float(ticker.get("last", ticker.get("price", 0)))
        bid = float(ticker.get("bid", 0))
        ask = float(ticker.get("ask", 0))
        change = float(ticker.get("change_24h", 0))
        volume = float(ticker.get("volume", ticker.get("volume_24h", 0)))
        spread = ((ask - bid) / ((bid + ask) / 2)) * 100 if bid and ask else 0
        emoji = "📈" if change >= 0 else "📉"
        text = (
            f"💰 <b>{symbol.replace('_', '/')}</b>\n"
            f"💵 Last: <code>${last:.6f}</code>\n"
            f"🔹 Bid: <code>${bid:.6f}</code> | 🔸 Ask: <code>${ask:.6f}</code>\n"
            f"↔️ Spread: <b>{spread:.3f}%</b>\n"
            f"{emoji} 24h: <b>{change:+.2f}%</b>\n"
            f"📦 Volume: <code>{volume:,.0f}</code>"
        )
        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(f"❌ Failed to fetch data for {symbol}")

@router.message(Command("status"))
async def cmd_status(message: types.Message, **kwargs):
    from monitoring import NonKYCClient
    from config import Config
    symbol = message.text.split()[1].strip().upper() if len(message.text.split()) > 1 else Config.DEFAULT_SYMBOL
    await message.answer(f"🔍 Checking {symbol} status...")
    client = NonKYCClient(Config.NONKYC_API_BASE_URL, Config.NONKYC_API_TIMEOUT)
    ticker = client.get_ticker(symbol)
    ob = client.get_orderbook(symbol, limit=5)
    if ticker:
        last = float(ticker.get("last", ticker.get("price", 0)))
        change = float(ticker.get("change_24h", 0))
        volume = float(ticker.get("volume", ticker.get("volume_24h", 0)))
        lines = [f"📊 <b>{symbol.replace('_', '/')}</b>", f"💰 Price: <code>${last:.6f}</code>", f"{'📈' if change >= 0 else '📉'} 24h: <b>{change:+.2f}%</b>", f"📦 Volume: <code>{volume:,.0f}</code>", "", "📚 Top OrderBook:"]
        if ob:
            for i, (bid, ask) in enumerate(zip(ob.get("bids", [])[:3], ob.get("asks", [])[:3]), 1):
                lines.append(f"{i}. 🔹 ${float(bid[0]):.6f} | 🔸 ${float(ask[0]):.6f}")
        else:
            lines.append("  (unavailable)")
        lines.append(f"\n<small>Updated: {ticker.get('timestamp', 'now')}</small>")
        await message.answer("\n".join(lines), parse_mode="HTML")
    else:
        await message.answer(f"❌ Failed to fetch status for {symbol}")

def _parse_condition(condition: str):
    condition = condition.strip().lower()
    pct_match = re.match(r'^([+-])?(\d+\.?\d*)\s*%?$', condition)
    if pct_match:
        sign = pct_match.group(1) or "+"
        return ConditionType.PRICE_CHANGE_PERCENT, float(pct_match.group(2)), "up" if sign == "+" else "down"
    price_match = re.match(r'^(price\s*=\s*)?(\d+\.?\d*)$', condition)
    if price_match:
        return ConditionType.PRICE_LEVEL_REACHED, float(price_match.group(2)), None
    vol_match = re.match(r'^(volume|vol)\s*([+-])?(\d+\.?\d*)\s*%?$', condition)
    if vol_match:
        sign = vol_match.group(2) or "+"
        return ConditionType.VOLUME_SPIKE, float(vol_match.group(3)), "up" if sign == "+" else "down"
    depth_match = re.match(r'^(depth|orderbook)\s*[>=]?\s*(\d+\.?\d*)$', condition)
    if depth_match:
        return ConditionType.ORDERBOOK_DEPTH, float(depth_match.group(2)), None
    return None
