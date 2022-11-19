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
    pp_name TEXT NOT NULL DEFAULT 'Unnamed Pp'
);


CREATE TABLE IF NOT EXISTS inventory (
    user_id BIGINT,
    item_name TEXT,
    amount BIGINT,
    PRIMARY KEY (user_id, item_name)
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
