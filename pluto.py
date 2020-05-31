import ftplib
import urllib.request
from urllib.request import Request, urlopen
from io import BytesIO
from PIL import Image
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ParseMode
import logging
import datetime
from lxml import html
import requests
from bs4 import BeautifulSoup
import json
import sys
import os
from urllib import parse
import psycopg2
from datetime import datetime, timezone
import time

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

parse.uses_netloc.append("postgres")
url = parse.urlparse(os.environ["DATABASE_URL"])

conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

dt = datetime.now()
    
#cur = conn.cursor()
# create table one by one
#cur.execute("DROP TABLE Artstation")
#cur.execute("CREATE TABLE Artstation(Id SERIAL PRIMARY KEY, Chatname VARCHAR(30), Artistname VARCHAR(30), Lastdate TIMESTAMP)")

#FOR ADD SOMETHING NEW
#SQL = "INSERT INTO Artstation (Chatname, Artistname, Lastdate) VALUES (%s, %s, %s);" # Note: no quotes
#data = ("Some", "Some", dt)
#cur.execute(SQL, data) # Note: no % operator

#FOR SELECT ALL
#cur.execute("SELECT * FROM Artstation")
#for record in cur:
#    print(record)

#FOR SELECT ONE USE THIS
#SQL2 = "SELECT * FROM Artstation WHERE Chatname = %s AND Artistname = %s;"
#data3 = ("Some", "Some")
#cur.execute(SQL2, data3)
#if cur.rowcount > 0:
#    print("Found!")
#else:
#    print("Not found!")

#FOR DELETE SOMETHING
#SQL2 = "DELETE FROM Artstation WHERE Chatname = %s;"
#data3 = ("Some",)
#cur.execute(SQL2, data3)

#FOR UPDATE SOMETHING
#dt2 = datetime(2015, 2, 1, 15, 16, 17, 345, tzinfo=timezone.utc)
#SQL2 = "UPDATE Artstation SET Lastdate = %s WHERE Artistname = %s;"
#data3 = (dt2, "gawel")
#cur.execute(SQL2, data3)

# close communication with the PostgreSQL database server
#cur.close()
# commit the changes
#conn.commit()


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    chat_id = update.message.chat_id
    update.message.reply_text('Start getting last photo from space...!')
    url = get_image()
    bot.send_photo(chat_id = chat_id, photo=open(url, 'rb'))


def addSub(bot, update):
    cur = conn.cursor()
    chat_id = update.message.chat_id
    messageText = update.message.text.replace("/addsub", "").strip()
    if not messageText:
        update.message.reply_text('Please, add artist nickname!')
    else:
        #print(messageText)
        non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)
        try:
            url = 'https://www.artstation.com/users/' + messageText + '/projects.rss'
            print(url)
            req_headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
            request = Request(url, headers=req_headers)
            r = urlopen(request)
            jsonArray = json.loads(r.read().decode("utf-8").translate(non_bmp_map))
            jsonData = jsonArray['data']

            if len(jsonData):
                partsOfUrl = jsonData[0]['cover']['small_square_url'].split("/")
                imageUrl = partsOfUrl[0] + "/" + partsOfUrl[1] + "/" + partsOfUrl[2] + "/" + partsOfUrl[3] + "/" + partsOfUrl[4] + "/" + partsOfUrl[5] + "/" + partsOfUrl[6] + "/" + partsOfUrl[7] + "/" + partsOfUrl[8] + "/" + partsOfUrl[9] + "/" + "large" + "/" + partsOfUrl[-1]
                publishData = jsonData[0]['published_at']
                publishTime = datetime.strptime(publishData[:19],'%Y-%m-%dT%H:%M:%S')
                SQL = "SELECT * FROM Artstation WHERE Chatname = %s AND Artistname = %s;"
                data = (str(chat_id), messageText)
                cur.execute(SQL, data)
                if cur.rowcount > 0:
                    update.message.reply_text('You already have it')
                else:
                    SQL2 = "INSERT INTO Artstation (Chatname, Artistname, Lastdate) VALUES (%s, %s, %s);" # Note: no quotes
                    data2 = (chat_id, messageText, publishTime)
                    cur.execute(SQL2, data2) # Note: no % operator
                    update.message.reply_text('Added to your list!')
                    bot.send_photo(chat_id=chat_id, photo=imageUrl)

            else:
                update.message.reply_text("I can't take any data from artstation :(")
        except BaseException as error:
            print('An exception occurred in sub: {}'.format(error))
            update.message.reply_text('Some error happen')

        cur.close()
    conn.commit()


def unsub(bot, update):
    try:
        cur = conn.cursor()
        messageText = update.message.text.replace("/unsub", "").strip()
        if not messageText:
            update.message.reply_text('Please, write artist name after command!')
        else:
            chat_id = str(update.message.chat_id)
            cur.execute("SELECT * FROM Artstation")
            deletedCount = 0
            result = cur.fetchall()
            for record in result:
                rec_chat_id = str(record[1])
                artist_name = record[2]
                if (rec_chat_id == chat_id and artist_name == messageText):
                    deletedCount += 1
                    SQL2 = "DELETE FROM Artstation WHERE Chatname = %s AND Artistname = %s;"
                    data3 = (chat_id, artist_name)
                    cur.execute(SQL2, data3)
                    conn.commit()

            if deletedCount != 0:
                update.message.reply_text("You successfully unsubscribed")
            else:
                update.message.reply_text('You are not subscribed to this artist')
                
            cur.close()
        
    except BaseException as error:
        update.message.reply_text("Some error!")
        print('An exception occurred in unsub: {}'.format(error))


def getAllSubs(bot, update):
    try:
        cur = conn.cursor()
        chat_id = str(update.message.chat_id)
        update.message.reply_text('Ok, its your subscriptions:')
        cur.execute("SELECT * FROM Artstation")
        resStringA = []
        result = cur.fetchall()
        for record in result:
            rec_chat_id = str(record[1])
            artist_name = record[2]
            if rec_chat_id == chat_id:
                linkToArtist = '<a href="https://www.artstation.com/' + artist_name + '">' + artist_name + '</a>'
                resStringA.append(linkToArtist)

        if len(resStringA):
            resLen = len(resStringA)
            if (resLen > 50):
                #in other cases not all links will works
                firstHalfA = math.ceil(resLen - resLen / 2)
                secondHalfA = -1 * (resLen - firstHalfA)
                bot.send_message(chat_id=chat_id, text=', '.join(resStringA[:firstHalfA]), parse_mode=ParseMode.HTML)
                bot.send_message(chat_id=chat_id, text=', '.join(resStringA[secondHalfA:]), parse_mode=ParseMode.HTML)
            else:
                bot.send_message(chat_id=chat_id, text=', '.join(resStringA), parse_mode=ParseMode.HTML)
        else:
            update.message.reply_text('Nothing')
            
        cur.close()
    except BaseException as error:
        update.message.reply_text("Some error!")
        print('An exception occurred in sub: {}'.format(error))


def autoArtUpdate(bot):
    cur = conn.cursor()
    cur.execute("SELECT * FROM Artstation")
    result = cur.fetchall()
    for record in result:
        chat_id = record[1]
        artist_name = record[2]
        lastPublishDate = record[3]
        non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)
        try:
            url = 'https://www.artstation.com/users/' + artist_name + '/projects.rss'
            req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'}
            request = Request(url, headers=req_headers)
            r = urlopen(request)
            jsonArray = json.loads(r.read().decode("utf-8").translate(non_bmp_map))
            jsonData = jsonArray['data']

            if len(jsonData):
                partsOfUrl = jsonData[0]['cover']['small_square_url'].split("/")
                imageUrl = partsOfUrl[0] + "/" + partsOfUrl[1] + "/" + partsOfUrl[2] + "/" + partsOfUrl[3] + "/" + partsOfUrl[4] + "/" + partsOfUrl[5] + "/" + partsOfUrl[6] + "/" + partsOfUrl[7] + "/" + partsOfUrl[8] + "/" + partsOfUrl[9] + "/" + "large" + "/" + partsOfUrl[-1]
                #imageUrl = jsonData[0]['cover']['small_square_url'].replace("/small/", "/large/")
                permaLink = jsonData[0]['permalink']
                assetsCount = jsonData[0]['assets_count']
                additionalLink = str(assetsCount) + ' arts, <a href="' + permaLink + '">link</a>'
                publishData = jsonData[0]['published_at']
                currentPublishDate = datetime.strptime(publishData[:19],'%Y-%m-%dT%H:%M:%S')
                if currentPublishDate > lastPublishDate:
                    try:
                        SQL = "UPDATE Artstation SET Lastdate = %s WHERE Artistname = %s;"
                        data = (currentPublishDate, artist_name)
                        cur.execute(SQL, data)
                        conn.commit()
                    except psycopg2.ProgrammingError as error:
                        #bot.send_message(chat_id=chat_id, text='Some error in autoupdate')
                        print('An exception occurred: {}'.format(error))
                        
                    bot.send_message(chat_id=chat_id, text='New art from ' + artist_name + ' (' + additionalLink + ')', parse_mode=ParseMode.HTML)
                    bot.send_photo(chat_id=chat_id, photo=imageUrl)
        except BaseException as error:
            #bot.send_message(chat_id=chat_id, text='Some error in autoupdate')
            print('An exception occurred in autoupdate: {}'.format(error), " for " + artist_name)

    db = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Autoupdate : " + db)
    cur.close()
    conn.commit()


def echo(bot, update):
    update.message.reply_text(update.message.text)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def help(bot, update):
    update.message.reply_text("Hello! You can get photo from space by /start or subcribe to artstation artists by /addsub, /unsub and others commands")


def get_image():
    ftp = ftplib.FTP("ftp.ntsomz.ru")
    ftp.login("electro", "electro")
    ftp.cwd('ELECTRO_L_2')

    now = datetime.now()
    now.year
    data = []
    ftp.dir('-t', data.append)
    newfld = str(now.year)
    #data[0].rsplit(' ',1)[1] #year
    year = newfld
    print(newfld)
    ftp.cwd(newfld)

    data = []
    ftp.dir('-t', data.append)
    newfld = data[0].rsplit(' ',1)[1] #month
    month = newfld
    print(newfld)
    ftp.cwd(newfld)

    data = []
    ftp.dir('-t', data.append)
    newfld = data[0].rsplit(' ',1)[1] #day
    day = newfld
    print(newfld)
    ftp.cwd(newfld)

    data = []
    ftp.dir('-t', data.append)
    newfld = data[0].rsplit(' ',1)[1] #time
    time = newfld
    print(newfld)
    ftp.cwd(newfld)

    data = []
    ftp.dir('-t', data.append)
    sub = time + "_RGB"
    file = ""
    for text in data:
        if sub in text:
            file = text
    print(file.rsplit(' ',1)[1])
    filePath = file.rsplit(' ',1)[1]
    imagePath = "ftp://electro:electro@ftp.ntsomz.ru/ELECTRO_L_2/" + year + "/" + month + "/" + day + "/" + time + "/" + filePath  
    #print(imagePath)
    c = ""
    with urllib.request.urlopen(imagePath) as url:
        c = BytesIO(url.read())
    
    img = Image.open(c)
    img.save("img1.png","PNG")
    return("img1.png")
    #img.show() 


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(os.environ["TG_KEY"])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("addsub", addSub))
    dp.add_handler(CommandHandler("mysubs", getAllSubs))
    dp.add_handler(CommandHandler("unsub", unsub))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    startTime=time.time()
    while True:
        autoArtUpdate(updater.bot)
        time.sleep(60.0 - ((time.time() - startTime) % 60.0))

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
