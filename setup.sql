CREATE ROLE torstats_admin;
GRANT ALL PRIVILEGES ON DATABASE torstats TO torstats_admin;

CONNECT torstats
CREATE EXTENSION citext;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO torstats_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO torstats_admin;

CREATE USER "${user_name}" WITH PASSWORD '${user_password}' IN GROUP torstats_admin

CREATE TABLE IF NOT EXISTS redditor (
    name citext
        PRIMARY KEY,
    valid boolean
        NOT NULL
        DEFAULT TRUE,
);

CREATE TABLE IF NOT EXISTS discord_user (
    reddit_account citext
        -- purposefully nullable.
        REFERENCES redditor(name),
    name citext,
    discord_id bigint
        PRIMARY KEY,
    verified boolean
        NOT NULL
        DEFAULT FALSE
);

CREATE ENUM IF NOT EXISTS direction ('forwards', 'backwards');

CREATE TABLE IF NOT EXISTS search (
    name citext
        REFERENCES redditor(name),
    start_comment text,
    end_comment text,
    counted_comments integer
        NOT NULL
        DEFAULT 0,
    direction direction
        NOT NULL
        DEFAULT 'backwards'::direction
);

CREATE VIEW transcribers AS (
    SELECT
        redditors.name
        (
            SELECT
                gamma
            FROM new_gammas
            WHERE name=redditors.name
            ORDER BY time DESC
            LIMIT 1
        ) official_gamma_count,
        (
            SELECT
                comment
            FROM comments
            WHERE name = redditors.name AND comments.comment_type='reference'
            ORDER BY time DESC
            LIMIT 1
        ) reference_comment,
        discord_id,
        valid,
    FROM redditors
    LEFT OUTER JOIN discord_user ON redditors.name = discord_user.name
);

CREATE TABLE IF NOT EXISTS new_gammas (
    transcriber citext
        REFERENCES redditor(name),
    gamma integer
        NOT NULL,
    "time" timestamp with time zone
        NOT NULL,
    PRIMARY KEY (transcriber, gamma)
);

CREATE VIEW gammas AS (
    SELECT
        transcriber,
        LAG(gamma, 1, 0) OVER (PARTITION BY transcriber ORDER BY time ASC) AS old_gamma,
        gamma AS new_gamma,
        time
    FROM new_gammas
);

CREATE ENUM IF NOT EXISTS comment_type('reference', 'transcription', 'comment');

CREATE TABLE IF NOT EXISTS comments (
    comment_id text PRIMARY KEY,
    comment_type comment_type
        NOT NULL
        DEFAULT 'comment'::comment_type,
    author citext REFERENCES redditor(name),
    content text
        NOT NULL,
    subreddit text
        NOT NULL,
    found timestamp with time zone
        NOT NULL,
    error boolean
        NOT NULL
        DEFAULT FALSE,
    permalink text
        NOT NULL,
    created timestamp with time zone
);

CREATE TABLE IF NOT EXISTS transcription_stats (
    comment_id text REFERENCES comments(comment_id),
    replies integer
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
    from_archive boolean
        NOT NULL
        DEFAULT FALSE
);

CREATE VIEW transcriptions AS (
    SELECT
        transcription_stats.*,
        comments.author AS transcriber,
        comments.content,
        comments.subreddit,
        comments.found,
        comments.error,
        comments.permalink,
        comments.created
    FROM transcription_stats
    INNER JOIN comments ON transcription_stats.comment_id = comments.comment_id
);
