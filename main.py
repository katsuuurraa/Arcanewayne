import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, select
import random

BOT_TOKEN = os.getenv("BOT_TOKEN") or "DEMO_TOKEN"

# --- DB Setup ---
Base = declarative_base()
engine = create_async_engine("sqlite+aiosqlite:///./db.sqlite3")
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True)
    name = Column(String)
    balance = Column(Integer, default=0)
    last_bonus = Column(DateTime, default=datetime.utcnow)
    last_loan = Column(DateTime, default=datetime.utcnow)

class Bank(Base):
    __tablename__ = "bank"
    id = Column(Integer, primary_key=True)
    total = Column(Integer, default=100000)

# --- Bot Setup ---
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)

# --- Utils ---
async def get_or_create_user(tg_id: int, name: str):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            return user, session
        user = User(tg_id=tg_id, name=name, balance=500)
        session.add(user)
        bank = await session.get(Bank, 1)
        if not bank:
            session.add(Bank(id=1, total=100000))
        await session.commit()
        return user, session

# --- Handlers ---

@dp.message(F.text.lower() == "старт")
async def cmd_start(message: Message):
    user, _ = await get_or_create_user(message.from_user.id, message.from_user.first_name)
    await message.answer("🎉 Ты зарегистрирован!" if user.balance == 500 else "✅ Уже зарегистрирован.")

@dp.message(F.text.lower() == "профиль")
async def profile(message: Message):
    user, _ = await get_or_create_user(message.from_user.id, message.from_user.first_name)
    await message.answer(f"👤 <b>{user.name}</b>
💰 Баланс: {user.balance} монет")

@dp.message(F.text.lower() == "банк")
async def bank_info(message: Message):
    async with async_session() as session:
        bank = await session.get(Bank, 1)
        await message.answer(f"🏦 Банк содержит: {bank.total} монет")

@dp.message(F.text.lower() == "бонус")
async def bonus(message: Message):
    user, session = await get_or_create_user(message.from_user.id, message.from_user.first_name)
    now = datetime.utcnow()
    if now - user.last_bonus >= timedelta(hours=6):
        user.last_bonus = now
        user.balance += 200
        await session.commit()
        await message.answer("🎁 Ты получил бонус 200 монет!")
    else:
        left = timedelta(hours=6) - (now - user.last_bonus)
        await message.answer(f"⌛ Приходи через {int(left.total_seconds()//3600)} ч.")

@dp.message(F.text.lower() == "займ")
async def loan(message: Message):
    user, session = await get_or_create_user(message.from_user.id, message.from_user.first_name)
    bank = await session.get(Bank, 1)
    now = datetime.utcnow()
    if now - user.last_loan >= timedelta(hours=12):
        amount = 300
        if bank.total < amount:
            await message.answer("❌ В банке недостаточно средств.")
            return
        user.last_loan = now
        user.balance += amount
        bank.total -= amount
        await session.commit()
        await message.answer(f"💸 Ты получил займ {amount} монет.")
    else:
        left = timedelta(hours=12) - (now - user.last_loan)
        await message.answer(f"⌛ Займ доступен через {int(left.total_seconds()//3600)} ч.")

@dp.message(F.text.lower() == "монетка")
async def coin(message: Message):
    user, session = await get_or_create_user(message.from_user.id, message.from_user.first_name)
    if user.balance < 100:
        await message.answer("❌ Недостаточно монет (нужно 100).")
        return
    user.balance -= 100
    result = random.choice(["орел", "решка"])
    if result == "орел":
        user.balance += 200
        text = "🎉 Выпал <b>орел</b>! Ты выиграл 200 монет."
    else:
        text = "💤 Выпала <b>решка</b>. Ты проиграл."
    await session.commit()
    await message.answer(text)

@dp.message(F.text.lower() == "слот")
async def slot(message: Message):
    user, session = await get_or_create_user(message.from_user.id, message.from_user.first_name)
    if user.balance < 100:
        await message.answer("❌ Нужно хотя бы 100 монет.")
        return
    user.balance -= 100
    emojis = ["🍒", "🍋", "🍊", "💎", "7️⃣"]
    roll = [random.choice(emojis) for _ in range(3)]
    if len(set(roll)) == 1:
        user.balance += 500
        result = "🎉 Джекпот! +500 монет"
    elif len(set(roll)) == 2:
        user.balance += 200
        result = "✨ Почти! +200 монет"
    else:
        result = "💤 Не повезло."
    await session.commit()
    await message.answer("[" + " ".join(roll) + f"]
{result}")

@dp.message(F.text.lower() == "дайс")
async def dice(message: Message):
    user, session = await get_or_create_user(message.from_user.id, message.from_user.first_name)
    if user.balance < 50:
        await message.answer("❌ Нужно хотя бы 50 монет.")
        return
    user.balance -= 50
    roll = random.randint(1, 6)
    if roll == 6:
        user.balance += 300
        result = "🎲 Выпало 6! Ты выиграл 300 монет."
    else:
        result = f"🎲 Выпало {roll}. Не повезло."
    await session.commit()
    await message.answer(result)

@dp.message(F.text.lower() == "топ")
async def top(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.balance.desc()).limit(10))
        top_users = result.scalars().all()
        text = "🏆 Топ игроков:
"
        for i, user in enumerate(top_users, 1):
            text += f"{i}. {user.name} — {user.balance} монет
"
        await message.answer(text)

# --- Main ---
async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
