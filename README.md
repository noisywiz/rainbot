# Rainbot
The telegram bot notifies you if you need to take an umbrella today:) Tell him your coordinates and time for notifications.

The time zone is fast calculated offline by the user's geolocation thanks to [timezonefinder](https://github.com/MrMinimal64/timezonefinder). Scheduling jobs (sending alerts) is by [apscheduler](https://github.com/agronholm/apscheduler) in Redis.

## Commands
- /start
- /forecast - today forecast
- /stop - stop alerts (removes a job from scheduler)

## Requirements:
- Python3
- redis-server

### Python packages:
- [redis](https://github.com/andymccurdy/redis-py)
- [weather-api](https://github.com/AnthonyBloomer/weather-api)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [timezonefinder](https://github.com/MrMinimal64/timezonefinder)
- [apscheduler](https://github.com/agronholm/apscheduler)
- [python-dateutil](https://github.com/dateutil/dateutil/)

## Example
![rainbot imgage](https://github.com/noisywiz/rainbot/blob/master/image.png)
