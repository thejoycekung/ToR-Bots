#bin/sh

# Install for citext
apt-get update && apt-get install -y postgresql-contrib

psql -U postgres -d torstats --command "CREATE EXTENSION citext;"

echo "SELECT 'CREATE DATABASE torstats' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'torstats')\gexec" | psql -U postgres

psql -U postgres --command "CREATE ROLE torstats_admin;"
psql -U postgres --command "GRANT ALL PRIVILEGES ON DATABASE torstats TO torstats_admin;"
psql -U postgres -d torstats --command "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO torstats_admin;"
psql -U postgres -d torstats --command "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO torstats_admin;"

psql -U postgres --command "CREATE USER \"${user_name}\" WITH PASSWORD '${user_password}' IN GROUP torstats_admin"

psql -U postgres -d torstats --command "CREATE TABLE IF NOT EXISTS transcribers (
    name citext
        PRIMARY KEY,
    discord_id bigint,
    official_gamma_count integer,
    start_comment text,
    end_comment text,
    reference_comment text,
    valid boolean
        NOT NULL
        DEFAULT TRUE,
    counted_comments integer
        NOT NULL
        DEFAULT 0,
    forwards boolean
        NOT NULL
        DEFAULT FALSE
);"

psql -U postgres -d torstats --command "CREATE TABLE IF NOT EXISTS new_gammas (
    transcriber citext
        REFERENCES transcribers(name),
    gamma integer
        NOT NULL,
    \"time\" timestamp with time zone
        NOT NULL,
    PRIMARY KEY (transcriber, gamma)
);"

# psql -U postgres -d torstats --command "CREATE FUNCTION update_official_gamma ()
# RETURNS trigger
# LANGUAGE plpgsql
# SECURITY DEFINER
# AS $BODY$
# BEGIN
#     UPDATE
#         transcribers
#     SET official_gamma_count = (
#         SELECT
#             official_gamma_count
#         FROM transcribers
#         WHERE name = NEW.transcriber LIMIT 1
#     )
#     WHERE name = NEW.transcriber
#     ORDER BY time;

#     RETURN NEW
# END
# $BODY$;
# "

# psql -U postgres -d torstats --command "CREATE TRIGGER new_gamma AFTER INSERT OR UPDATE OF gamma OR DELETE OR TRUNCATE
# ON transcribers
# FOR EACH STATEMENT
# EXECUTE PROCEDUTE update_official_gamma(transcriber.name);
# "

psql -U postgres -d torstats --command "CREATE VIEW gammas AS (
    SELECT
        transcriber,
        LAG(gamma, 1, 0) OVER (PARTITION BY transcriber ORDER BY time ASC) AS old_gamma,
        gamma AS new_gamma,
        time
    FROM new_gammas
);"

psql -U postgres -d torstats --command "CREATE TABLE IF NOT EXISTS transcriptions (
    comment_id text PRIMARY KEY,
    transcriber citext REFERENCES transcribers(name),
    content text
        NOT NULL,
    subreddit text
        NOT NULL,
    found timestamp with time zone
        NOT NULL,
    comment_count integer
        NOT NULL
        DEFAULT 0,
    upvotes integer
        NOT NULL
        DEFAULT 0,
    last_checked timestamp with time zone,
    good_bot integer
        NOT NULL
        DEFAULT 0,
    bad_bot integer
        NOT NULL
        DEFAULT 0,
    good_human integer
        NOT NULL
        DEFAULT 0,
    bad_human integer
        NOT NULL
        DEFAULT 0,
    error boolean
        NOT NULL
        DEFAULT FALSE,
    from_archive boolean
        NOT NULL
        DEFAULT FALSE,
    permalink text
        NOT NULL,
    created timestamp with time zone
);"
