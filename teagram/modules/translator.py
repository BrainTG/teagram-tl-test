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
                    self.strings['notext']
                )
        
        if (lang := self.config.get('language')) not in LANGUAGES:
            return await utils.answer(
                message,
                self.strings['wronglang'].format(lang)
            )
        
        translated: Translated = Translator().translate(text, dest=lang)
        
        await utils.answer(
            message,
            f"👅 {self.strings['lang']} <b>{translated.src} -> {lang}</b>\n"
            f"🗣 {self.string['pronun']} <b>{translated.pronunciation}</b>\n"
            f"➡ {self.strings['text']}:\n"
            f"<b>{translated.origin}</b>\n"
            f"➡ {self.strings['trans']}:\n"
            f"<b>{translated.text}</b>"
        )

