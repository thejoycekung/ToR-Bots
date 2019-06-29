FROM python:3.6.5-slim-jessie
RUN mkdir /charlie
WORKDIR /charlie
RUN python3 -m pip install -U pip
ADD requirements.txt /charlie/
RUN python3 -m pip install -r requirements.txt
ADD . /charlie/
CMD python3 charlie_the_collector.py
