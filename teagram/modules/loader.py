import logging

import os
import re
import sys
import time


import atexit
import requests

from telethon import types
from telethon.tl.custom import Message
from .. import loader, utils

VALID_URL = r"[-[\]_.~:/?#@!$&'()*+,;%<=>a-zA-Z0-9]+"
VALID_PIP_PACKAGES = re.compile(
    r"^\s*# required:(?: ?)((?:{url} )*(?:{url}))\s*$".format(url=VALID_URL),
    re.MULTILINE,
)

GIT_REGEX = re.compile(
    r"^https?://github\.com((?:/[a-z0-9-]+){2})(?:/tree/([a-z0-9-]+)((?:/[a-z0-9-]+)*))?/?$",
    flags=re.IGNORECASE,
)

async def get_git_raw_link(repo_url: str):
    """Получить raw ссылку на репозиторий"""
    match = GIT_REGEX.search(repo_url)
    if not match:
        return False

    repo_path = match.group(1)
    branch = match.group(2)
    path = match.group(3)

    r = await utils.run_sync(requests.get, f"https://api.github.com/repos{repo_path}")
    if r.status_code != 200:
        return False

    branch = branch or r.json()["default_branch"]

    return f"https://raw.githubusercontent.com{repo_path}/{branch}{path or ''}/"

@loader.module(name="Loader", author='teagram')
class LoaderMod(loader.Module):
    """Загрузчик модулей"""

    async def dlrepo_cmd(self, message: types.Message, args: str):
        """Установить репозиторий с модулями. Использование: dlrepo <ссылка на репозиторий или reset>"""
        if not args:
            return await utils.answer(
                message, "❌ Нет аргументов")

        if args == "reset":
            self.db.set(
                "teagram.loader", "repo",
                "https://github.com/itzlayz/teagram-modules "
            )
            return await utils.answer(
                message, "✅ Ссылка на репозиторий была сброшена")

        if not await get_git_raw_link(args):
            return await utils.answer(
                message, "❌ Ссылка указана неверно")

        self.db.set("teagram.loader", "repo", args)
        return await utils.answer(
            message, "✅ Ссылка на репозиторий установлена")

    async def dlmod_cmd(self, message: types.Message, args: str):
        """Загрузить модуль по ссылке. Использование: dlmod <ссылка или all или ничего>"""
        modules_repo = self.db.get(
            "teagram.loader", "repo",
            "https://github.com/itzlayz/teagram-modules"
        )
        api_result = await get_git_raw_link(modules_repo)
        if not api_result:
            return await utils.answer(
                message, "<b>❌ Неверная ссылка на репозиторий.</b>\n"
                        "<b>Поменяй её с помощью команды: dlrepo <ссылка на репозиторий или reset></b>"
            )

        raw_link = api_result
        modules = await utils.run_sync(requests.get, raw_link + "all.txt")
        if modules.status_code != 200:
            return await utils.answer(
                message, (
                    f"<b>❌ В <a href=\"{modules_repo}\">репозитории</a> не найден файл all.txt</b>\n"
                )
            )

        modules = modules.text.splitlines()

        if not args:
            text = (
                f"<b>📥 Список доступных модулей с <a href=\"{modules_repo}\">репозитория</a>:</b>\n\n"
                + "<code>all</code> - загрузит все модули\n"
                + "\n".join(
                    map("<code>{}</code>".format, modules))
            )
            return await utils.answer(
                message, text)

        error_text = None
        module_name = None
        count = 0

        if args == "all":
            for module in modules:
                module = raw_link + module + ".py"
                try:
                    r = await utils.run_sync(requests.get, module)
                    if r.status_code != 200:
                        raise requests.exceptions.RequestException
                except requests.exceptions.RequestException:
                    continue

                if not (module_name := await self.manager.load_module(r.text, r.url)):
                    continue

                self.db.set("teagram.loader", "modules",
                            list(set(self.db.get("teagram.loader", "modules", []) + [module])))
                count += 1
        else:
            if args in modules:
                args = raw_link + args + ".py"

            try:
                r = await utils.run_sync(requests.get, args)
                if r.status_code != 200:
                    raise requests.exceptions.ConnectionError

                module_name = await self.manager.load_module(r.text, r.url)
                if module_name is True:
                    error_text = "✅ Зависимости установлены. Требуется перезагрузка"

                if not module_name:
                    error_text = "❌ Не удалось загрузить модуль. Подробности смотри в логах"
            except requests.exceptions.MissingSchema:
                error_text = "❌ Ссылка указана неверно"
            except requests.exceptions.ConnectionError:
                error_text = "❌ Модуль недоступен по ссылке"
            except requests.exceptions.RequestException:
                error_text = "❌ Произошла непредвиденная ошибка. Подробности смотри в логах"

            if error_text:
                return await utils.answer(message, error_text)

            self.db.set("teagram.loader", "modules",
                        list(set(self.db.get("teagram.loader", "modules", []) + [args])))

        return await utils.answer(
            message, (
                f"✅ Модуль \"<code>{module_name}</code>\" загружен"
                if args != "all"
                else f"✅ Загружено <b>{count}</b> из <b>{len(modules)}</b> модулей"
            )
        )

    async def loadraw_cmd(self, message: Message, args: str):
        if not args:
            return await utils.answer(
                message,
                '❌ Вы не указали ссылку'
            )
        
        try:
            response = await utils.run_sync(requests.get, args)
            
            module = await self.manager.load_module(response.text, response.url)

            if module is True:
                return await utils.answer(
                    message, "✅ Зависимости установлены. Требуется перезагрузка")

            if not module:
                return await utils.answer(
                    message, "❌ Не удалось загрузить модуль. Подробности смотри в логах")

            with open(f'teagram/modules/{module}.py', 'w', encoding="utf-8") as file:
                file.write(response.text)
            
            await utils.answer(
                message, 
                f"✅ Модуль \"<code>{module}</code>\" загружен"
            )

        except requests.exceptions.MissingSchema:
            await utils.answer(message, '❌ Вы указали неправильную ссылку')
        except Exception as error:
            await utils.answer(message, f'❌ Ошибка: <code>{error}</code>')

    async def loadmod_cmd(self,  message: Message):
        """Загрузить модуль по файлу. Использование: <реплай на файл>"""
        reply: Message = await message.get_reply_message()
        file = (
            message
            if message.document
            else reply
            if reply and reply.document
            else None
        )

        if not file:
            return await utils.answer(
                message, "❌ Нет реплая на файл")

        _file = await reply.download_media(bytes)

        try:
            _file = _file.decode()
        except UnicodeDecodeError:
            return await utils.answer(
                message, "❌ Неверная кодировка файла")

        modules = [
            '_example'
            'config',
            'eval',
            'help',
            'info',
            'moduleGuard',
            'terminal',
            'tester',
            'updater'
        ]
        
        for mod in modules:
            if _file == mod:
                return await utils.answer(
                    message,
                    "❌ Нельзя загружать встроенные модули"
                )

        module_name = await self.manager.load_module(_file)
        module = '_'.join(module_name.lower().split())

        if module_name is True:
            with open(f'teagram/modules/{module}.py', 'w', encoding="utf-8") as file:
                file.write(_file)

            return await utils.answer(
                message, "✅ <b>Зависимости установлены. Требуется перезагрузка</b>")

        if not module_name:
            return await utils.answer(
                message, "❌ <b>Не удалось загрузить модуль. Подробности смотри в логах</b>")
        
        with open(f'teagram/modules/{module}.py', 'w', encoding="utf-8") as file:
            file.write(_file)
        
        await utils.answer(
            message, f"✅ Модуль \"<code>{module_name}</code>\" загружен")

    async def unloadmod_cmd(self,  message: types.Message, args: str):
        """Выгрузить модуль. Использование: unloadmod <название модуля>"""
        if not (module_name := self.manager.unload_module(args)):
            return await utils.answer(
                message, "❌ Неверное название модуля")
        
        modules = [
            'config',
            'eval',
            'help',
            'info',
            'moduleGuard',
            'terminal',
            'tester',
            'updater',
            'loader'
        ]
        
        if module_name in modules:
            return await utils.answer(
                message,
                "❌ Выгружать встроенные модули нельзя"
            )

        return await utils.answer(
            message, f"✅ Модуль \"<code>{module_name}</code>\" выгружен")
    
    async def reloadmod_cmd(self,  message: types.Message, args: str):
        if not args:
            return await utils.answer(
                message, "❌ Вы не указали модуль")
        
        try:
            module = args.split(maxsplit=1)[0].replace('.py', '')

            modules = [
                'config',
                'eval',
                'help',
                'info',
                'moduleGuard',
                'terminal',
                'tester',
                'updater',
                'loader'
            ]
            
            # for mod in modules:
            #     if module == mod:
            #         return await utils.answer(
            #             message,
            #             "❌ Нельзя перезагружать встроенные модули"
            #         )

            if module + '.py' not in os.listdir('teagram/modules'):
                return await utils.answer(
                    message,
                    f'❌ Модуль {module} не найден'
                )
            
            unload = self.manager.unload_module(module)
            with open(f'teagram/modules/{module}.py', encoding='utf-8') as file:
                module_source = file.read()

            load = await self.manager.load_module(module_source)

            if not load and not unload:
                return await utils.answer(
                    message,
                    '❌ Произошла ошибка, пожалуйста проверьте логи'
                )
        except Exception as error:
            logging.error(error)
            return await utils.answer(
                message,
                '❌ Произошла ошибка, пожалуйста проверьте логи'
            )


        return await utils.answer(
            message, f"✅ Модуль \"<code>{module}</code>\" перезагружен")

    async def restart_cmd(self, message: types.Message):
        """Перезагрузка юзербота"""
        def restart() -> None:
            """Запускает загрузку юзербота"""
            os.execl(sys.executable, sys.executable, "-m", "teagram")

        atexit.register(restart)
        self.db.set(
            "teagram.loader", "restart", {
                "msg": f"{((message.chat.id) if message.chat else 0 or message._chat_peer)}:{message.id}",
                "start": time.time(),
                "type": "restart"
            }
        )

        await utils.answer(message, "<b><emoji id=5328274090262275771>🛠</emoji> Перезагрузка...</b>")

        logging.info("Перезагрузка...")
        return sys.exit(0)
    