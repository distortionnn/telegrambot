import io
import json
import string
import subprocess
from datetime import datetime
import sqlite3
import requests
from flask import Flask, request
import base64, hashlib, hmac
import time
import aiosqlite
import buttons
import dbworker
from telebot import TeleBot
from pyqiwip2p import QiwiP2P
from pyqiwip2p import AioQiwiP2P
from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot
import emoji as e
import asyncio
import threading
from telebot import types
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
from outline_vpn.outline_vpn import OutlineVPN
import random
app = Flask(__name__)
ENCODING = 'utf-8'

import asyncio
from WalletPay import AsyncWalletPayAPI


from buttons import main_buttons
from dbworker import User

with open("config.json", encoding="utf-8") as file_handler:
    CONFIG=json.load(file_handler)
    dbworker.CONFIG=CONFIG
    buttons.CONFIG=CONFIG
with open("texts.json", encoding="utf-8") as file_handler:
    text_mess = json.load(file_handler)
    texts_for_bot=text_mess

DBCONNECT="data.sqlite"
BOTAPIKEY=CONFIG["tg_token"]
apiWallet = AsyncWalletPayAPI(api_key=CONFIG["tg_wallet_token"])

bot = AsyncTeleBot(CONFIG["tg_token"], state_storage=StateMemoryStorage())
#QIWI_PRIV_KEY = CONFIG["qiwi_key"]

#p2p = AioQiwiP2P(auth_key=QIWI_PRIV_KEY,alt="zxcvbnm.online")
class MyStates(StatesGroup):
    findUserViaId = State()
    editUser = State()
    editUserResetTime = State()

    UserAddTimeDays = State()
    UserAddTimeHours = State()
    UserAddTimeMinutes = State()
    UserAddTimeApprove = State()
    ServerAdd = State()
    ServerAddName = State()
    ServerAddIP = State()
    ServerAddPass = State()
    ServerAddUrl = State()
    ServerAddCerSha = State()
    ServerDelet = State()

    AdminNewUser = State()
    AdminNewUrl = State()
    AdminMessage = State()

@bot.message_handler(commands=['start'])
async def start(message:types.Message):
    if message.chat.type == "private":
        await bot.delete_state(message.from_user.id)
        user_dat = await User.GetInfo(message.chat.id)
        if user_dat.registered:
            await bot.send_message(message.chat.id,"Информация о подписке",parse_mode="HTML",reply_markup=await main_buttons(user_dat))
        else:
            try:
                username = "@" + str(message.from_user.username)
            except:

                username = str(message.from_user.id)

            await user_dat.Adduser(username,message.from_user.full_name)
            user_dat = await User.GetInfo(message.chat.id)
            await bot.send_message(message.chat.id,e.emojize(texts_for_bot["hello_message"]),parse_mode="HTML",reply_markup=await main_buttons(user_dat))
            await bot.send_message(message.chat.id,e.emojize(texts_for_bot["trial_message"]))



@bot.message_handler(state=MyStates.ServerDelet, content_types=["text"])
async def DeleteServers(m: types.Message):
    ip = str(m.text).strip()
    if e.demojize(ip) == 'Вернутья :right_arrow_curving_left:':
        await bot.send_message(m.from_user.id, "Вернул вас назад!", reply_markup=await buttons.admin_buttons_server())
        await bot.delete_state(m.from_user.id)
        await bot.reset_data(m.from_user.id)
        return
    user_dat = await User.GetInfo(int(m.chat.id))
    flag = await user_dat.DeleteServer(ip=ip)
    if flag:
        await bot.send_message(m.from_user.id, e.emojize("*Сервер удален*"), parse_mode= 'Markdown',reply_markup=await buttons.admin_buttons())
    else:
        await bot.send_message(m.from_user.id, e.emojize("*Ошибка при удалении* :double_exclamation_mark:"), parse_mode='Markdown', reply_markup=await buttons.admin_buttons())
    await bot.delete_state(m.from_user.id)
    await bot.reset_data(m.from_user.id)


@bot.message_handler(state=MyStates.ServerAddName, content_types=["text"])
async def addNameServer(m: types.Message):
    if e.demojize(m.text) == 'Вернутья :right_arrow_curving_left:':
        await bot.send_message(m.from_user.id, "Вернул вас назад!", reply_markup=await buttons.admin_buttons_server())
        await bot.delete_state(m.from_user.id)
        await bot.reset_data(m.from_user.id)
        return
    async with bot.retrieve_data(m.from_user.id) as data:
        data['serverName'] = m.text.strip()
    await bot.set_state(m.from_user.id,MyStates.ServerAddIP)
    await bot.send_message(m.from_user.id, e.emojize("Напишите *IP* сервера"), parse_mode= 'Markdown')

@bot.message_handler(state=MyStates.ServerAddIP, content_types=["text"])
async def addIpServer(m: types.Message):
    if e.demojize(m.text) == 'Вернутья :right_arrow_curving_left:':
        await bot.send_message(m.from_user.id, "Вернул вас назад!", reply_markup=await buttons.admin_buttons_server())
        await bot.delete_state(m.from_user.id)
        await bot.reset_data(m.from_user.id)
        return
    async with bot.retrieve_data(m.from_user.id) as data:
        data['ip'] = m.text.strip()
    await bot.set_state(m.from_user.id,MyStates.ServerAddPass)
    await bot.send_message(m.from_user.id, e.emojize("Напишите пароль для сервера"))

@bot.message_handler(state=MyStates.ServerAddPass, content_types=["text"])
async def addPassServer(m: types.Message):
    if e.demojize(m.text) == 'Вернутья :right_arrow_curving_left:':
        await bot.send_message(m.from_user.id, "Вернул вас назад!", reply_markup=await buttons.admin_buttons_server())
        await bot.delete_state(m.from_user.id)
        await bot.reset_data(m.from_user.id)
        return
    async with bot.retrieve_data(m.from_user.id) as data:
        data['pass'] = m.text.strip()
    await bot.set_state(m.from_user.id,MyStates.ServerAddUrl)
    await bot.send_message(m.from_user.id, e.emojize("Напишите URL для доступа к Management API"))

@bot.message_handler(state=MyStates.ServerAddUrl, content_types=["text"])
async def addUrlServer(m: types.Message):
    if e.demojize(m.text) == 'Вернутья :right_arrow_curving_left:':
        await bot.send_message(m.from_user.id, "Вернул вас назад!", reply_markup=await buttons.admin_buttons_server())
        await bot.delete_state(m.from_user.id)
        await bot.reset_data(m.from_user.id)
        return
    async with bot.retrieve_data(m.from_user.id) as data:
        data['url'] = m.text.strip()
    await bot.set_state(m.from_user.id,MyStates.ServerAddCerSha)
    await bot.send_message(m.from_user.id, e.emojize("Напишите certSha256"))

async  def AddChekServe(m: types.Message, name,ip,pas,url,cersha):
    user_dat = await User.GetInfo(int(m.chat.id))
    if not await user_dat.CheckClient(url,cersha):
        await bot.send_message(m.from_user.id, e.emojize("Ошибка подключения"),reply_markup=await buttons.admin_buttons_server_back())
        return False
    if not await user_dat.AddServer(name=name, ip=ip, password=pas, url=url, cersha=cersha):
        bot.send_message(m.from_user.id, e.emojize("Ошибка при добавлении в БД"),reply_markup=await buttons.admin_buttons_server_back())
        return False
    return True


@bot.message_handler(state=MyStates.ServerAddCerSha, content_types=["text"])
async def addCerShaServer(m: types.Message):
    if e.demojize(m.text) == 'Вернутья :right_arrow_curving_left:':
        await bot.send_message(m.from_user.id, "Вернул вас назад!", reply_markup=await buttons.admin_buttons_server())
        await bot.delete_state(m.from_user.id)
        await bot.reset_data(m.from_user.id)
        return
    async with bot.retrieve_data(m.from_user.id) as data:
        name = data['serverName']
        ip = data['ip']
        pas = data['pass']
        url = data['url']
        cersha = m.text.strip()
    if await AddChekServe(m,name,ip,pas,url,cersha):
        await bot.send_message(m.from_user.id, e.emojize(
        f"Сервер:\n Имя: {name}\n ip: {ip}\n Пароль: {pas}\n Url: {url}\n certSha256: {cersha}\n Добавлен"),
                           reply_markup=await buttons.admin_buttons_server())
    await bot.reset_data(m.from_user.id)
    await bot.delete_state(m.from_user.id)


@bot.message_handler(state=MyStates.editUser, content_types=["text"])
async def Work_with_Message(m: types.Message):
    async with bot.retrieve_data(m.from_user.id) as data:
        tgid=data['usertgid']
    user_dat = await User.GetInfo(tgid)
    if e.demojize(m.text) == "Назад :right_arrow_curving_left:":
        await bot.reset_data(m.from_user.id)
        await bot.delete_state(m.from_user.id)
        await bot.send_message(m.from_user.id,"Вернул вас назад!",reply_markup=await buttons.admin_buttons())
        return
    if e.demojize(m.text) == "Добавить время":
        await bot.set_state(m.from_user.id,MyStates.UserAddTimeDays)
        Butt_skip = types.ReplyKeyboardMarkup(resize_keyboard=True)
        Butt_skip.add(types.KeyboardButton(e.emojize(f"Пропустить :next_track_button:")))
        await bot.send_message(m.from_user.id,"Введите сколько дней хотите добавить:",reply_markup=Butt_skip)
        return
    if e.demojize(m.text) == "Обнулить время":
        await bot.set_state(m.from_user.id,MyStates.editUserResetTime)
        Butt_skip = types.ReplyKeyboardMarkup(resize_keyboard=True)
        Butt_skip.add(types.KeyboardButton(e.emojize(f"Да")))
        Butt_skip.add(types.KeyboardButton(e.emojize(f"Нет")))
        await bot.send_message(m.from_user.id,"Вы уверены что хотите сбросить время для этого пользователя ?",reply_markup=Butt_skip)
        return

@bot.message_handler(state=MyStates.editUserResetTime, content_types=["text"])
async def Work_with_Message(m: types.Message):
    async with bot.retrieve_data(m.from_user.id) as data:
        tgid=data['usertgid']

    if e.demojize(m.text) == "Да":
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        await db.execute(f"Update userss set subscription = ?, banned=false, notion_oneday=true where tgid=?",(str(int(time.time())), tgid))
        await db.commit()
        await db.close()
        await bot.send_message(m.from_user.id,"Время сброшено!")

    async with bot.retrieve_data(m.from_user.id) as data:
        usertgid = data['usertgid']
    user_dat = await User.GetInfo(usertgid)
    readymes = f"Пользователь: <b>{str(user_dat.fullname)}</b> ({str(user_dat.username)})\nTG-id: <code>{str(user_dat.tgid)}</code>\n\n"

    if int(user_dat.subscription) > int(time.time()):
        readymes += f"Подписка: до <b>{datetime.utcfromtimestamp(int(user_dat.subscription)+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')}</b> :check_mark_button:"
    else:
        readymes += f"Подписка: закончилась <b>{datetime.utcfromtimestamp(int(user_dat.subscription)+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')}</b> :cross_mark:"
    await bot.set_state(m.from_user.id, MyStates.editUser)

    await bot.send_message(m.from_user.id, e.emojize(readymes),
                               reply_markup=await buttons.admin_buttons_edit_user(user_dat), parse_mode="HTML")

@bot.message_handler(state=MyStates.UserAddTimeDays, content_types=["text"])
async def Work_with_Message(m: types.Message):
    if e.demojize(m.text) == "Пропустить :next_track_button:":
        days=0
    else:
        try:
            days=int(m.text)
        except:
            await bot.send_message(m.from_user.id,"Должно быть число!\nПопробуйте еще раз.")
            return
        if days<0:
            await bot.send_message(m.from_user.id, "Не должно быть отрицательным числом!\nПопробуйте еще раз.")
            return

    async with bot.retrieve_data(m.from_user.id) as data:
        data['days']= days
    await bot.set_state(m.from_user.id,MyStates.UserAddTimeHours)
    Butt_skip = types.ReplyKeyboardMarkup(resize_keyboard=True)
    Butt_skip.add(types.KeyboardButton(e.emojize(f"Пропустить :next_track_button:")))
    await bot.send_message(m.from_user.id, "Введите сколько часов хотите добавить:", reply_markup=Butt_skip)
    
@bot.message_handler(state=MyStates.UserAddTimeHours, content_types=["text"])
async def Work_with_Message(m: types.Message):
    if e.demojize(m.text) == "Пропустить :next_track_button:":
        hours=0
    else:
        try:
            hours=int(m.text)
        except:
            await bot.send_message(m.from_user.id,"Должно быть число!\nПопробуйте еще раз.")
            return
        if hours<0:
            await bot.send_message(m.from_user.id, "Не должно быть отрицательным числом!\nПопробуйте еще раз.")
            return

    async with bot.retrieve_data(m.from_user.id) as data:
        data['hours']= hours
    await bot.set_state(m.from_user.id,MyStates.UserAddTimeMinutes)
    Butt_skip = types.ReplyKeyboardMarkup(resize_keyboard=True)
    Butt_skip.add(types.KeyboardButton(e.emojize(f"Пропустить :next_track_button:")))
    await bot.send_message(m.from_user.id, "Введите сколько минут хотите добавить:", reply_markup=Butt_skip)

@bot.message_handler(state=MyStates.UserAddTimeMinutes, content_types=["text"])
async def Work_with_Message(m: types.Message):
    if e.demojize(m.text) == "Пропустить :next_track_button:":
        minutes=0
    else:
        try:
            minutes=int(m.text)
        except:
            await bot.send_message(m.from_user.id,"Должно быть число!\nПопробуйте еще раз.")
            return
        if minutes<0:
            await bot.send_message(m.from_user.id, "Не должно быть отрицательным числом!\nПопробуйте еще раз.")
            return

    async with bot.retrieve_data(m.from_user.id) as data:
        data['minutes']= minutes
        hours= data['hours']
        days = data['days']
        tgid = data['usertgid']

    await bot.set_state(m.from_user.id,MyStates.UserAddTimeApprove)
    Butt_skip = types.ReplyKeyboardMarkup(resize_keyboard=True)
    Butt_skip.add(types.KeyboardButton(e.emojize(f"Да")))
    Butt_skip.add(types.KeyboardButton(e.emojize(f"Нет")))
    await bot.send_message(m.from_user.id, f"Пользователю {str(tgid)} добавится:\n\nДни: {str(days)}\nЧасы: {str(hours)}\nМинуты: {str(minutes)}\n\nВсе верно ?", reply_markup=Butt_skip)


@bot.message_handler(state=MyStates.UserAddTimeApprove, content_types=["text"])
async def Work_with_Message(m: types.Message):
    all_time=0
    if e.demojize(m.text) == "Да":
        async with bot.retrieve_data(m.from_user.id) as data:
            minutes=data['minutes']
            hours = data['hours']
            days = data['days']
            tgid = data['usertgid']
        all_time+=minutes*60
        all_time+=hours*60*60
        all_time += days * 60 * 60*24
        await AddTimeToUser(tgid,all_time)
        await bot.send_message(m.from_user.id, e.emojize("Время добавлено пользователю!"), parse_mode="HTML")



    async with bot.retrieve_data(m.from_user.id) as data:
        usertgid = data['usertgid']
    user_dat = await User.GetInfo(usertgid)
    readymes = f"Пользователь: <b>{str(user_dat.fullname)}</b> ({str(user_dat.username)})\nTG-id: <code>{str(user_dat.tgid)}</code>\n\n"

    if int(user_dat.subscription) > int(time.time()):
        readymes += f"Подписка: до <b>{datetime.utcfromtimestamp(int(user_dat.subscription)+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')}</b> :check_mark_button:"
    else:
        readymes += f"Подписка: закончилась <b>{datetime.utcfromtimestamp(int(user_dat.subscription)+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')}</b> :cross_mark:"
    await bot.set_state(m.from_user.id, MyStates.editUser)

    await bot.send_message(m.from_user.id, e.emojize(readymes),
                               reply_markup=await buttons.admin_buttons_edit_user(user_dat), parse_mode="HTML")

@bot.message_handler(state=MyStates.AdminMessage, content_types=['text'])
async def Work_with_Message(m: types.Message):
    if m.text == e.emojize("Вернутья :right_arrow_curving_left:"):
        await bot.send_message(m.from_user.id, "Вернул вас назад",
                               reply_markup=await buttons.admin_buttons())
        await bot.delete_state(m.from_user.id)
        return
    user_dat = await User.GetInfo(m.chat.id)
    allusers = await user_dat.GetAllUsers()
    for user in allusers:
        try:
            await bot.send_message(user['tgid'], m.text)
        except:
            continue
    await bot.delete_state(m.from_user.id)
@bot.message_handler(state=MyStates.findUserViaId, content_types=["text"])
async def Work_with_Message(m: types.Message):
    await bot.delete_state(m.from_user.id)
    try:
        user_id=int(m.text)
    except:
        await bot.send_message(m.from_user.id,"Неверный Id!",reply_markup=await buttons.admin_buttons())
        return
    user_dat = await User.GetInfo(user_id)
    if not user_dat.registered:
        await bot.send_message(m.from_user.id, "Такого пользователя не существует!", reply_markup=await buttons.admin_buttons())
        return

    readymes=f"Пользователь: <b>{str(user_dat.fullname)}</b> ({str(user_dat.username)})\nTG-id: <code>{str(user_dat.tgid)}</code>\n\n"

    if int(user_dat.subscription)>int(time.time()):
        readymes+=f"Подписка: до <b>{datetime.utcfromtimestamp(int(user_dat.subscription)+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')}</b> :check_mark_button:"
    else:
        readymes += f"Подписка: закончилась <b>{datetime.utcfromtimestamp(int(user_dat.subscription)+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')}</b> :cross_mark:"
    await bot.set_state(m.from_user.id,MyStates.editUser)
    async with bot.retrieve_data(m.from_user.id) as data:
        data['usertgid'] = user_dat.tgid
    await bot.send_message(m.from_user.id,e.emojize(readymes),reply_markup=await buttons.admin_buttons_edit_user(user_dat),parse_mode="HTML")

@bot.message_handler(state=MyStates.AdminNewUser, content_types=["text"])
async def Work_with_Message(m: types.Message):
    if e.demojize(m.text) == "Назад :right_arrow_curving_left:":
        await bot.delete_state(m.from_user.id)
        await bot.send_message(m.from_user.id,"Вернул вас назад!",reply_markup=await buttons.admin_buttons())
        return
    async with bot.retrieve_data(m.from_user.id) as data:
        data['keyname'] = m.text
    await bot.set_state(m.from_user.id,MyStates.AdminNewUrl)
    await bot.send_message(m.from_user.id,e.emojize("Введите url серверка к которому хотите создать ключ"),reply_markup=await buttons.admin_buttons_back())

@bot.message_handler(state=MyStates.AdminNewUrl, content_types=["text"])
async def Work_with_Message(m: types.Message):
    if e.demojize(m.text) == "Назад :right_arrow_curving_left:":
        await bot.delete_state(m.from_user.id)
        await bot.reset_data(m.from_user.id)
        await bot.send_message(m.from_user.id,"Вернул вас назад!",reply_markup=await buttons.admin_buttons())
        return

    async with bot.retrieve_data(m.from_user.id) as data:
        keyname = data['keyname']
    db = await aiosqlite.connect(DBCONNECT)
    db.row_factory = sqlite3.Row
    c = await db.execute(f"SELECT * FROM servers WHERE url=?", (m.text,))
    log = await c.fetchall()
    if len(log) == 0:
        await bot.send_message(
            m.from_user.id, "Ошибка добавления пользователя!",
            reply_markup=await buttons.admin_buttons_static_users()
        )
        await bot.delete_state(m.from_user.id)
        await bot.reset_data(m.from_user.id)
        return
    await db.execute(f"INSERT INTO static_profiles (name,url) values (?,?)",
                     (keyname, m.text,))
    await db.commit()
    await c.close()
    await db.close()
    key = await User.AdminAddConfigServer(m.from_user,m.text,log[0][5],keyname)

    await bot.delete_state(m.from_user.id)
    await bot.reset_data(m.from_user.id)
    await bot.send_message(m.from_user.id,"Пользователь добавлен!", reply_markup=await buttons.admin_buttons_static_users())
    return

async def checkSpaceServer(m):
    space = await User.countSpace(m)
    occupiedSpace = space[1]
    allSpace = space[0]
    if allSpace-occupiedSpace < CONFIG['max_people_server']*2:
        await bot.send_message(CONFIG['admin_tg_id'], f'Системное сообщение\nОсталось '
                                                      f'{allSpace-occupiedSpace} свободных мест на серверах', parse_mode='HTML')



@bot.message_handler(state="*", content_types=["text"])
async def Work_with_Message(m: types.Message):
    user_dat = await User.GetInfo(m.chat.id)


    if user_dat.registered == False:
        try:
            username = "@" + str(m.from_user.username)
        except:

            username = str(m.from_user.id)

        await user_dat.Adduser(username,m.from_user.full_name)
        await bot.send_message(m.chat.id,
                               texts_for_bot["hello_message"],
                               parse_mode="HTML", reply_markup=await main_buttons(user_dat))
        return
    await user_dat.CheckNewNickname(m)

    if m.from_user.id==CONFIG["admin_tg_id"]:
        if e.demojize(m.text) == "Админ-панель :smiling_face_with_sunglasses:":
            await bot.send_message(m.from_user.id,f"Админ панель",reply_markup=await buttons.admin_buttons())
            return
        if e.demojize(m.text) == "Главное меню :right_arrow_curving_left:":
            await bot.send_message(m.from_user.id, e.emojize("Админ-панель :smiling_face_with_sunglasses:"), reply_markup=await main_buttons(user_dat))
            return
        if e.demojize(m.text) == "Вывести пользователей :bust_in_silhouette:":
            await bot.send_message(m.from_user.id, e.emojize("Выберите каких пользователей хотите вывести."),
                                   reply_markup=await buttons.admin_buttons_output_users())
            return
        if e.demojize(m.text) == "Отправить уведомление :speech_balloon:":
            await bot.send_message(m.from_user.id, e.emojize("Напишите текст сообщения которое увидят все пользователи"),
                                   reply_markup=await buttons.admin_buttons_server_back())
            await bot.set_state(m.from_user.id, MyStates.AdminMessage)
            return
        
        if e.demojize(m.text) == "Сервера :desktop_computer:":
            await bot.send_message(m.from_user.id, e.emojize("Управление серверами :abacus:"), reply_markup=await buttons.admin_buttons_server())

        if e.demojize(m.text) == "Вернутья :right_arrow_curving_left:":
            await bot.send_message(m.from_user.id, "Админ панель", reply_markup=await buttons.admin_buttons_server())
            return

        if e.demojize(m.text) == "Назад :right_arrow_curving_left:":
            await bot.send_message(m.from_user.id, "Админ панель", reply_markup=await buttons.admin_buttons())
            return

        if e.demojize(m.text) == "Все сервера :bar_chart:":
            allservers = await user_dat.GetServers()
            result = ''
            if len(allservers) != 0:
                await bot.send_message(m.from_user.id, e.emojize(f"Все сервера:"), reply_markup=await buttons.admin_buttons_server())
                for elem in allservers:
                    result = (f"Имя: {str(allservers[elem]['s'][1])}\nIP: <code>{str(allservers[elem]['s'][2])}</code>\nПароль: <code>{str(allservers[elem]['s'][3])}</code>\n"
                              f"URL: {str(allservers[elem]['s'][4])}\nCertSha256: {str(allservers[elem]['s'][5])}\nЗанято: {str(allservers[elem]['space'])}")
                    await bot.send_message(m.from_user.id, e.emojize(result),parse_mode="HTML")
            else:
                await bot.send_message(m.from_user.id, e.emojize(f'Серверов нет :double_exclamation_mark:'),reply_markup=await buttons.admin_buttons_server())
            return

        if e.demojize(m.text) == "Добавить сервер :plus:":
            await bot.set_state(m.from_user.id, MyStates.ServerAddName)
            await bot.send_message(m.from_user.id, e.emojize("Напишите название сервера"),reply_markup=await buttons.admin_buttons_server_back())

        if e.demojize(m.text) == "Удалить сервер :fire:":
            await bot.set_state(m.from_user.id, MyStates.ServerDelet)
            await bot.send_message(m.from_user.id, e.emojize("Напишите ip сервера"), reply_markup=await buttons.admin_buttons_server_back())

        if e.demojize(m.text) == "Всех пользователей":
            allusers= await user_dat.GetAllUsers()
            count = 1
            readymes=""
            for i in allusers:
                if int(i[2])>int(time.time()):
                    readymes+=f"{count}) {i[6]} ({i[5]}|{str(i[1])}) ✅\n"
                else:
                    readymes += f"{count}) {i[6]} ({i[5]}|{str(i[1])})\n"
                count+=1

            with open('All_client.txt', 'w', encoding='utf8') as file:
                file.write(readymes)
            try:
                with open('All_client.txt', 'rb') as file:
                    await bot.send_message(m.from_user.id, e.emojize('Файл со всеми пользователями:\n'
                                                                     '✅ отмечаются пользователи у которых есть подписка'),
                                           reply_markup=await buttons.admin_buttons(),
                                           parse_mode="HTML")
                    await bot.send_document(m.from_user.id, file, reply_markup= await buttons.admin_buttons())
            except :
                    await bot.send_message(m.from_user.id, e.emojize("Ошибка при выводе всех пользователей"), reply_markup=await buttons.admin_buttons(),parse_mode="HTML")
            return

        if e.demojize(m.text) == "Пользователей с подпиской":
            allusers=await user_dat.GetAllUsersWithSub()
            readymes=""
            count = 1
            if len(allusers)==0:
                await bot.send_message(m.from_user.id, e.emojize("Нету пользователей с подпиской!"), reply_markup=await buttons.admin_buttons(),parse_mode="HTML")
                return
            for i in allusers:
                if int(i[2])>int(time.time()):
                    readymes+=f"{count}) {i[6]} ({i[5]}|{str(i[1])}) - {datetime.utcfromtimestamp(int(i[2])+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')}\n\n"
                    count +=1
            with open('Client_subscription.txt', 'w', encoding='utf8') as file:
                file.write(readymes)
            try:
                with open('Client_subscription.txt', 'rb') as file:
                    await bot.send_message(m.from_user.id, e.emojize('Файл с пользователями у которых активка подписка:\n'),
                                           reply_markup=await buttons.admin_buttons(),
                                           parse_mode="HTML")
                    await bot.send_document(m.from_user.id, file, reply_markup= await buttons.admin_buttons())
            except :
                    await bot.send_message(m.from_user.id, e.emojize("Ошибка при выводе пользователей с подпиской"), reply_markup=await buttons.admin_buttons(),parse_mode="HTML")
            return

        if e.demojize(m.text) == "Вывести статичных пользователей":
            db = await aiosqlite.connect(DBCONNECT)
            c =  await db.execute(f"select * from static_profiles")
            all_staticusers = await c.fetchall()
            await c.close()
            await db.close()
            if len(all_staticusers)==0:
                await bot.send_message(m.from_user.id,"Статичных пользователей нету!")
                return
            for i in all_staticusers:
                Butt_delete_account = types.InlineKeyboardMarkup()
                Butt_delete_account.add(types.InlineKeyboardButton(e.emojize("Удалить пользователя :cross_mark:"), callback_data=f'DELETE:{str(i[0])}'))
                url = str(i[2])
                keyname = str(i[1])
                config = await User.GetAdminServer(m.from_user,url,keyname)
                await bot.send_message(m.chat.id,f"<code>{config}</code>\nПользователь: <code>{str(i[1])}</code>", parse_mode="HTML", reply_markup=Butt_delete_account)
            return

        if e.demojize(m.text) =="Редактировать пользователя по id :pencil:":
            await bot.send_message(m.from_user.id,"Введите Telegram Id пользователя:",reply_markup=types.ReplyKeyboardRemove())
            await bot.set_state(m.from_user.id,MyStates.findUserViaId)
            return

        if e.demojize(m.text) =="Статичные":
            await bot.send_message(m.from_user.id,"Выберите пункт меню:",reply_markup=await buttons.admin_buttons_static_users())
            return

        if e.demojize(m.text) =="Добавить пользователя :plus:":
            await bot.send_message(m.from_user.id,"Введите имя для нового пользователя!",reply_markup=await buttons.admin_buttons_back())
            await bot.set_state(m.from_user.id,MyStates.AdminNewUser)
            return

    if e.demojize(m.text) == "Узнать о VPN :thinking_face:":
        await bot.send_message(m.chat.id,text_mess['about_message'], parse_mode="HTML")

    if e.demojize(m.text) == "Продлить :money_bag:":
        payment_info= await user_dat.PaymentInfo()
        if CONFIG['tg_shop_token'] or CONFIG['tg_wallet_token']:
            Butt_payment = types.InlineKeyboardMarkup()
            Butt_payment.add(
                types.InlineKeyboardButton(e.emojize(f"1 мес. 📅 - {str(CONFIG['one_month_cost'])} руб."), callback_data="BuyMonth:1"))
            Butt_payment.add(
                types.InlineKeyboardButton(e.emojize(f"3 мес. 📅 - {str(CONFIG['three_month_cost'])} руб."), callback_data="BuyMonth:3"))
            Butt_payment.add(
                types.InlineKeyboardButton(e.emojize(f"6 мес. 📅 - {str(CONFIG['six_month_cost'])} руб."), callback_data="BuyMonth:6"))
            await bot.send_message(m.chat.id,
                                   "Выберите на сколько месяцев хотите приобрести подписку:",
                                   reply_markup=Butt_payment, parse_mode="HTML")
        else:
            await bot.send_message(m.chat.id,"Оплата в данный момент невозможна, попробуйте позже")

    if e.demojize(m.text) == "Подключить VPN :gear:":
        if user_dat.trial_subscription == False:
            Butt_how_to = types.InlineKeyboardMarkup()
            Butt_how_to.add(
                types.InlineKeyboardButton(e.emojize("Инструкция для iPhone"), url="https://telegra.ph/Instrukciya-po-ustanovke-Outline-na-iPhone-08-19"))
            Butt_how_to.add(
                types.InlineKeyboardButton(e.emojize("Инструкция для Android"), url="https://telegra.ph/Instrukciya-po-ustanovke-Outline-na-Android-08-19"))
            Butt_how_to.add(
                types.InlineKeyboardButton(e.emojize("Инструкция для Windows"),url="https://telegra.ph/Instrukciya-na-ustanovku-Outline-Windows-08-19"))
            Butt_how_to.add(
                types.InlineKeyboardButton(e.emojize("Проверить VPN"),url="https://2ip.ru/"))
            ConfigUser = await User.CheckUserServer(user_dat)
            freeServer = {}
            if not ConfigUser:
                freeServer = await User.freeServer(user_dat,CONFIG["max_people_server"])
            if len(freeServer) != 0 or ConfigUser:
                if ConfigUser:
                    config = await User.GetUserServer(self=user_dat)
                else:
                    config = await User.AddConfigServer(self=user_dat,id=user_dat.tgid,freeServer=freeServer,max_people_server=CONFIG["max_people_server"])
                    await checkSpaceServer(m)
                await bot.send_message(m.chat.id,e.emojize(f"<code>{config}</code>"), parse_mode="HTML")
                await bot.send_message(chat_id=m.chat.id,text=e.emojize(f"{texts_for_bot['how_to_connect_info']}"), parse_mode="HTML",reply_markup=Butt_how_to)
            else:
                await bot.send_message(m.chat.id, e.emojize(f"Свободных серверов нет\nПопробуйте позже"))
        else:
            await bot.send_message(chat_id=m.chat.id,text="Сначала нужно купить подписку!")

async def PyWallet(order,time,call,Month_count):
    tic = 0
    while tic < time:
        # Get order preview
        order_preview = await apiWallet.get_order_preview(order_id=order.id)
        # Check if the order is paid
        if order_preview.status == "PAID":
            await addTimePament(call, Month_count)
            return
        tic +=2
        await asyncio.sleep(2)
    return

async def get_amount(mount_count):
    price = 1000
    if (mount_count == 1):
        price = CONFIG['one_month_cost']
    elif (mount_count == 3):
        price = CONFIG['three_month_cost']
    elif (mount_count == 6):
        price = CONFIG['six_month_cost']
    return price

async def NewOrder(idUser,idorder,mountCount):
    order = await apiWallet.create_order(
        amount = await get_amount(mountCount),
        currency_code="RUB",
        description=f"Оплата VPN на {mountCount} мес.",
        external_id=idorder,
        timeout_seconds=60,
        customer_telegram_user_id=idUser
    )
    return order

@bot.callback_query_handler(func=lambda c: 'BuyMonth:' in c.data)
async def Buy_month(call: types.CallbackQuery):
    user_dat = await User.GetInfo(call.from_user.id)
    payment_info = await user_dat.PaymentInfo()
    if payment_info is None:
        Month_count=int(str(call.data).split(":")[1])
        await bot.delete_message(call.message.chat.id, call.message.id)
        payInline = types.InlineKeyboardMarkup()
        if CONFIG['tg_wallet_token']:
            payInline.add(types.InlineKeyboardButton(e.emojize(":gem_stone: Wallet Pay"), callback_data=f"PayWallet:{Month_count}"))
        if CONFIG['tg_shop_token']:
            payInline.add(types.InlineKeyboardButton(e.emojize("🇷🇺 Оплата картой"), callback_data=f"PayCard:{Month_count}"))
        await bot.send_message(call.message.chat.id, f"Cпособ оплаты:", reply_markup=payInline)

    await bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: 'PayWallet:' in c.data)
async def Pay_month(call: types.CallbackQuery):
    user_dat = await User.GetInfo(call.from_user.id)
    payment_info = await user_dat.PaymentInfo()
    if payment_info is None:
        Month_count=int(str(call.data).split(":")[1])
        await bot.delete_message(call.message.chat.id, call.message.id)
        order = await NewOrder(call.from_user.id, random.randint(1, 10000),Month_count)
        payInline = types.InlineKeyboardMarkup()
        payInline.add(types.InlineKeyboardButton(e.emojize(":purse: Pay via Wallet"),url=order.pay_link))
        price = await get_amount(Month_count);
        await bot.send_message(call.message.chat.id,f"Оплата VPN на {Month_count} мес. {price} руб.", reply_markup=payInline)
        await PyWallet(order, 60, call, Month_count)
    await bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: 'PayCard:' in c.data)
async def Pay_month(call: types.CallbackQuery):
    user_dat = await User.GetInfo(call.from_user.id)
    payment_info = await user_dat.PaymentInfo()
    if payment_info is None:
        Month_count=int(str(call.data).split(":")[1])
        await bot.delete_message(call.message.chat.id, call.message.id)
        price = await get_amount(Month_count);
        bill = await bot.send_invoice(call.message.chat.id, f"Оплата VPN", f"VPN на {str(Month_count)} мес.", call.data,
                                      currency="RUB", prices=[types.LabeledPrice(f"VPN на {str(Month_count)} мес.", price * 100)],
                                      provider_token=CONFIG["tg_shop_token"])
    await bot.answer_callback_query(call.id)

async def AddTimeToUser(tgid,timetoadd):
    userdat = await User.GetInfo(tgid)
    db = await aiosqlite.connect(DBCONNECT)
    db.row_factory = sqlite3.Row
    if int(userdat.subscription) < int(time.time()):
        passdat = int(time.time()) + timetoadd
        await db.execute(f"Update userss set subscription = ?, banned=false, notion_oneday=false where tgid=?",(str(int(time.time()) + timetoadd), userdat.tgid))
        check = subprocess.call(f'./addusertovpn.sh {str(userdat.tgid)}', shell=True)
        await bot.send_message(userdat.tgid, e.emojize( 'Данны для входа были обновлены, скопируйте новый ключ авторизации через раздел "Подключить VPN :gear:"'))
    else:
        passdat = int(userdat.subscription) + timetoadd
        await db.execute(f"Update userss set subscription = ?, notion_oneday=false where tgid=?",(str(int(userdat.subscription)+timetoadd), userdat.tgid))
    await db.commit()
    await db.close()
    Butt_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    dateto = datetime.utcfromtimestamp(int(passdat)+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')
    timenow = int(time.time())
    if int(passdat) >= timenow:
        Butt_main.add(
            types.KeyboardButton(e.emojize(f":green_circle: До: {dateto} МСК:green_circle:")))

    Butt_main.add(types.KeyboardButton(e.emojize(f"Продлить :money_bag:")),
                  types.KeyboardButton(e.emojize(f"Подключить VPN :gear:")))

@bot.callback_query_handler(func=lambda c: 'DELETE:' in c.data or 'DELETYES:' in c.data or 'DELETNO:' in c.data)
async def DeleteUserYesOrNo(call: types.CallbackQuery):
    idstatic = str(call.data).split(":")[1]
    db = await aiosqlite.connect(DBCONNECT)
    c = await db.execute(f"select * from static_profiles where id=?",(int(idstatic),))
    staticuser = await c.fetchone()
    await c.close()
    await db.close()
    if staticuser[0]!=int(idstatic):
        await bot.answer_callback_query(call.id, "Пользователь уже удален!")
        return

    if "DELETE:" in call.data:
        Butt_delete_account = types.InlineKeyboardMarkup()
        Butt_delete_account.add(types.InlineKeyboardButton(e.emojize("Удалить!"),callback_data=f'DELETYES:{str(staticuser[0])}'),types.InlineKeyboardButton(e.emojize("Нет"),callback_data=f'DELETNO:{str(staticuser[0])}'))
        await bot.edit_message_reply_markup(call.message.chat.id,call.message.id,reply_markup=Butt_delete_account)
        await bot.answer_callback_query(call.id)
        return
    if "DELETYES:" in call.data:
        db = await aiosqlite.connect(DBCONNECT)
        await db.execute(f"delete from static_profiles where id=?", (int(idstatic),))
        await db.commit()
        await db.close()
        await bot.delete_message(call.message.chat.id,call.message.id)
        url = staticuser[2]
        namekey = staticuser[1]
        DeleteConfig(namekey,url)
        await bot.send_message(call.message.chat.id,"Пользователь удален!")
        return
    if "DELETNO:" in call.data:
        Butt_delete_account = types.InlineKeyboardMarkup()
        Butt_delete_account.add(types.InlineKeyboardButton(e.emojize("Удалить пользователя :cross_mark:"),
                                                           callback_data=f'DELETE:{str(idstatic)}'))
        await bot.edit_message_reply_markup(call.message.chat.id,call.message.id,reply_markup=Butt_delete_account)
        await bot.answer_callback_query(call.id)
        return


@bot.pre_checkout_query_handler(func=lambda query: True)
async def checkout(pre_checkout_query):
    #(pre_checkout_query)
    month=int(str(pre_checkout_query.invoice_payload).split(":")[1])
    price = await get_amount(month);
    if 100*price != pre_checkout_query.total_amount:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                            error_message="Нельзя купить по старой цене!")
        await bot.send_message(pre_checkout_query.from_user.id,"<b>Цена изменилась! Нельзя приобрести по старой цене!</b>",parse_mode="HTML")
    else:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                            error_message="Оплата не прошла, попробуйте еще раз!")

async def addTimePament(m,month):
    await AddTimeToUser(m.from_user.id, month * 30 * 24 * 60 * 60)
    user_dat = await User.GetInfo(m.from_user.id)
    await bot.send_message(m.from_user.id, texts_for_bot["success_pay_message"],
                           reply_markup=await buttons.main_buttons(user_dat), parse_mode="HTML")
@bot.message_handler(content_types=['successful_payment'])
async def got_payment(m):
    payment:types.SuccessfulPayment = m.successful_payment
    month=int(str(payment.invoice_payload).split(":")[1])
    await addTimePament(m,month)


bot.add_custom_filter(asyncio_filters.StateFilter(bot))

#Удаляем конфиг
def DeleteConfig(id,url):
    db = sqlite3.connect(DBCONNECT)
    db.row_factory = sqlite3.Row
    c = db.execute(f"SELECT * FROM servers where url = ?", (url,))
    cert_sha256 = c.fetchall()
    cert_sha256 = cert_sha256[0][5]
    client = OutlineVPN(api_url=url, cert_sha256=cert_sha256)

    try:
        for key in client.get_keys():
            if key.name == str(id):
                key_id = key.key_id
                client.delete_key(key_id)
                if len(client.get_keys()) <= CONFIG['max_people_server']:
                    db.execute(f"Update servers set space = ? where url = ?", (True, url))
                    db.commit()
        c.close()
        db.close()
    except:
        c.close()
        db.close()
        return





def checkTime():
    while True:
        try:
            time.sleep(15)
            db = sqlite3.connect(DBCONNECT)
            db.row_factory = sqlite3.Row
            c = db.execute(f"SELECT * FROM userss")
            log = c.fetchall()
            c.close()
            db.close()
            for i in log:
                time_now=int(time.time())
                remained_time=int(i[2])-time_now
                if remained_time<=0 and i[3]==False:
                    db = sqlite3.connect(DBCONNECT)
                    db.execute(f"UPDATE userss SET banned=true where tgid=?",(i[1],))
                    db.execute(f"Update userss set server = ? where tgid = ?", (None, i[1]))
                    db.commit()
                    db.close()
                    if i[7] != None:
                        DeleteConfig(i[1],i[7])
                    dateto = datetime.utcfromtimestamp(int(i[2])+CONFIG['UTC_time']*3600).strftime('%d.%m.%Y %H:%M')
                    Butt_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    Butt_main.add(
                            types.KeyboardButton(e.emojize(f":red_circle: Закончилась: {dateto} МСК:red_circle:")))
                    Butt_main.add(types.KeyboardButton(e.emojize(f"Продлить :money_bag:")),
                                  types.KeyboardButton(e.emojize(f"Подключить VPN :gear:")))
                    Butt_main.add(types.KeyboardButton(e.emojize(f"Узнать о VPN :thinking_face:")))
                    BotChecking = TeleBot(BOTAPIKEY)
                    BotChecking.send_message(i['tgid'],texts_for_bot["ended_sub_message"],parse_mode="HTML")

                if remained_time<=86400 and i[4]==False:
                    db = sqlite3.connect(DBCONNECT)
                    db.execute(f"UPDATE userss SET notion_oneday=true where tgid=?", (i[1],))
                    db.commit()
                    db.close()
                    BotChecking = TeleBot(BOTAPIKEY)
                    try:
                        BotChecking.send_message(i['tgid'],texts_for_bot["alert_to_renew_sub"],parse_mode="HTML")
                    except:
                        continue

        except Exception as err:
            print(err)
            pass


if __name__ == '__main__':

    threadcheckTime = threading.Thread(target=checkTime, name="checkTime1")
    threadcheckTime.start()

    asyncio.run(bot.polling(non_stop=True, interval=0, request_timeout=60, timeout=60))


