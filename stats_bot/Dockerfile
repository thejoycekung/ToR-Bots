FROM python:3.6.5-slim
RUN mkdir /stats_bot/
WORKDIR /stats_bot
RUN python3 -m pip install -U pip
ADD requirements.txt /stats_bot/
RUN python3 -m pip install -r requirements.txt
ADD . /stats_bot/
RUN chmod +x ./run_stats_bot.sh
CMD cd .. && python3 -u -m stats_bot.stats_bot
