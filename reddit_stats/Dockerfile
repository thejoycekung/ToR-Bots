FROM python:3.6.5-slim
RUN mkdir /redditstats
WORKDIR /redditstats
RUN python3 -m pip install -U pip
ADD requirements.txt /redditstats/
RUN python3 -m pip install --user -r requirements.txt
ADD . /redditstats/
CMD python3 -u reddit_stats.py
