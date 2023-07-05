import time
from pyrogram import Client, types
from .. import loader, utils


@loader.module(name="ping")
class PingModule(loader.Module):
    """🍵 Команда пинг"""

    async def pingcmd(self, app: Client, message: types.Message, args: str):
        """🍵 команда для просмотра пинга."""
        start = time.perf_counter_ns()
        await utils.answer(message, "☕")
        ping = round((time.perf_counter_ns() - start) / 10**6, 3)
        await utils.answer(
            message,
            f"""
🍵 `Teagram | UserBot`
🏓 **Понг!**: `{ping}ms`
            """
        )
