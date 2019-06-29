#!/usr/bin/env bash
while true; do
	python3 -u -m stats_bot.stats_bot
	echo Bot died!
	echo Restarting in 5 Seconds...
	python3 -u stats_bot.message_me StatsBot offline
	sleep 5
done
