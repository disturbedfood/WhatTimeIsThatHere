from pprint import pprint
import os.path
import datetime
import pytz
import discord
import re
import json

time_re_12 = re.compile(
    r"(^|\s+)((0?[0-9]:)|(1[0-1]:))([0-5][0-9]) ?(pm|PM)($|\s+)")
time_re_24 = re.compile(
    r"(^|\s+)(([0-1]?[0-9]:)|([1-2][0-3]:))([0-5][0-9])($|\s+)")

def save_data():
    with open("data.json", "w") as f:
        json.dump({
            "user_data": user_data,
            "channel_data": channel_data
        }, f)


def save_settings():
    with open("settings.json", "w") as f:
        json.dump(settings, f)


def safe_get_timezone(tz_input):
    try:
        timezone = pytz.timezone(tz_input)
        return timezone
    except pytz.UnknownTimeZoneError:
        search_attempt = search_timezones(tz_input)
        if len(search_attempt) == 1:
            return safe_get_timezone(search_attempt[0])
        return None


def convert_aware_timestamp(dt_input, to_tz):
    return dt_input.astimezone(to_tz)


def convert_timestamp(dt_input, from_tz, to_tz):
    try:
        return from_tz.localize(dt_input).astimezone(to_tz)
    except ValueError:
        return convert_aware_timestamp(dt_input, to_tz)


def format_date(dt_input):
    return datetime.datetime.strftime(dt_input, "%Y-%m-%d %H:%M")


def search_timezones(query):
    all_timezones = list(pytz.all_timezones)
    return list(filter(lambda x: query.lower() in x.lower(), all_timezones))


def get_time_reply(time_str, author_id, channel_id):
    if len(channel_data[channel_id]) == 0:
        return ""
    local_hour = int(time_str.split(":")[0])
    local_minute = int(time_str.split(":")[1])
    local_timezone = safe_get_timezone(user_data[author_id])
    local_time = datetime.datetime.now(local_timezone).replace(
        hour=local_hour, minute=local_minute)
    reply = "{0} {1}, in different timezones (24h clock):".format(
        format_date(local_time), local_timezone) + "\n--------"
    for tz_name in channel_data[channel_id]:
        tz = safe_get_timezone(tz_name)
        if str(tz) != str(local_timezone):
            reply += "\n{1} - *{0}*".format(tz,
                                            format_date(local_time.astimezone(tz)))
    return reply


def do_search(args, message):
    results = search_timezones(args)
    reply = '\n'.join(results[:10])
    if len(results) > 10:
        reply += '\nMore than 10 results, please be more specific.'
    return reply


def set_local_timezone(args, message):
    tz_result = safe_get_timezone(args)
    reply = "**{0}**: unable to set your timezone to *{1}*. Use *!!tzsearch* to find a correct timezone.".format(
        message.author.name, args)
    if tz_result != None:
        user_data[message.author.id] = str(tz_result)
        save_data()
        reply = "**{0}**: set your timezone to *{1}*".format(
            message.author.name, str(tz_result))
    return reply


def remove_local_timezone(args, message):
    if message.author.id in user_data:
        user_data.pop(message.author.id, None)
        save_data()
        return "**{0}**: your timezone was deleted.".format(message.author.name)
    else:
        return "**{0}**: you do not have a timezone saved.".format(message.author.name)


def add_timezone_to_channel(args, message):
    tz_result = safe_get_timezone(args)
    reply = "**{0}**: unable to add *{1}* to the channel timezones. Use *!!tzsearch* to find a correct timezone.".format(
        message.author.name, args)
    if tz_result != None:
        if message.channel.id not in channel_data:
            channel_data[message.channel.id] = []
        channel_data[message.channel.id].append(str(tz_result))
        save_data()
        reply = "**{0}**: added *{1}* to this channel".format(
            message.author.name, str(tz_result))
    return reply


def remove_timezone_from_channel(args, message):
    if message.channel.id not in channel_data:
        return ""
    tz_result = safe_get_timezone(args)
    old_length = len(channel_data[message.channel.id])
    reply = "**{0}**: could not find *{1}*. Use *!!tzsearch* to find a correct timezone.".format(
        message.author.name, args)
    if tz_result != None:
        channel_data[message.channel.id] = list(
            filter(lambda x: x != str(tz_result), channel_data[message.channel.id]))
        save_data()
        new_len = len(channel_data[message.channel.id])
        if (new_len != old_length):
            reply = "**{0}**: *{1}* was removed from this channel.".format(
                message.author.name, args)
    return reply

def get_timezones_from_channel(args, message):
    if message.channel.id not in channel_data:
        return ""
    return "Channel timezones:\n{0}".format(", ".join(channel_data[message.channel.id]))

def get_time_from_message(message):
    time_12_result = time_re_12.search(message)
    time_24_result = time_re_24.search(message)

    if time_12_result:
        time = time_12_result.group(0).strip()
        split_time = time.split(":")
        hour = str((int(split_time[0]) + 12) % 24)
        minute = split_time[1][:2]
        return "{0}:{1}".format(hour, minute)
    elif time_24_result:
        return time_24_result.group(0).strip()
    return ""


def get_commands(args, message):
    return '''Commands:
    !!tzsearch <query> - search for a valid timezone
    !!tzset <timezone> - set your local timezone
    !!tzdelete - remove your local timezone (you will no longer get an automatic reply when messaging a time)
    !!tzchadd <timezone> - add a timezone to the current channel
    !!tzchdelete <timezone> - remove a timezone from the current channel
    !!tzchlist - lists the timezones assigned to the current channel
    !!tzchtoggle - enable/disable the bot for the current channel (not yet implemented)
    '''


def dummy_command(args, message):
    return "This command is not yet implemented."


commands = {
    "!!tzsearch": do_search,
    "!!tzset": set_local_timezone,
    "!!tzdelete": remove_local_timezone,
    "!!tzchadd": add_timezone_to_channel,
    "!!tzchdelete": remove_timezone_from_channel,
    "!!tzchlist": get_timezones_from_channel,
    "!!tzchtoggle": dummy_command,
    "!!tzcommands": get_commands
}

settings = {}
user_data = {}
channel_data = {}

if not os.path.exists("data.json"):
    with open("defaultsettings.json") as s:
        settings = json.load(s)
    save_settings()

with open("settings.json") as s:
    settings = json.load(s)

if not os.path.exists("data.json"):
    save_data()

with open("data.json") as f:
    data = json.load(f)
    if "user_data" in data:
        user_data = data["user_data"]
    if "channel_data" in data:
        channel_data = data["channel_data"]

client = discord.Client()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.author.id in user_data and message.channel.id in channel_data:
        valid_time = get_time_from_message(message.content)
        if len(valid_time) > 0:
            reply = get_time_reply(
                valid_time, message.author.id, message.channel.id)
            await client.send_message(message.channel, reply)

    for key, value in commands.items():
        if message.content.startswith(key):
            args = message.content[len(key):].strip()
            reply = value(args, message)
            if len(reply) > 0:
                await client.send_message(message.channel, reply)

client.run(settings["token"])
