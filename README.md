# ToR-Bots v3.0.0

The program's name "ToR Bots" comes from its utility being targeted towards the international charity Transcribers of Reddit which is commonly shortened to ToR. The charity is aimed towards image transcriptions for the visually impaired. This program is split into three main components as follows:

Stats Bot is the public facing portion, the program appears as a bot for Discord and sends messages providing utility such as the number of replies saying `good bot`/`good human` etc. Statsbot also tries to announce if someone gets new flair on the ToR subreddit, which typically signifies that someone has finished a transcription.

Reddit Stats looks through every registered member's history and find transcriptions and then adds them to the Postgres database if it finds any. It does not process any statistics on transcriptions it finds.

Charlie the Collector is a task loop that reads through every transcription it has that is younger than two days and find that comments statistics that StatsBot outputs such as the comment's score, reply count, and stores comment information.

To run the program:

- Create a server for postgres and run `setup_postgres` on it.
- Rename the `secrets/passwords_and_tokens.py.example` to `passwords_and_tokens.py`, fill in the credentials, and copy it into the `stats_bot`, `reddit_stats`, and `charlie` folders.
- Run the docker containers with with `docker-compose up`
  - if any changes were made add the `--build` flag to build the images.
  - if you want to detach from the logs use `ctrl-z` or specify the `--detach`(`-d`) flag.
