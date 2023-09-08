from .. import loader, utils, validators
from ..types import Config, ConfigValue

from telethon import types
from googletrans import Translator, LANGUAGES
from googletrans.models import Translated

@loader.module('Translator', 'teagram')
class TranslatorMod(loader.Module):
    """Переводчик"""
    
    def __init__(self):
        self.config = Config(
            ConfigValue(
                option='language',
                docstring='Язык',
                default='en',
                value=self.db.get('Translator', 'language', 'en'),
                validator=validators.String()
            )
        )

    @loader.command()
    async def translate(self, message: types.Message, args):
        """Перевод"""
        if not (text := args):
            if not (text := (await message.get_reply_message()).raw_text):
                return await utils.answer(
                    message,
                    '❌ Текст не найден'
                )
        
        if (lang := self.config.get('language')) not in LANGUAGES:
            return await utils.answer(
                message,
                f'❌ Неправильный язык (`{lang}`)'
            )
        
        translated: Translated = Translator().translate(text, dest=lang)
        
        await utils.answer(
            message,
            f"""
👅 Язык <b>{translated.src} -> {lang}</b>
🗣 Произношение <b>{translated.pronunciation}</b>

➡ Текст:
<b>{translated.origin}</b>

➡ Перевод:
<b>{translated.text}</b>
"""
        )

