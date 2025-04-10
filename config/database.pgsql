CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix TEXT,
    custom_role_requirement_role_id BIGINT,
    custom_role_parent_role_id BIGINT
);


CREATE TABLE IF NOT EXISTS user_settings(
    user_id BIGINT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS pps (
    user_id BIGINT PRIMARY KEY,
    pp_multiplier BIGINT NOT NULL DEFAULT 1,
    pp_size BIGINT NOT NULL DEFAULT 0,
    pp_name TEXT NOT NULL DEFAULT 'Unnamed Pp',
    digging_depth INTEGER NOT NULL DEFAULT 0
);


CREATE TABLE IF NOT EXISTS inventories (
    user_id BIGINT,
    item_id TEXT,
    item_amount BIGINT,
    PRIMARY KEY (user_id, item_id)
);


CREATE TABLE IF NOT EXISTS streaks (
    user_id BIGINT PRIMARY KEY,
    daily_streak SMALLINT NOT NULL DEFAULT 0,
    last_daily TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS donations (
    recipiant_id BIGINT NOT NULL,
    donor_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount INTEGER NOT NULL DEFAULT 0
);


-- CREATE TABLE IF NOT EXISTS role_list(
--     guild_id BIGINT,
--     role_id BIGINT,
--     key TEXT,
--     value TEXT,
--     PRIMARY KEY (guild_id, role_id, key)
-- );
-- A list of role: value mappings should you need one.
-- This is not required for VBU, so is commented out by default.


-- CREATE TABLE IF NOT EXISTS channel_list(
--     guild_id BIGINT,
--     channel_id BIGINT,
--     key TEXT,
--     value TEXT,
--     PRIMARY KEY (guild_id, channel_id, key)
-- );
-- A list of channel: value mappings should you need one.
-- This is not required for VBU, so is commented out by default.