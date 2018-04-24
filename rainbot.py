# coding: utf-8

import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram
import redis
from weather import Weather
from timezonefinder import TimezoneFinder
from dateutil import parser
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.redis import RedisJobStore


config = {

    'bot_token': 'T-O-K-E-N',  # str
    'logfile': None,  # str or None
    'db_type': 'redis',  # str
    'redis': {
        'db_index': 0,  # int
        'prefix': 'RainBot',  # str
        'host': 'localhost',  # str
    },
    # Statuses for alerts (rain is 0...12). Codes: https://developer.yahoo.com/weather/documentation.html
    'alert_statuses': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '17', '35', '37', '38', '39', '40', '45', '47'],
    'anyway_alert': False,  # Send notifications despite the status
}


# Enable logging
logging.basicConfig(filename=config['logfile'], format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enable scheduling
scheduler = BackgroundScheduler(
    jobstores={'default': RedisJobStore(db=config['redis']['db_index'])},
    jobs_key='rainbot.jobs',
    run_times_key='rainbot.run_times')
scheduler.start()


class RainBot:

    bot = telegram.Bot(token=config['bot_token'])

    @staticmethod
    def factory(db=config['db_type']):
        if db == 'redis':
            return RedisModel()
        else:
            logging.exception('Wrong DB type')

    # /start command
    def start(self, bot, update):
        update.message.reply_text('Give me your location! And set the time to receive notifications about upcoming rain')

    # /forecast command
    def force_forecast(self, bot, update):
        geo = self.get_user_geo(bot, update)
        if geo is not None:
            lat, lng = geo[0], geo[1]
            today = self.get_forecast_condition_code(lat, lng)
            update.message.reply_text('{0}\r\nMax Temp. {1}°C'.format(today.text, today.high))
        else:
            update.message.reply_text('First give me your location..')

    # /stop command
    @staticmethod
    def stop_forecast(bot, update):
        try:
            scheduler.remove_job(str(update.message.chat_id))
        except:
            logging.exception('stop_forecast exception')
            update.message.reply_text('Something wrong:(')
        else:
            update.message.reply_text('Okay, give me new alert time to resume..')

    # /reflection command
    def reflection(self, bot, update):
        update.message.reply_text('Your location: {}'.format(str(self.get_user_geo(bot, update))))

    @classmethod
    def send_alert(cls, chat_id, lat, lng):
        fc = cls.get_forecast_condition_code(lat, lng)
        rain = cls.is_rainy(fc)
        if rain or config['anyway_alert']:
            try:
                cls.bot.sendMessage(int(chat_id), text='{0}\r\nMax Temp. {1}°C'.format(fc.text, fc.high))
            except telegram.error.Unauthorized:
                scheduler.remove_job(str(chat_id))

    # Returns a forecast by Yahoo Weather API
    @staticmethod
    def get_forecast_condition_code(lat, lng):
        lat = float(lat)
        lng = float(lng)
        w = Weather()
        try:
            lookup = w.lookup_by_latlng(lat, lng)
            return lookup.forecast[0]
        except:
            return None

    @staticmethod
    def is_rainy(forecast):
        if forecast.code in config['alert_statuses']:
            return True
        return False

    def time_scheduler(self, bot, update):
        geo = self.get_user_geo(bot, update)
        if geo is not None:
            lat, lng = geo[0], geo[1]
            job_time = TimeHelper.parse(update.message.text.strip())
            if job_time is not None:
                tz_name = TimeHelper.time_zone_name(lng, lat)
                if tz_name is not None:
                    scheduler.add_job(
                        self.send_alert,
                        kwargs={'chat_id': int(update.message.chat_id), 'lat': lat, 'lng': lng},
                        trigger='cron',
                        hour=job_time.hour,
                        minute=job_time.minute,
                        timezone=tz_name,
                        id=str(update.message.chat_id),
                        replace_existing=True)
                    update.message.reply_text('Alert time: {0}, {1}'.format(job_time.strftime('%X'), tz_name))
                else:
                    update.message.reply_text('Something wrong:(')
        else:
            update.message.reply_text('First give me your location..')

    def save_location(self):
        pass

    def get_user_geo(self):
        pass


class RedisModel(RainBot):

    """
    Key format: prefix:geo:chat_id -> str(latitude,longitude)
    """

    db = redis.StrictRedis(host=config['redis']['host'], decode_responses=True, db=config['redis']['db_index'])
    prefix = config['redis']['prefix']
    
    def save_location(self, bot, update):
        key = '{0}:geo:{1}'.format(self.prefix, update.message.chat_id)
        val = '{0},{1}'.format(update.message.location['latitude'], update.message.location['longitude'])
        try:
            self.db.set(key, val)
            update.message.reply_text('+')
        except:
            logging.exception('save_location exception')
            update.message.reply_text('Something wrong:(')

    def get_user_geo(self, bot, update):
        try:
            key = '{0}:geo:{1}'.format(self.prefix, update.message.chat_id)
            geo = self.db.get(key)
            if geo is not None:
                geo = geo.split(',')
                return geo[0], geo[1]
            return None
        except:
            logging.exception('get_user_geo exception')


class TimeHelper:

    @staticmethod
    def parse(time: str):
        try:
            dt = parser.parse(time)
        except:
            dt = None
        return dt

    @staticmethod
    def time_zone_name(lng: float, lat: float):
        lng = float(lng)
        lat = float(lat)
        tf = TimezoneFinder()
        try:
            tz_name = tf.timezone_at(lng=lng, lat=lat)
            if tz_name is None:
                tz_name = tf.closest_timezone_at(lng=lng, lat=lat)
            return tz_name
        except:
            logging.exception('get_timezone exception')


def main():

    updater = Updater(config['bot_token'])
    dp = updater.dispatcher
    rainbot = RainBot.factory()
    
    dp.add_handler(CommandHandler("start", rainbot.start))
    dp.add_handler(CommandHandler("stop", rainbot.stop_forecast))
    dp.add_handler(CommandHandler("forecast", rainbot.force_forecast))
    dp.add_handler(CommandHandler("reflection", rainbot.reflection))
    dp.add_handler(MessageHandler(Filters.location, rainbot.save_location))
    dp.add_handler(MessageHandler(Filters.text, rainbot.time_scheduler))

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
