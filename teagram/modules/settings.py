import time
import io
import os
import logging

from datetime import timedelta
from telethon import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .. import loader, utils, bot

log = logging.getLogger()

class TestException(Exception):
    pass

@loader.module(name="Settings", author="teagram")
class SettingsMod(loader.Module):
    """Настройки юзер бота
       Userbot's settings"""

    strings = {'name': 'settings'}

    async def logs_cmd(self, message: types.Message, args: str):
        """Отправляет логи. Использование: logs <уровень>"""
        if not args:
            args = "40"

        lvl = int(args)

        if not args or lvl < 0 or lvl > 60:
            return await utils.answer(
                message, self.strings['no_logs'])

        if not getattr(self, '_logger', ''):
            self._logger = log.handlers[0]

        logs = '\n'.join(str(error) for error in self._logger.logs).encode('utf-8')
        
        if not logs:
            return await utils.answer(
                message, self.strings['no_lvl'].format(lvl=lvl,
                                                 name=logging.getLevelName(lvl)))

        logs = io.BytesIO(logs)
        logs.name = "teagram.log"

        return await utils.answer(
            message,
            logs,
            document=True,
            caption=self.strings['logs'].format(
                lvl=lvl, 
                name=logging.getLevelName(lvl))
            )

    @loader.command()
    async def clearlogs(self, message: types.Message):
        if not getattr(self, '_logger', ''):
            self._logger = log.handlers[0]

        self._logger.flush()
        self._logger.logs = []

        await utils.answer(message, self.strings['flushed'])

    @loader.command()
    async def error(self, message):
        raise TestException("Test exception")

    async def setprefix_cmd(self, message: types.Message, args: str):
        """Изменить префикс, можно несколько штук разделённые пробелом. Использование: setprefix <префикс> [префикс, ...]"""
        if not (args := args.split()):
            return await utils.answer(
                message, self.strings['wprefix'])

        self.db.set("teagram.loader", "prefixes", list(set(args)))
        prefixes = ", ".join(f"<code>{prefix}</code>" for prefix in args)
        await utils.answer(
            message, self.strings['prefix'].format(prefixes=prefixes))

    async def setlang_cmd(self, message: types.Message, args: str):
        """Изменить язык. Использование: setlang <язык>"""
        args = args.split()
        
        language = args[0]
        languages = list(map(lambda x: x.replace('.yml', ''), os.listdir('teagram/langpacks')))
        
        if not args:
            return await utils.answer(
                message, self.strings['wlang'])
        
        if language not in languages:
            langs = ' '.join(languages)
            return await utils.answer(
                message, self.strings['elang'].format(langs=langs))

        self.db.set("teagram.loader", "lang", language)
        
        pack = utils.get_langpack()
        setattr(self.manager, 'strings', pack.get('manager'))

        for instance in self.manager.modules:
            name = getattr(instance, 'strings', None)
            if name:
                stringsname = name.get('name', '').lower()
                if stringsname in [
                    'backup',
                    'config',
                    'eval',
                    'help',
                    'info',
                    'loader',
                    'moduleguard',
                    'settings',
                    'terminal',
                    'translator',
                    'updater'
                ]:
                    _pack = pack.get(stringsname, None)

                    if _pack:
                        _pack['name'] = stringsname
                        setattr(instance, 'strings', pack.get(stringsname))

        return await utils.answer(
            message, self.strings['lang'].format(language=language))

    async def addalias_cmd(self, message: types.Message, args: str):
        """Добавить алиас. Использование: addalias <новый алиас> <команда>"""
        if not (args := args.lower().split(maxsplit=1)):
            return await utils.answer(
                message, self.strings['walias'])

        if len(args) != 2:
            return await utils.answer(
                message, self.strings['ealias']
            )

        aliases = self.manager.aliases
        if args[0] in aliases:
            return await utils.answer(
                message, self.strings['nalias'])

        if not self.manager.command_handlers.get(args[1]):
            return await utils.answer(
                message, self.strings['calias'])

        aliases[args[0]] = args[1]
        self.db.set("teagram.loader", "aliases", aliases)

        return await utils.answer(
            message, self.strings['alias'].format(alias=args[0], cmd=args[1]))

    async def delalias_cmd(self, message: types.Message, args: str):
        """Удалить алиас. Использование: delalias <алиас>"""
        if not (args := args.lower()):
            return await utils.answer(
                message, self.strings['dwalias'])

        aliases = self.manager.aliases
        if args not in aliases:
            return await utils.answer(
                message, self.strings['dealias'])

        del aliases[args]
        self.db.set("teagram.loader", "aliases", aliases)

        return await utils.answer(
            message, self.strings['dalias'].format(args))

    async def aliases_cmd(self, message: types.Message):
        """Показать все алиасы"""
        aliases = self.manager.aliases
        if not aliases:
            return await utils.answer(
                message, self.strings['noalias'])

        return await utils.answer(
            message, self.strings['allalias'] + "\n".join(
                f"• <code>{alias}</code> ➜ {command}"
                for alias, command in aliases.items()
            )
        )

    async def ping_cmd(self, message: types.Message):
        """🍵 команда для просмотра пинга."""
        start = time.perf_counter_ns()
        
        msg = await message._client.send_message(utils.get_chat(message), "☕")
        
        ping = round((time.perf_counter_ns() - start) / 10**6, 3)
        uptime = timedelta(seconds=round(time.time() - utils._init_time))

        await utils.answer(
            message,
            f"🕒 {self.strings['ping']}: <code>{ping}ms</code>"
            f"❔ {self.strings['uptime']}: {uptime}"
        )

        await msg.delete()

    @loader.command()
    async def adduser(self, message: types.Message):
        if not (reply := await message.message.get_reply_message()):
            return await utils.answer(
                message,
                self.strings['noreply']
            )

        if reply.sender_id == (_id := (await self.client.get_me()).id):
            return await utils.answer(
                message,
                self.strings['yourself']
            )

        if message.message.sender_id != _id:
            return await utils.answer(
                message,
                self.strings['owner']
            )
        
        user = reply.sender_id
        users = self.db.get('teagram.loader', 'users', [])
        self.db.set('teagram.loader', 'users', users + [user])

        await utils.answer(message, self.strings['adduser'])

    @loader.command()
    async def rmuser(self, message: types.Message):
        if not (reply := await message.message.get_reply_message()):
            return await utils.answer(
                message,
                self.strings['noreply']
            )

        if reply.sender_id == (_id := (await self.client.get_me()).id):
            return await utils.answer(
                message,
                self.strings['yourself']
            )

        if message.message.sender_id != _id:
            return await utils.answer(
                message,
                self.strings['owner']
            )
        
        user = reply.sender_id
        users = self.db.get('teagram.loader', 'users', [])
        self.db.set('teagram.loader', 'users', list(filter(lambda x: x != user, users)))

        await utils.answer(message, self.strings['deluser'])

    @loader.command()
    async def users(self, message: types.Message):
        _users = self.db.get('teagram.loader', 'users', [])
        await utils.answer(
            message,
            (f'➡ {self.strings["user"]} <code>' + ', '.join(str(user) for user in _users) + '</code>')
              if _users else self.strings['nouser']
        )

    @loader.command('Deleting teagram')
    async def uninstall_teagram(self, message: types.Message):
        manager: bot.BotManager = self.bot

        # TODO:
        # translation
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                '⚠ Подтвердить',
                callback_data='teagram_perm_delete'
            ),
            InlineKeyboardButton(
                '❌ Отменить',
                callback_data='no_perm_delete'
            )
        )

        await manager.form(
            title='Delete teagram',
            description='Delete teagram permanently',
            text='⚠ <b>Вы уверены что хотите удалить teagram?</b>\n',
            message=message,
            reply_markup=keyboard,
            callback='_loader_permdel'
        )