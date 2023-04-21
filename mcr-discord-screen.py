import nest_asyncio
nest_asyncio.apply()
import asyncio 
import discord 
from discord import Webhook
import aiohttp 
import os
import time
import psutil
import options
import sys

def check_process(names: list):
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() in names:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


async def async_send_screenshot(url, username, imagefile):
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(url, session=session)
        embed = discord.Embed(title="Screenshot from " + username)
        file = discord.File(imagefile, filename="image.png")
        embed.set_image(url="attachment://image.png")
        
        await webhook.send(file=file, embed=embed)
        

def send_screenshot(url, username, imagefile):
    for try_i in range(3):
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(async_send_screenshot(url, username, imagefile))
            loop.close()
            break
        except Exception as Err:
            if try_i == 2:
                raise Err
            time.sleep(2.5)
        

def get_new_screenshots(d: str, maxage: int, ignore: list):
    r = []
    for path in os.scandir(d):
        if path.is_file() and path.name.endswith('.png'):
            f = os.path.join(d, path.name)
            if f in ignore:
                continue
            ct = os.path.getctime(f)
            if (time.time() - ct) < maxage:
                r.append(f)
    return r

        
if __name__ == "__main__":
    whurl = options.chanel_url
    username = os.path.expandvars(options.username)
    screendir = os.path.expandvars(os.path.normpath(options.searchdir))

    if not whurl:
        print('Discord webhook URL is not defined in options.py')
        sys.exit()
        
    print('Screenshots search path:', screendir)
    print('Username in message:', username)
    print('Waiting for screenshots...')

    processed = []
    last_process_check = time.time()
    proc_not_found = 0
    age = options.max_file_age_first
    while True:
        dirmodtime = os.path.getmtime(screendir)
        if time.time() - dirmodtime < age:
            for f in get_new_screenshots(screendir, age, processed):
                try:
                    print('Found:', f)
                    processed.append(f)
                    send_screenshot(whurl, username, f)
                    print('Sent to Discord')                        
                    if options.remove_screenshot_file:
                        os.remove(f)
                        print('File removed')
                except Exception as Err:
                    print('Error:', Err)
        age = options.max_file_age
        for i in range(5):
            time.sleep(1)
        if time.time() - last_process_check > 60:
            last_process_check = time.time()
            processnames = ['javaw.exe', 'java.exe']
            isrun = check_process(processnames)
            if isrun:
                proc_not_found = 0
            else:
                names = ' or '.join(processnames)
                print(f"Process {names} is not run")
                proc_not_found = proc_not_found + 1
                if proc_not_found > 1:
                    print(f"Finish waiting for screenshot because {names} is not run {proc_not_found} minutes")
                    break