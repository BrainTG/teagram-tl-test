import logging

from pyrogram import Client, types

from .. import database, loader, utils

prefix = database.load_db().get('prefix')


@loader.module(name="Logging")
class LoggingModule(loader.Module):
    """Simple logging with teagram"""
    
    # logging messages
    @loader.on(lambda _, __, message: not message.from_user.is_self)
    async def watcher_messages(self, app: Client, message: types.Message):
        return await app.send_message(
            'Teagram Logs',
            '[INFO] 🍵 - message from {}: {}'.format(
                message.from_user.first_name,
                message.text
            )
        )

    # logging commands
    @loader.on(lambda _, __, message: message.text.startswith(prefix))
    async def watcher_commands(self, app: Client, message: types.Message):
        return await app.send_message(
            'Teagram Logs',
            '[INFO] 🍵 - command from {}: {}'.format(
                message.from_user.first_name,
                message.text.split()
            )
        )
