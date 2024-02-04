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

import asyncio
import os
import sys

import re
import subprocess

import logging
import traceback

import requests
import inspect

from importlib.abc import SourceLoader
from importlib.machinery import ModuleSpec
from importlib.util import spec_from_file_location, module_from_spec

from typing import Union, List, Dict, Any, Callable
from types import FunctionType, LambdaType

from telethon import TelegramClient, types
from . import dispatcher, utils, database, bot, translation
from . import validators as _validators
from . import types as ttypes

VALID_URL = r"[-[\]_.~:/?#@!$&'()*+,;%<=>a-zA-Z0-9]+"
VALID_PIP_PACKAGES = re.compile(
    r"^\s*# required:(?: ?)((?:{url} )*(?:{url}))\s*$".format(url=VALID_URL),
    re.MULTILINE,
)

logger = logging.getLogger()

class Loop:
    def __init__(
        self,
        func: FunctionType,
        interval: Union[int, float],
        autostart: bool,
        *args,
        **kwargs
    ):
        """Args, kwargs using in start"""
        
        self.func = func
        self.interval = interval
        self.autostart = autostart
        self.status = False
        self.task = None
        self.method = None

        if self.autostart:
            self.start(*args, **kwargs)
            self.status = True

    def start(self, interval: int = None, *args, **kwargs):
        """Args, kwargs using in start"""

        if self.task:
            return False
        if interval:
            self.interval = interval

        self.task = asyncio.ensure_future(self.loop(*args, **kwargs))

    def stop(self):
        if self.task:
            logger.info(f"{self.func.__name__} loop have stopped")
            self.task.cancel()

            return True

        return False

    async def loop(self, *args, **kwargs):
        while self.status:
            if self.interval <= 0:
                logger.exception('Interval must be higher than zero')
                break

            if not getattr(self, 'method', ''):
                break

            try:
                await self.func(self.method, *args, **kwargs)
            except Exception:
                logger.error(traceback.format_exc())

            await asyncio.sleep(self.interval)

        self.status = False


def module(
    name: str,
    author: Union[str, None] = None,
    version: Union[int, float, None] = None,
    warning: Union[str, None] = None
) -> FunctionType:
    def decorator(instance: "Module"):
        instance.name = name
        instance.author = author
        instance.version = version
        instance.warning = warning

        return instance

    return decorator


@module(name="Unknown")
class Module:
    name: str
    author: str
    version: Union[int, float]
    warning: str

    async def on_load(self) -> Any:
        ...
    
    async def on_unload(self) -> Any:
        ...

    # same as on_load but with some args
    async def client_ready(self, client, db):
        ...

    def get(self, key: str, _: Any = None) -> Any:
        db = getattr(self, 'db', {}) # we can't get db now
        
        return db.get(
            self.__class__.__name__,
            key, _
        )

    def set(self, key: str, value: Any) -> None:
        db = getattr(self, 'db', {})
        
        db.set(
            self.__class__.__name__,
            key, value
        )


class StringLoader(SourceLoader):
    def __init__(self, data: str, origin: str) -> None:
        self.data = data.encode("utf-8")
        self.origin = origin

    def get_code(self, full_name: str) -> Union[Any, None]:
        if source := self.get_source(full_name):
            return compile(source, self.origin, "exec", dont_inherit=True)
        else:
            return None

    def get_filename(self, _: str) -> str:
        return self.origin

    def get_data(self, _: str) -> str:
        return self.data

def get_command_handlers(instance: Module) -> Dict[str, FunctionType]:
    command_handlers = {}
    for method_name in dir(instance):
        iscmd = hasattr(getattr(instance, method_name), "is_command")
        if callable(getattr(instance, method_name)) and (len(method_name) > 4 if not iscmd else True):
            if method_name.endswith("_cmd"):
                command_handlers[method_name[:-4].lower()] = getattr(instance, method_name)
            elif method_name.endswith("cmd"):
                command_handlers[method_name[:-3].lower()] = getattr(instance, method_name)
            elif iscmd:
                method_name = method_name.replace('_cmd', '').replace('cmd', '')
                command_handlers[method_name] = getattr(instance, method_name)
                
    return command_handlers


def get_watcher_handlers(instance: 'Module') -> List[FunctionType]:
    return [
        method for method in dir(instance)
        if callable(getattr(instance, method)) and(
            method.startswith("watcher")
            or hasattr(method, 'watcher')
        )
    ]


def get_message_handlers(instance: Module) -> Dict[str, FunctionType]:
    return {
        method_name[:-16].lower(): getattr(
            instance, method_name
        ) for method_name in dir(instance)
        if (
            callable(getattr(instance, method_name))
            and len(method_name) > 16
            and method_name.endswith("_message_handler")
        )
    }


def get_callback_handlers(instance: Module) -> Dict[str, FunctionType]:
    return {
        method_name[:-17].lower(): getattr(
            instance, method_name
        ) for method_name in dir(instance)
        if (
            callable(getattr(instance, method_name))
            and len(method_name) > 17
            and method_name.endswith("_callback_handler")
        )
    }

def get_inline_handlers(instance: Module) -> Dict[str, Callable]:
    inline_handlers = {}

    for method_name in dir(instance):
        if (
            callable(getattr(instance, method_name))
            and (
                (len(method_name) > 15 and method_name.endswith("_inline_handler"))
                or hasattr(getattr(instance, method_name), "is_inline_handler")
            )
        ):
            key = method_name[:-15].lower() if len(method_name) > 15 else method_name.lower()
            value = getattr(instance, method_name.lower())
            inline_handlers[key] = value

    return inline_handlers

def get_loops(instance: Module):
    loops = []

    for method in dir(instance):
        func = getattr(instance, method)
        if (
            callable(getattr(instance, method)) and
            hasattr(func, 'loop') and
            method.startswith('loop') or
            method.endswith('loop')
        ):
            loops.append(func)

    return loops

def tag(*args, **kwargs) -> FunctionType:
    def decorator(func: FunctionType):
        for arg in args:
            setattr(func, arg, True)

        for kwarg, value in kwargs.items():
            setattr(func, kwarg, value)

        return func

    return decorator

def loop(interval: Union[int, float], autostart: bool = True):
    def decorator(func: FunctionType):
        _loop = Loop(func, interval, autostart)
        setattr(func, "loop", True)
        tag(
            _loop=_loop,
            interval=interval,
            autostart=autostart
        )

        return _loop

    return decorator

def command(docs: str = None, alias: str = None, *args, **kwargs) -> FunctionType:
    def decorator(func: FunctionType):
        if docs:
            func.__doc__ = docs

        if alias:
            setattr(func, "alias", alias)
        
        setattr(func, "is_command", True)
        tag(*args, **kwargs)
        return func

    return decorator

def inline_handler(docs: str = None, *args, **kwargs) -> FunctionType:
    def decorator(func: FunctionType):
        if docs:
            func.__doc__ = docs
        
        setattr(func, "is_inline_handler", True)
        tag(*args, **kwargs)
        return func

    return decorator

def watcher(*args, **kwargs) -> FunctionType:
    def decorator(func: FunctionType):
        setattr(func, "watcher", True)
        tag(*args, **kwargs)
        return func

    return decorator

def inline_everyone(func: Callable) -> FunctionType:
    return setattr(func, 'inline_everyone', True)

def on_bot(custom_filters: LambdaType) -> FunctionType:
    """
    Makes custom filter for bot
    :param custom_filters: Lambda filter
    :returns: 
    """

    def decorator(func: FunctionType):
        func._filters = custom_filters
        return func

    return decorator

# non functional, for hikka
def tds(cls):
    return cls


# hikka support
ModuleConfig = ttypes.Config
ConfigValue = ttypes.HikkaValue
validators = _validators

class ModulesManager:
    """Manager of modules"""

    def __init__(
        self,
        client: TelegramClient,
        db: database.Database,
        me: types.User
    ) -> None:
        self.modules: List[Module] = []
        self.watcher_handlers: List[FunctionType] = []

        self.command_handlers: Dict[str, FunctionType] = {}
        self.message_handlers: Dict[str, FunctionType] = {}
        self.inline_handlers: Dict[str, FunctionType] = {}
        self.callback_handlers: Dict[str, FunctionType] = {}
        self.loops: List[FunctionType] = []

        self._local_modules_path: str = "./teagram/modules"

        self._client: TelegramClient = client
        self._db: database.Database = db
        self.me: types.User = me
        self.warnings: List[str] = []

        langpack = utils.get_langpack()
        while not langpack: # idk why, but sometimes it returns None
            langpack = utils.get_langpack()

        self.aliases: dict = self._db.get(__name__, "aliases", {})
        self.strings: dict = langpack.get('manager')
        self.translator = translation.Translator(self._db)
        self.core_modules = [
            'backuper',
            'teaconfig',
            'dump',
            'eval',
            'help',
            'info',
            'loader',
            'settings',
            'terminal',
            'updater'
        ]

        self.dp: dispatcher.DispatcherManager = None
        self.bot_manager: bot.BotManager = None
        self.inline: bot.BotManager = None # same as bot_manager

    async def load(self, app: TelegramClient) -> bool:
        setattr(app, 'loader', self)

        self.dp = dispatcher.DispatcherManager(app, self)
        await self.dp.load()

        self.bot_manager = bot.BotManager(app, self._db, self)
        await self.bot_manager.load()

        self.inline = self.bot_manager
        self.me.phone = "sup"
        
        setattr(app, 'inline_bot', self.inline.bot)
        for local_module in filter(
            lambda file_name: file_name.endswith(".py")
            and not file_name.startswith("_"), os.listdir(self._local_modules_path)
        ):
            module_name = f"teagram.modules.{local_module[:-3]}"
            file_path = os.path.join(
                os.path.abspath("."), self._local_modules_path, local_module
            )

            try:
                self.register_instance(module_name, file_path)
            except Exception as error:
                logger.exception(
                    f"Error loading local module {module_name}: {error}")

        await self.send_on_loads()
        for custom_module in self._db.get(__name__, "modules", []):
            try:
                r = await utils.run_sync(requests.get, custom_module)
                await self.load_module(r.text, r.url)
            except requests.exceptions.RequestException as error:
                logger.exception(
                    f"Error loading third party module {custom_module}: {error}")

        self.warnings = []
        return self.bot_manager.bot
    
    def _init(self, value) -> Any:
        """Init module's attributes"""
        value.db = self._db
        value.manager = self
        value.client = self._client
        value._client = self._client
        value.bot = self.bot_manager
        value.inline = self.bot_manager
        value.prefix = self.get_prefix()
        value.get_prefix = self.get_prefix
        value.lookup = self.lookup

        return value

    def _init_instance(self, instance) -> Any:
        """Init instance"""
        instance.command_handlers = get_command_handlers(instance)
        instance.watcher_handlers = list(
            map(
                lambda x: getattr(instance, x),
                get_watcher_handlers(instance)
            )
        )

        instance.loops = get_loops(instance)
        instance.logger = logging.getLogger(instance.__module__)

        instance.message_handlers = get_message_handlers(instance)
        instance.callback_handlers = get_callback_handlers(instance)
        instance.inline_handlers = get_inline_handlers(instance)

        if (
            not instance.name or 
            instance.name.lower() == 'unknown' and 
            (
                name := getattr(
                    instance, 'strings', {}
                ).get('name', '')
            )
        ):
            instance.name = name
        
        instance.strings = translation.Strings(
            instance, self.translator)
        instance.translator = self.translator

        self.modules.append(instance)
        self.command_handlers.update(instance.command_handlers)
        self.watcher_handlers.extend(instance.watcher_handlers)
        self.loops.append(*instance.loops) if instance.loops else None

        self.message_handlers.update(instance.message_handlers)
        self.callback_handlers.update(instance.callback_handlers)
        self.inline_handlers.update(instance.inline_handlers)

        if instance.loops:
            for loop in self.loops:
                if not getattr(loop, 'method', ''):
                    setattr(loop, 'method', instance)

        for name, func in instance.command_handlers.copy().items():
            if getattr(func, 'alias', ''):
                self.aliases[func.alias] = name

        return instance

    def get_prefix(self) -> list:
        """Returns prefix"""
        return self._db.get('teagram.loader', 'prefixes', ['.'])

    def register_instance(
        self,
        module_name: str,
        file_path: str = "",
        spec: ModuleSpec = None
    ) -> Module:
        spec = spec or spec_from_file_location(module_name, file_path)
        module = module_from_spec(spec)
        sys.modules[module.__name__] = module
        spec.loader.exec_module(module)

        instance = None
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, Module):
                for module in self.modules:
                    if module.__class__.__name__ == value.__name__:
                        self.unload_module(module, True)
                
                warning = value.warning
                if warning not in self.warnings:
                    self.warnings.append(warning)
                    return (value, warning)

                value = self._init(value)
                instance = self._init_instance(value())

        if not instance:
            logger.warn(f"Could not find module class ({module_name})")

        return instance

    async def load_module(
        self, 
        module_source: str, 
        origin: str = "<string>", 
        did_requirements: bool = False
    ) -> str:
        module_name = f"teagram.modules.{utils.random_id()}"

        try:
            spec = ModuleSpec(module_name, StringLoader(
                module_source, origin), origin=origin)
            instance = self.register_instance(module_name, spec=spec)
        except ImportError:
            if did_requirements:
                return True
            try:
                requirements = re.findall(r"# required:\s+([\w-]+(?:\s+[\w-]+)*)", module_source)
            except TypeError:
                logger.error(traceback.format_exc())
                return logger.warning("Installation packages not specified")
            
            if not requirements:
                logger.error(traceback.format_exc())
                return logger.warning("Installation packages not specified")

            logger.info(f"Installing packages: {', '.join(requirements)}...")
            try:
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "--user",
                        requirements,
                    ]
                )
            except subprocess.CalledProcessError as error:
                logger.exception(f"Error installing packages: {error}")

            return await self.load_module(module_source, origin, True)
        except Exception as error:
            return logger.exception(
                f"Error loading module {origin}: {error}")

        if isinstance(instance, tuple):
            return instance

        try:
            await self.send_on_load(instance)
        except Exception as error:
            return logger.exception(error)

        if not isinstance(instance, type):
            return False

        return getattr(instance, "name", instance.__name__[:-3])

    async def send_on_loads(self) -> bool:
        for module in self.modules:
            await self.send_on_load(module)

        return True

    async def send_on_load(self, module: Module) -> bool:
        try:
            await module.on_load()
            _len = len(inspect.getfullargspec(module.client_ready).args)
            if _len >= 2:
                args = [self._client]
                if _len == 3:
                    args.append(self._db)
                await module.client_ready(*args)
            else:
                await module.client_ready()
            
        except Exception as error:
            return logger.exception(error)

        return True

    def unload_module(
        self, 
        module_name: str = None, 
        is_replace: bool = False
    ) -> str:
        if is_replace:
            module = module_name
        else:
            if not (module := self.lookup(module_name)):
                return False
            
            try:
                asyncio.ensure_future(module.on_unload())
            except Exception as error:
                logger.exception(error)

            if (get_module := inspect.getmodule(module)).__spec__.origin != "<string>":
                set_modules = set(self._db.get(__name__, "modules", []))
                self._db.set("teagram.loader", "modules",
                             list(set_modules - {get_module.__spec__.origin}))

            for alias, command in self.aliases.copy().items():
                if command in module.command_handlers:
                    del self.aliases[alias]
                    del self.command_handlers[command]
            
            for loop in self.loops:
                if loop in module.loops:
                    loop.stop()

        self.modules.remove(module)
        self.command_handlers = dict(
            set(self.command_handlers.items()) ^ set(module.command_handlers.items())
        )
        self.watcher_handlers = list(
            set(self.watcher_handlers) ^ set(module.watcher_handlers)
        )

        self.inline_handlers = dict(
            set(self.inline_handlers.items()) ^ set(module.inline_handlers.items())
        )
        self.callback_handlers = dict(
            set(self.callback_handlers.items()) ^ set(module.callback_handlers.items())
        )
        self.loops = list(
            set(self.loops) ^ set(module.loops)
        )

        return module.name

    def lookup(self, name: str) -> Union[Module, None]:
        """Finds module by name"""
        if not isinstance(name, str):
            return None

        module = next((module for module in self.modules if module.name.lower() in name.lower()), None)
        if not module:
            module = next((module for module in self.modules if name.lower() in module.name.lower()), None)
            return module if module else None
        return module
