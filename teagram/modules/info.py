import platform
import socket
from datetime import datetime

import psutil
from pyrogram import Client, types

from .. import __version__, loader, utils


def byter(num: float, suffix: str = "B") -> str:
    for unit in ["B", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0

    return "%.1f%s%s" % (num, "Yi", suffix)

@loader.module(name="UserBot")
class AboutMod(loader.Module):
    """Узнайте что такое юзербот, или информацию о вашем 🍵teagram"""
    
    async def info_cmd(self, app: Client, message: types.Message):
        """информацию о вашем 🍵teagram."""
        await utils.answer(message, "☕")
        me = await app.get_me()
        boot = psutil.boot_time()
        bt = datetime.fromtimestamp(boot)
        await utils.answer(
            message,
            f"""
`🍵 teagram | UserBot`

`💻 UserBot`
**Владелец**: `{me.username}`
**Версия**: `v{__version__}`
`🧠 Процессор`
**Использование**: `{int(psutil.cpu_percent())}%`
**Ядер**: `{psutil.cpu_count()}`
`🗃 ОЗУ`
**Использование**: `{byter(psutil.virtual_memory().used)}`/`{byter(psutil.virtual_memory().total)}`
`💾 ПЗУ`
[/] | **Использование**: ``{byter(psutil.disk_usage("/").used)}`/`{byter(psutil.disk_usage("/").total)}` (`{psutil.disk_usage("/").percent}%`)
`🖥️ хост`
**Система**: `{platform.uname().system}`
**Узел**: `{platform.uname().node}`
**Релиз**: `{platform.uname().release}`
**Версия**: `{platform.uname().version}`
**Архитектура**: `{platform.machine()}`
**Процессор**: `{platform.processor()}`
**Имя хоста**: `{socket.gethostname()}`
**Работает с**: `{bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}`
            """)
        
    async def ubinfo_cmd(self, app: Client, message: types.Message, args: str):
        """информация о UserBot"""
        await utils.answer(message, "☕")
        await utils.answer(message, '''🤔 <b>Что такое юзербот?</b>
        
📚 <b>Юзербот это</b> - <b>Сборник разных програм</b> для взаймодeйствия с Telegarm API
А с помощью взаймодействия с Telegarm API <b>можно написать разныe скрипты</b> для автоматизаций некоторых действий со стороны пользователя такие как: <b>Присоединение к каналам, отправление сообщений, и т.д</b>

🤔 <b>Чем отличается юзербот от обычного бота?</b>

🤭 <b>Юзербот может выполняться на аккаунте обычного пользователя</b>
Например: @pavel_durov А бот может выполняться только на специальных бот аккаунтах например: @examplebot
<b>Юзерботы довольно гибкие</b> в плане настройки, у них больше функций.

🛑 <b>Поддерживаются ли оффициально юзерботы телеграмом?</b>

🚫 <b>Нет.</b> Они оффициально не поддерживаются, но вас не заблокируют за использование юзерботов.
Но <b>могут заблокировать в случае выполнения вредоносного кода или за злоупотребление Telegarm API</b> на вашем аккаунте, так что владельцу юзербота надо тщательно проверять что выполняется на вашем аккаунте.''')
