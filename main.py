import logging
import tempfile

from aiogram import Bot, Dispatcher, executor
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputFile
from bs4 import BeautifulSoup
import requests
from io import BytesIO
from moviepy.editor import *
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

bot = Bot(os.getenv('BOT_TOKEN'), parse_mode='HTML')
dp = Dispatcher(bot)

url = 'https://getyarn.io'

@dp.message_handler(commands=['start', 'help'])
async def react_to_main_commands(ctx: Message):
    print(ctx.from_user)
    await ctx.answer('🎙️ RU:\nВ этом боте вы можете искать различные фразы из фильмов, сериалов и мультфильмов. Введите нужную фразу и скачайте ее бесплатно\n\n🎙️ EN:\nIn this bot you can search for various phrases from movies, TV series and cartoons. Enter the desired phrase and download it for free:')


def generate_searched(btns: list, current_page=0, buttons_per_page=10):
    inline_buttons = btns

    pages = [inline_buttons[i:i + buttons_per_page] for i in range(0, len(inline_buttons), buttons_per_page)]
    current_page = current_page % len(pages)
    markup = InlineKeyboardMarkup(row_width=1).add(*pages[current_page])

    prev_btn = 'N'
    next_btn = 'N'
    if len(pages) > 1:
        if current_page > 0:
            prev_btn = InlineKeyboardButton('◀', callback_data='prev_page')
        if current_page < len(pages) - 1:
            next_btn = (InlineKeyboardButton('▶', callback_data='next_page'))

    # if next_btn != 'N' and prev_btn != 'N':
    #     markup.add(prev_btn, next_btn)
    # elif next_btn != 'N':
    #     markup.add(next_btn)
    # elif prev_btn != 'N':
    #     markup.add(prev_btn)

    return markup

def generate_audio_get(data):
    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton(text='🔉 GET AUDIO', callback_data=f'd_{data}')
    markup.add(btn)
    return markup

@dp.message_handler(content_types=['text'])
async def answer_to_messages(ctx: Message):
    trash = await ctx.reply('🔄️ Searching...')
    query = ctx.text.replace(' ', '%20')
    html = requests.get(f'{url}/yarn-find?text={query}').text
    soup = BeautifulSoup(html, 'html.parser')
    info = soup.find('div', class_='pure-gx')
    status = ''
    try:
        status = info.find('div', class_='tac w100').find('h3').get_text(strip=True)
    except:
        print('')

    if status == 'No clips found': return await ctx.answer('No clips found')
    voices = info.find_all('div', class_='pure-u-1-2 pure-u-md-1-3 pure-u-lg-1-4 pure-u-xl-1-4')
    buttons = []
    for voice in voices:
        voicelinkdiv = voice.find_all('a')[1]
        voice_link = voicelinkdiv.get('href')
        text = voicelinkdiv.find('div', class_='transcript db bg-w fwb p05 tal').get_text(strip=True).capitalize()
        if text[0] == '[': continue
        buttons.append(InlineKeyboardButton(text=text, callback_data=f's_{voice_link}'))

    await ctx.answer(f'Here is what I was able to find on request:\n<i>{ctx.text}</i>', reply_markup=generate_searched(buttons, 0, 10))
    await bot.delete_message(ctx.chat.id, trash.message_id)



@dp.callback_query_handler(lambda call: 's' in call.data)
async def call_hand(call: CallbackQuery):
    try:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        data = call.data.split('_')[1]
        qurl = url + data
        html = requests.get(qurl).text
        soup = BeautifulSoup(html, 'html.parser')
        videodiv = soup.find('div', class_='video-js bg-b fcw p0 usn vam p')
        video = videodiv.find('video').find('source').get('src')
        vido_title = soup.find('div', class_='fs12 tac fwb p05').get_text(strip=True).capitalize()
        await bot.send_video(call.message.chat.id, video, caption=vido_title,
                             reply_markup=generate_audio_get(data=video.replace("https://y.yarn.co", "")))
        await call.answer()
    except Exception as e:
        print(e)

async def video_to_audio_buffer(video_url, user_id, title):
    try:
        response = requests.get(video_url)
        with open(f"./videos/{user_id}.mp4", 'wb') as f:
            f.write(response.content)

        video_path = f'./videos/{user_id}.mp4'

        # Load the video clip
        video_clip = VideoFileClip(video_path)

        # Extract the audio from the video
        audio_clip = video_clip.audio

        # Save the audio to a file (optional)
        audio_clip.write_audiofile(f'./audios/{user_id}.mp3')

        # Close the clips
        audio_clip.close()
        video_clip.close()
        os.remove(f'./videos/{user_id}.mp4')
        await bot.send_audio(user_id, InputFile(f'./audios/{user_id}.mp3', filename=title))
        os.remove(f'./audios/{user_id}.mp3')
    except Exception as e:
        print(e)

@dp.callback_query_handler(lambda call: 'd' in call.data)
async def call_hand(call: CallbackQuery):
    try:
        await bot.edit_message_caption(call.message.chat.id, call.message.message_id, caption=f'{call.message.caption}\n\nAudio ⬇')
        data = call.data.split('_')[1]
        qurl = 'https://y.yarn.co' + data
        asyncio.create_task(video_to_audio_buffer(qurl, call.from_user.id, call.message.caption))
        await call.answer()
    except Exception as e:
        print(e)

executor.start_polling(dp, skip_updates=True)