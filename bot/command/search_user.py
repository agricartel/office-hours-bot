import logging

from discord import Message, Client, Colour, Embed

import re
import command
import mongo
from datetime import datetime as dt
from datetime import timedelta
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority
from member import MemberAuthority
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class SearchUsers(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_ID = 'discord'
    __DROPPED = 'dropped'

    permissions = {'student': False, 'ta': False, 'admin': True}

    def search_database(self, criteria):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        found_list = []

        for group in [students_group, ta_group, admin_group]:
            found_list.extend([first_name_user for first_name_user in group.find(criteria)])
        return found_list

    @command.Command.authenticate
    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)
        ca: ChannelAuthority = ChannelAuthority(self.message.guild)
        match = re.match(r'!search\s+user\s+(?P<user_identifier>\w+)', self.message.content)

        if ca.is_maintenance_channel(self.message.channel) and match:
            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]

            first_name_list = []
            last_name_list = []
            umbc_id_list = []

            for group in [students_group, ta_group, admin_group]:
                first_name_list.extend([first_name_user for first_name_user in group.find({'First-Name': match.group('user_identifier')})])
                last_name_list.extend([first_name_user for first_name_user in group.find({'Last-Name': match.group('user_identifier')})])
                umbc_id_list.extend([user for user in group.find({'UMBC-Name-Id': match.group('user_identifier')})])

            combined_list = first_name_list + last_name_list + umbc_id_list
            color = Colour(0).dark_gold()
            for person in combined_list:
                db_text = '\n'.join('{}: {}'.format(attr, person[attr]) for attr in person)
                embedded_message = Embed(description=db_text, timestamp=dt.now() + timedelta(hours=4), colour=color)

                await self.message.channel.send(embed=embedded_message)

            if not combined_list:
                await self.message.channel.send('No results were found')
        elif re.match(r'!search\s+user\s+--unauthed', self.message.content):

            found_list = self.search_database({self.__DISCORD_ID: ''})

            color = Colour(0).dark_gold()
            for person in found_list:
                db_text = '\n'.join('{}: {}'.format(attr, person[attr]) for attr in person)
                embedded_message = Embed(description=db_text, timestamp=dt.now() + timedelta(hours=4), colour=color)

                await self.message.channel.send(embed=embedded_message)

            if not found_list:
                await self.message.channel.send('No results were found')
        elif re.match(r'!search\s+user\s+--dropped', self.message.content):

            found_list = self.search_database({self.__DROPPED: True})

            color = Colour(0).dark_gold()
            for person in found_list:
                db_text = '\n'.join('{}: {}'.format(attr, person[attr]) for attr in person)
                embedded_message = Embed(description=db_text, timestamp=dt.now() + timedelta(hours=4), colour=color)

                await self.message.channel.send(embed=embedded_message)

            if not found_list:
                await self.message.channel.send('No results were found')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!search user"):
            return True

        return False
