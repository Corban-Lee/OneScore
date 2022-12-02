
CREATE TABLE IF NOT EXISTS scores (
    member_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (member_id, guild_id)
)
