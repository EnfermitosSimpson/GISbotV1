from flask import Flask, request, make_response
from googleapiclient.discovery import build
import json
import os
from pprint import pprint
import sys
import telebot
from telebot import types
from config import *

import logging
logger = logging.getLogger(__file__)

server = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN)

global allowed_users
try:
    the_file = open('allowed.json', 'r')
    allowed_users = json.loads(the_file.read())
    the_file.close()
except:
    allowed_users = None


def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    try:
        res = service.cse().list(q=search_term, cx=cse_id, searchType='image', **kwargs).execute()
    except Exception:
        return False
    imgs = []
    if 'items' not in res:
        return False
    for item in res['items']:
        imgs.append((item['link'], item['image']['thumbnailLink']))
    return imgs

@bot.message_handler(commands=['add'])
def add_allowed_user(message):
    new_users = message.text.split(" ")[1:]
    if (len(new_users) > 0 and allowed_users is not None and message.from_user.username not in allowed_users):
        return
    if (allowed_users is None):
        global allowed_users
        allowed_users = []

    global allowed_users
    allowed_users = list(set(new_users + allowed_users))
    new_json = json.dumps(allowed_users)
    the_file = open('allowed.json', 'w')
    the_file.write(new_json)
    the_file.close()
    bot.reply_to(message, "New users added")


@bot.inline_handler(lambda query: True)
def default_query(inline_query):
    if (inline_query.query == '' or (allowed_users is not None and inline_query.from_user.username not in allowed_users)):
        return

    if inline_query.offset == '':
        offset = 0
    else:
        offset = int(inline_query.offset)

    search_term = inline_query.query
    search_results = google_search(search_term, CSE_KEY, CSE_CX, safe="off", num=BATCH, start=(offset * BATCH) + 1)

    rs = []
    if not search_results:
        rs.append(types.InlineQueryResultPhoto("1", "https://images-na.ssl-images-amazon.com/images/I/41q1QAln%2BQL._AC_UL320_SR248,320_.jpg", "https://images-na.ssl-images$amazon.com/images/I/41q1QAln%2BQL._AC_UL320_SR248,320_.jpg"))
    else:
        try:
            id = 0
            for each in search_results:
                id += 1
                rs.append(types.InlineQueryResultPhoto(str(id), each[0], each[1]))
        except Exception as e:
            print(e)

    bot.answer_inline_query(inline_query.id, rs, cache_time=2592000, next_offset=offset + 1)


@server.route("{subpath}/bot".format(subpath=NGINX_SUBPATH), methods=['POST'])
def getMessage():
    bot.process_new_updates(
        [telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("{subpath}/".format(subpath=NGINX_SUBPATH))
def webhook():
    webhook = bot.get_webhook_info()
    bot.remove_webhook()
    bot.set_webhook(url="{hostname}{subpath}/bot".format(hostname=WEBHOOK_URL, subpath=NGINX_SUBPATH))
    return "!", 200


if (len(sys.argv) == 2):
    if (POLLING):
        bot.remove_webhook()
        bot.polling()
    else:
        server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 443)))
