# TelegramDB
# Copyright (C) 2022
# Anony <github.com/anonyindian>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import inspect, asyncio, nest_asyncio
from logging import Logger, getLogger
from ast import literal_eval
from telethon import TelegramClient
from pyrogram import Client
from typing import Union
from .constants import DP_NAME_SEPARATOR, __version__
from .exceptions import InvalidClient, InvalidDataPack, ReservedCharacter, UnsupportedClient

nest_asyncio.apply()

class Member:
    """
    Member of a :class:`DataPack`.

    Attributes:
        is_primary (:obj:`bool`): Whether the member is a primary key or not.
    """
    def __init__(self, _:type, is_primary:bool=False):
        self.is_primary = is_primary
        return

class DataPack:
    """
    Object that contains all the data in a database.

    Note:
        Members are added as attributes in an inherited class of this object. 

    Attributes:
        __datapack_name__ (:obj:`str`): Name of the :class:`DataPack`.

    """
    __datapack_name__:str

    def __get_dict__(self):
        __dict_to_return = dict(self.__dict__)
        if '__datapack_name__' in __dict_to_return:
            __dict_to_return.pop('__datapack_name__')
        return __dict_to_return
    
    def __query_data__(self):
        return f"{self.__datapack_name__} - {self.__get_dict__()}"

class TelegramDB:
    """
    Main object which initialises the telegram database session.

    Attributes:
        __telegram_client__ (:class:`pyrogram.Client` | :class:`telethon.TelegramClient`): Telegram client which will be used to save database queries on telegram.
        __chat_id__ (:obj:`int` | :obj:`str`): Unique identifier for the target chat or username of the target channel (in the format ``@channelusername``).
        debug (:obj:`bool`, Optional): Database queries will be debugged if it is set to ``True``.
        LOGGER (:class:`logging.Logger`, Optional): Logger which will be used for debugging.
    """
    __datapacks__:dict = {str:{"id":int, "data":str}}
    __dp_cache__:dict = {}
    __publisher_busy__ = False  
    def __init__(self, __telegram_client__: Union[Client, TelegramClient], __chat_id__: Union[int, str]=None, debug: bool=False, LOGGER: Logger=None):
        print(f"""
    TelegramDB v{__version__} Copyright (C) 2022 anonyindian
    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under certain conditions.
            """)
        self.debug = debug
        self.__telegram_client__ = __telegram_client__

        if __chat_id__:
            self.__chat_id__ = __chat_id__
            self.__get_datapacks__()
        else:
            self.__make_chat__()

        if debug:
            self.LOGGER = getLogger() if not LOGGER else LOGGER
        self.__loop__ = asyncio.get_event_loop()
    
    def prepare_datapack(self, datapack_class: DataPack):
        """
        Use this method to initialise the :class:`DataPack` with primary key member.

        Parameters:
            datapack_class (:class:`DataPack`): `DataPack` to be initialised with the primary key.
        
        Returns:
            :obj:`None`
        """
        for i in inspect.getmembers(datapack_class):
            if (
                not i[0].startswith('_')
                and not inspect.ismethod(i[1])
                and isinstance(i[1], Member)
                and i[1].is_primary
            ):
                if self.debug:
                    self.LOGGER.info(f"Initialised {datapack_class} with primary key '{i[0]}'")
                self.__dp_cache__[datapack_class] = i[0]
    
    def commit(self, datapack: DataPack):
        """
        Use this method to save the data on telegram database.

        Parameters:
            datapack (:class:`DataPack`): Subclass of the `DataPack` of the data to be saved on telegram.

        Returns:
            :obj:`None`
        """
        if DP_NAME_SEPARATOR in datapack.__datapack_name__:
            raise ReservedCharacter(datapack.__datapack_name__)
        datapack = self.__fill_datapack(datapack)
        self.__publish_data__(datapack, self.__format_datapack__(datapack))
    
    def __publish_data__(self, datapack: DataPack, data:str):
        """
        This is method is used to publish the committed data on telegram database chat.

        Parameters:
            datapack (:class:`DataPack`): Subclass of the `DataPack` of the data to be published on telegram database.
            data (:obj:`str`): Formatted string of the data to be published on telegram database.

        Returns:
            :obj:`None`
        """
        if client := self.__telegram_client__:
            msg_id = 0
            if datapack.__datapack_name__ in self.__datapacks__:
                msg_id:int = self.__datapacks__[datapack.__datapack_name__]["id"]
            if isinstance(client, Client):
                if msg_id == 0:
                    async def publish():
                        nonlocal msg_id
                        msg_id = (await client.send_message(chat_id=self.__chat_id__, text=data)).message_id
                    self.__loop__.run_until_complete(publish())
                    self.__commit_success__ = True
                else:
                    self.__get_data_from_cache(datapack)
                    if self.__format_datapack__(datapack) == data:
                        self.__commit_success__ = False
                        if self.debug:
                            self.LOGGER.warning(f"Exact values already stored: {datapack.__query_data__()}")
                    else:
                        try:
                            self.__loop__.run_until_complete(client.edit_message_text(chat_id=self.__chat_id__, message_id=msg_id, text=data))
                            self.__commit_success__ = True
                        except:
                            self.__commit_success__ = False
                            if self.debug:
                                self.LOGGER.warning(f"Failed to update: {datapack.__query_data__()}")
                        
            elif isinstance(client, TelegramClient):
                if msg_id == 0:
                    async def publish():
                        nonlocal msg_id
                        msg_id = (await client.send_message(entity=self.__chat_id__, message=data, parse_mode=None)).id
                    self.__loop__.run_until_complete(publish())
                    self.__commit_success__ = True
                else:
                    self.__get_data_from_cache(datapack)
                    if self.__format_datapack__(datapack) == data:
                        self.__commit_success__ = False
                        if self.debug:
                            self.LOGGER.warning(f"Exact values already stored: {datapack.__query_data__()}")
                    else:
                        try:
                            self.__loop__.run_until_complete(client.edit_message(entity=self.__chat_id__, message=msg_id, text=data, parse_mode=None))
                            self.__commit_success__ = True
                        except:
                            self.__commit_success__ = False
                            if self.debug:
                                self.LOGGER.warning(f"Failed to update: {datapack.__query_data__()}")
            else:
                raise InvalidClient()
            if self.debug and self.__commit_success__:
                self.LOGGER.info(datapack.__query_data__())
            self.__datapacks__[datapack.__datapack_name__] = {"id": msg_id, "data":datapack.__get_dict__()}
    
    def get(self, datapack: DataPack):
        """
        Use this method to get the data from telegram database.

        Parameters:
            datapack (:obj:`DataPack`): Object of the `DataPack` of the data to be retrieved from telegram database.

        Returns:
            :obj:`bool`
        """
        return self.__get_data_from_cache(self.__fill_datapack(datapack))

    def __get_data_from_cache(self, datapack: DataPack):
        """
        This method fills data in the provided :obj:`DataPack` from the cache.

        Parameters:
            datapack (:obj:`DataPack`): Object of the `DataPack` of the data to be retrieved from telegram database.

        Returns:
            :obj:`bool`
        """
        if datapack.__datapack_name__ in self.__datapacks__:
            data = self.__datapacks__[datapack.__datapack_name__]["data"]
            for attribute in data:
                setattr(datapack, attribute, data[attribute])
            return True
        return False


    def __format_datapack__(self, datapack: DataPack):
        """
        This method is used to format the :class:`DataPack` in a string which will be published on telegram database chat.

        Parameters:
            datapack (:class:`DataPack`): Subclass of the `DataPack` of the data to be published on telegram database.

        Returns:
            :obj:`str`
        """
        query = f"#{datapack.__datapack_name__}"
        query += f"\n{datapack.__get_dict__()}"
        return query

    def __get_datapacks__(self):
        """
        This method is used to load the existing data from the telegram database chat.

        Returns:
            :obj:`None`
        """
        if isinstance(self.__telegram_client__, Client):
            from pyrogram.types import Message
            for message in self.__telegram_client__.iter_history(self.__chat_id__):
                message: Message = message
                if not message.text:
                    continue
                try:
                    text = message.text.markdown.split("\n", 1)
                    self.__datapacks__[text[0][1:]] = {"id":message.message_id, "data":literal_eval(text[1])}
                except:
                    raise InvalidDataPack(message.message_id)
                
        elif isinstance(self.__telegram_client__, TelegramClient):
            raise UnsupportedClient("telethon")
        else:
            raise InvalidClient()
    
    def __make_chat__(self):
        """
        This method is used to make the telegram database chat if not provided.

        Returns:
            :obj:`None`
        """
        if isinstance(self.__telegram_client__, Client):
            chat = self.__telegram_client__.create_channel("Telegram DB")
            self.__chat_id__ = chat.id
        elif isinstance(self.__telegram_client__, TelegramClient):
            raise UnsupportedClient("telethon")
        else:
            raise InvalidClient()
    
    def __fill_datapack(self, datapack: DataPack):
        """
        This method is used to append the primary key in default name of the datapack, separated by `DP_NAME_SEPARATOR`. 

        Parameters:
            datapack (:class:`DataPack`): Subclass of the `DataPack` of the data to be published on telegram database.

        Returns:
            :class:`DataPack`
        """
        for dp in self.__dp_cache__:
            if isinstance(datapack, dp):
                datapack.__datapack_name__ += f"{DP_NAME_SEPARATOR}" + str(getattr(datapack, self.__dp_cache__[dp]))
                break
        return datapack