import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def test():
    try:
        conn = await asyncpg.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "campus_nav_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            ssl=False,
        )
        result = await conn.fetchval("SELECT COUNT(*) FROM nav.poi")
        print(f"连接成功！nav.poi 记录数：{result}")
        await conn.close()
    except Exception as e:
        print(f"连接失败：{type(e).__name__}: {e}")

asyncio.run(test())
