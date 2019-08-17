CREATE ENUM IF NOT EXISTS direction ('forwards', 'backwards');
CREATE ENUM IF NOT EXISTS comment_type('reference', 'transcription', 'comment');

ALTER TABLE new_gammas
    DROP CONSTRAINT new_gammas_fkey;

ALTER TABLE transcriptions RENAME to transcription_stats;
COPY TABLE transcription_stats comments;

ALTER TABLE transcription_stats
    DROP COLUMN transcriber
    DROP COLUMN content
    DROP COLUMN subreddit
    DROP COLUMN found
    DROP COLUMN error
    DROP COLUMN permalink
    DROP COLUMN created;

ALTER TABLE comments
    ALTER COLUMN transcriber RENAME to author
    DROP COLUMN from_archive;

CREATE TABLE IF NOT EXISTS redditor (
    reddit_account citext
        REFERENCES redditor(name),
    name citext,
    valid boolean
        NOT NULL
        DEFAULT TRUE,
);

CREATE TABLE IF NOT EXISTS discord_user (
    reddit_account citext
        REFERENCES redditor(name),
    name citext,
    discord_id bigint
        PRIMARY KEY,
    verified boolean
        NOT NULL
        DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS discord_user (
    name citext
        NO NULL,
    discord_id bigint
        PRIMARY KEY,
    verified boolean
        NOT NULL
        DEFAULT FALSE
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
