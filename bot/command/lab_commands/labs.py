import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File
from datetime import datetime, timedelta
import csv
import re

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority, PermissionAuthority

logger = logging.getLogger(__name__)

@command.command_class
class LabCheckIn(command.Command):
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __CHECK_IN_DATA = 'check-in-data'
    __DISCORD_ID = 'discord'
    __SECTION_STRING = 'Lab {}'

    __ALLOW_SECOND_CHECKIN = 'allow-second-checkin'
    __FIRST_CHECK_IN = 1
    __SECOND_CHECK_IN = 2
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __WEEKDAY_MAP = {0: 'M', 1: 'Tu', 2: 'W', 3: 'Th', 4: 'F', 5: 'Sa', 6: 'Su'}

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        # if the student is in the text chat of their lab session and the time is at the start then do the first authentication
        # if the student is in the text chat of their lab session and the time is after the second login and the TA has started the second check in process.

        current_lab_channel = None
        the_category: CategoryChannel = self.message.channel.category
        for lab_name in ca.lab_sections:
            if the_category == ca.lab_sections[lab_name]:
                current_lab_channel = ca.lab_sections[lab_name]

        students_group = mongo.db[self.__STUDENTS_GROUP]
        section_collection = mongo.db[self.__SECTION_DATA]
        check_in_collection = mongo.db[self.__CHECK_IN_DATA]

        student_record = students_group.find_one({self.__DISCORD_ID: self.message.author.id})
        today = datetime.today()

        if student_record and current_lab_channel:
            section_name = self.__SECTION_STRING.format(student_record[self.__SECTION])

            # we're in the right section, now we need to check that it's the right time
            if current_lab_channel.name == section_name:
                section_data = section_collection.find_one({'Section Name': section_name})
                check_in_data = check_in_collection.find_one({'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))})
                """ {'_id': ObjectId('5f480a36a6bca0f612b90999'), 'Section': '61', 'Days': 'M', 'Time': '11:00 am - 11:50 am', 'TA': '', 'Nickname': '', 'Section Name': 'Lab 61', 
                    'Section Category': 748625915226882068, 'Text Channel': 748625915839512646, 'Voice Channel': 748625916711665714}
                    2020-08-29 13:46:54.248772
                """
                if section_data:
                    if not check_in_data:
                        todays_record = {'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))}
                        for student in students_group.find({self.__SECTION: student_record[self.__SECTION]}):
                            todays_record[student[self.__USERNAME]] = 0
                        check_in_collection.insert_one(todays_record)
                        check_in_data = check_in_collection.find_one({'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))})

                    # give students a bit of a forgiveness margin
                    margin = timedelta(seconds=30)

                    split_times = section_data['Time'].split('-')
                    matched_group = re.match(r'(?P<hour>\d+):(?P<minute>\d+)\s+(?P<am_pm>(am|pm))', split_times[0].strip())
                    # test day for section 61; today = datetime(year=2020, month=8, day=31, hour=11, minute=3, second=0)

                    the_hour = int(matched_group.group('hour'))
                    the_minute = int(matched_group.group('minute'))

                    if matched_group.group('am_pm') == 'pm':
                        the_hour += 12
                    # combines the current day with the starting time
                    start_time = datetime(year=today.year, month=today.month, day=today.day,
                                          hour=the_hour, minute=the_minute, second=0)

                    if self.__WEEKDAY_MAP[today.weekday()] in section_data['Days']:
                        if start_time - margin <= today <= start_time + timedelta(minutes=15) + margin and check_in_data[student_record[self.__USERNAME]] == 0:
                            check_in_collection.update_one({'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))}, {'$inc': student_record[self.__USERNAME]})
                            await self.message.author.send('You are checked in to your office hours!  Remember to stick around until your TA allows you to confirm your check in. ')
                        elif start_time <= today and check_in_data[student_record[self.__USERNAME]] == self.__FIRST_CHECK_IN and check_in_data[self.__ALLOW_SECOND_CHECKIN]:
                            check_in_collection.update_one({'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))}, {'$inc': student_record[self.__USERNAME]})
                            await self.message.author.send('You have completed your office hour check in requirements.  You should receive full attendance credit. ')
                        else:
                            await self.message.author.send('This is not the correct check in time.')
                    else:
                        await self.message.author.send('This is not the correct day for discussion.')

        elif not student_record:
            await self.message.author.send("We were unable to find you. Talk to you TAs or Professors. ")
        elif not current_lab_channel:
            await self.message.author.send("We couldn't find this section.  Did you send this in your lab channel?")

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!check in'):
            return True
        return False


@command.command_class
class AllowCheckIn(command.Command):
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __CHECK_IN_DATA = 'check-in-data'
    __DISCORD_ID = 'discord'
    __SECTION_STRING = 'Lab {}'

    __ALLOW_SECOND_CHECKIN = 'allow-second-checkin'
    __FIRST_CHECK_IN = 1
    __SECOND_CHECK_IN = 2
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __WEEKDAY_MAP = {0: 'M', 1: 'Tu', 2: 'W', 3: 'Th', 4: 'F', 5: 'Sa', 6: 'Su'}

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        current_lab_channel = None
        the_category: CategoryChannel = self.message.channel.category
        for lab_name in ca.lab_sections:
            if the_category == ca.lab_sections[lab_name]:
                current_lab_channel = ca.lab_sections[lab_name]

        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        section_collection = mongo.db[self.__SECTION_DATA]
        check_in_collection = mongo.db[self.__CHECK_IN_DATA]

        ta_record = ta_group.find_one({self.__DISCORD_ID: self.message.author.id})

        today = datetime.today()

        if ra.ta_or_higher(self.message.author) and current_lab_channel:
            section_name = self.__SECTION_STRING.format(ta_record[self.__SECTION])

            # we're in the right section, now we need to check that it's the right time
            if current_lab_channel.name == section_name:
                section_data = section_collection.find_one({'Section Name': section_name})
                check_in_data = check_in_collection.find_one({'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))})

                if section_data:
                    if not check_in_data:
                        todays_record = {'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))}
                        for student in students_group.find({self.__SECTION: ta_record[self.__SECTION]}):
                            todays_record[student[self.__USERNAME]] = 0
                        check_in_collection.insert_one(todays_record)
                        check_in_data = check_in_collection.find_one({'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))})

                    # give students a bit of a forgiveness margin

                    split_times = section_data['Time'].split('-')
                    matched_group = re.match(r'(?P<hour>\d+):(?P<minute>\d+)\s+(?P<am_pm>(am|pm))', split_times[0].strip())
                    # test day for section 61; today = datetime(year=2020, month=8, day=31, hour=11, minute=3, second=0)

                    the_hour = int(matched_group.group('hour'))
                    the_minute = int(matched_group.group('minute'))

                    if matched_group.group('am_pm') == 'pm':
                        the_hour += 12
                    # combines the current day with the starting time
                    start_time = datetime(year=today.year, month=today.month, day=today.day,
                                          hour=the_hour, minute=the_minute, second=0)

                    if self.__WEEKDAY_MAP[today.weekday()] in section_data['Days']:
                        if start_time <= today <= start_time + timedelta(minutes=15) and check_in_data[ta_record[self.__USERNAME]] == 0:
                            check_in_collection.update_one({'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))}, {'$inc': ta_record[self.__USERNAME]})
                            await self.message.author.send('You are checked in to your office hours!  Remember to stick around until your TA allows you to confirm your check in. ')
                        elif start_time <= today and check_in_data[ta_record[self.__USERNAME]] == self.__FIRST_CHECK_IN and check_in_data[self.__ALLOW_SECOND_CHECKIN]:
                            check_in_collection.update_one({'Section Name': section_name, 'Date': int(today.strftime('%Y%m%d'))}, {'$inc': ta_record[self.__USERNAME]})
                            await self.message.author.send('You have completed your office hour check in requirements.  You should receive full attendance credit. ')
                        else:
                            await self.message.author.send('This is not the correct check in time.')
                    else:
                        await self.message.author.send('This is not the correct day for discussion.')

        elif not ta_record:
            await self.message.author.send("We were unable to find you. You are either not a TA, or otherwise unable to run this command.  ")
        elif not current_lab_channel:
            await self.message.author.send("We couldn't find this section.  Did you send this in your lab channel?")

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab allow check in'):
            return True
        elif message.content.startswith('!lab allow check in conf'):
            return True
        return False

@command.command_class
class GetLabZeroAttendance(command.Command):
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __CHECK_IN_DATA = 'check-in-data'
    __DISCORD_ID = 'discord'
    __SECTION_STRING = 'Lab {}'

    __ALLOW_SECOND_CHECKIN = 'allow-second-checkin'
    __FIRST_CHECK_IN = 1
    __SECOND_CHECK_IN = 2
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        lab_channel: CategoryChannel = ca.find_lab_channel(self.message.channel.category)

        recognized_authors = {}

        students_group = mongo.db[self.__STUDENTS_GROUP]

        if ra.ta_or_higher(self.message.author) and lab_channel:
            for channel in lab_channel.text_channels:
                channel: TextChannel
                channel_history_list = await channel.history(limit=None).flatten()
                for message in channel_history_list:
                    if message.author.id not in recognized_authors:
                        student = students_group.find_one({self.__DISCORD_ID: message.author.id})
                        recognized_authors[message.author.id] = student

            discord_lab_file: File = None
            field_names = {'First-Name', 'Last-Name', self.__USERNAME}
            if recognized_authors:
                section = lab_channel.name
                lab_attendance_file_name = 'lab_attendance_{}_{}.csv'.format(section, datetime.today().strftime('%m.%d.%H.%M.%S'))
                with open(lab_attendance_file_name, 'w', newline='') as lab_attendance_file:
                    writer = csv.DictWriter(lab_attendance_file, fieldnames=field_names)
                    writer.writeheader()
                    for student_id in recognized_authors:
                        if recognized_authors[student_id]:
                            new_line = {col_id: recognized_authors[student_id][col_id] for col_id in field_names}
                            writer.writerow(new_line)
                discord_lab_file = File(open(lab_attendance_file_name, 'rb'))
                await self.message.author.send('Getting Lab 0 Attendance Score', files=[discord_lab_file])
            else:
                await self.message.author.send('No one has checked in yet.')
        else:
            await self.message.author.send('You do not have permission to run the command.')

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab get lab0 grades'):
            return True
        return False
