import os
import time
import psutil
import options
import sys
import requests
import json
import tempfile
from PIL import Image
import logging


def check_process(names: list):
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() in names:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

        
def get_webhook_json(author_data: dict, image_name: str):
    a = {"name": str(author_data['name'])}
    if ('icon_url' in author_data) and (author_data['icon_url'] != ''):
        a['icon_url'] = str(author_data['icon_url'])
    e = {"author": a,
         "image": {"url": f"attachment://{image_name}"}
    }
    if ('color' in author_data) and (author_data['color'] != 0):
        e['color'] = int(author_data['color'])
    return {"embeds": [e]}


def convert_image(pngfile: str):
    img_png = Image.open(pngfile)
    rgb_image = img_png.convert('RGB')
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
        rgb_image.save(tf.name)
        return tf.name


def send_screenshot(url: str, imagefile: str, author_data: dict):
    jpgfile = convert_image(imagefile)
    try:
        j = get_webhook_json(author_data, 'image.jpg')
        with open(jpgfile, 'rb') as f:
            file = {'file': ('image.jpg', f, 'image/jpg', {'Expires': '0'})}
            r = requests.post(url, files=file, data={"payload_json": json.dumps(j)})
            r.raise_for_status()
            return r.content
    finally:
        os.remove(jpgfile)


def attempts(count: int, action, fail_action):
    for i in range(count):
        try:
            return action()
            break
        except:
            if i == count - 1:
                raise
            fail_action()
   

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
    screendir = os.path.expandvars(os.path.normpath(options.searchdir))
    author = options.author
    author['name'] = os.path.expandvars(author['name'])

    if not whurl:
        print('Discord webhook URL is not defined in options.py')
        sys.exit()
        
    if not os.path.exists(screendir):
        print('Screenshots search path not found:', screendir)
        sys.exit()
        
    print('Screenshots search path:', screendir)
    print('Username in message:', author['name'])
    
    if options.use_logging:
        logfile = __file__ + '.log'
        logging.basicConfig(level=logging.INFO, filename=logfile,filemode="w",
                            format="%(asctime)s %(levelname)s %(message)s")
        print('Use logging:', logfile)
    
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
                    r = attempts(3, lambda: send_screenshot(whurl, f, author), lambda: time.sleep(2.5))
                    if options.use_logging:
                        logging.info('Image sent: ' + str(r))
                    print('Sent to Discord')                        
                    if options.remove_screenshot_file:
                        os.remove(f)
                        print('File removed')
                except Exception as Err:
                    print('Error:', Err)
                    if options.use_logging:
                        logging.error('Send image error: ' + str(Err))
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
