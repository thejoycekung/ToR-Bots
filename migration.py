import praw

from secrets import passwords_and_tokens

reddit = praw.Reddit(
    client_id=passwords_and_tokens.reddit_id,
    client_secret=passwords_and_tokens.reddit_token,
    user_agent=passwords_and_tokens.user_agent,
)

# TO BE DONE
