#                            ██╗████████╗███████╗██╗░░░░░░█████╗░██╗░░░██╗███████╗
#                            ██║╚══██╔══╝╚════██║██║░░░░░██╔══██╗╚██╗░██╔╝╚════██║
#                            ██║░░░██║░░░░░███╔═╝██║░░░░░███████║░╚████╔╝░░░███╔═╝
#                            ██║░░░██║░░░██╔══╝░░██║░░░░░██╔══██║░░╚██╔╝░░██╔══╝░░
#                            ██║░░░██║░░░███████╗███████╗██║░░██║░░░██║░░░███████╗
#                            ╚═╝░░░╚═╝░░░╚══════╝╚══════╝╚═╝░░╚═╝░░░╚═╝░░░╚══════╝
#                                            https://t.me/itzlayz
#                           
#                                    🔒 Licensed under the GNU AGPLv3
#                                 https://www.gnu.org/licenses/agpl-3.0.html

import requests
from .. import loader, utils

@loader.module("Lumix", "itzlayz", 1.0)
class LumixMod(loader.Module):
    strings = {
        "name": "Lumix",
        "searching": "🔎 <b>Searching module...</b>",
        "searching_git": "🔎 <b>Searching module in Github...</b>",
        "installed": "✅ <b>Module successfully loaded</b>\n",
        "not_found": "❌ <b>Module not found</b>",
        "installing": "📥 <b>Installing module...</b>"
    }
    strings_ru = {
        "name": "Lumix",
        "searching": "🔎 <b>Поиск модуля...</b>",
        "searching_git": "🔎 <b>Поиск модуля в Github...</b>",
        "installed": "✅ <b>Модуль успешно установлен</b>\n",
        "not_found": "❌ <b>Модуль не найден</b>",
        "installing": "📥 <b>Устанавливаем модуль...</b>"
    }
    def __init__(self):
        self.api = "http://lumix.myddns.me:62671"

    def prep_docs(self, module: str) -> str:
        module = self.lookup(module)
        prefix = self.get_prefix()[0]
        return "\n".join(
            f"""👉 <code>{prefix + command}</code> {f"<b>{module.command_handlers[command].__doc__}</b>" or ''}"""
            for command in module.command_handlers
        )

    @loader.command()
    async def lumix(self, message, args: str):
        if not args:
            return await utils.answer(
                message,
                self.strings("not_found")
            )

        await utils.answer(
            message,
            self.strings("searching")
        )
        
        module = args.split()[0]
        text = (
            await utils.run_sync(
                requests.get, 
                f"{self.api}/view/{module}",
            )
        ).text
        
        if text == "Not found":
            await utils.answer(
                message,
                self.strings("searching_git")
            )

            headers = {
                'User-Agent': "Teagram-TL-Lumix",
                'X-Lumix': "Lumix",
                "X-Teagram-SHA": utils.git_hash()
            }
            matches = (
                await utils.run_sync(
                    requests.get, 
                    f"{self.api}/find_git_matches/{module}",
                    headers=headers
                )
            )
            if matches.text == "Not found":
                return await utils.answer(
                    message,
                    self.strings("not_found")
                )
            
            module = max(matches.json(), key=lambda x: x[-1])
            text = (
                await utils.run_sync(
                    requests.get, 
                    f"{self.api}/view/{module[0]}",
                )
            ).text
            name = await self.manager.load_module(text)
            await utils.answer(
                message,
                self.strings("installed").format(name) + self.prep_docs(name)
            )
        
        await utils.answer(
            message,
            self.strings("installing")
        )
        
        name = await self.manager.load_module(text)
        await utils.answer(
            message,
            self.strings("installed").format(name) + self.prep_docs(name)
        )
