import logging

from googletrans import Translator
from pyrogram import Client, types

from .. import loader, utils

# не трогайте если команды не пофиксили

@loader.module(name="Translator")
class TranslatorMod(loader.Module):
    """Используйте Google переводчик прямо через 🍵teagram!"""

    @loader.on(lambda _, __, message: message.text.startswith('.translate'))
    async def watcher(self, app: Client, message: types.Message):
        await app.send_message(message.from_chat.id, "☕")
        tr = Translator()
        translated = tr.translate(args[0], dest=args[1:])
        await app.send_message(
            message.from_chat.id,
            f"""
🍵 `Teagram | UserBot`
Переведено с **{translated.src}** на **{translated.dest}**
**Перевод:**
`{translated.text}`
**Произношение:**
`{translated.pronunciation}`
            """
        )
