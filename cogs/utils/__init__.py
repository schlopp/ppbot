import discord

MEME_URL = "https://youtu.be/4rgxdf-fVw0"
VOTE_URL = "https://top.gg/bot/735147633076863027/vote"
RED = discord.Colour(16007990)
GREEN = discord.Colour(5025616)
BLUE = discord.Colour(2201331)
PINK = discord.Colour(15418782)
REAL_LIFE_COMPARISONS: dict[int, str] = {
    0: "your IRL pp",
    60: "the average door",
    4_133: "a football field",
    11_800: "the Eiffel Tower",
    14_519: "the depth of the ocean",
    15_000: "the Empire State Building",
    145_200: "the depth of the ocean",
    348_385: "Mount Everest",
    434_412: "the Mariana Trench",
    4_588_228: "the 405 freeway",
    219_173_228: "the distance of New York to London",
    501_653_543: "the diameter of the fucking earth",
    15_157_486_080: "the distance from the earth to the moon",
    5_984_252_000_000: "the distance from the earth to THE SUN",
}
ITEM_COUNT_COMMENTS: dict[int, tuple[str, str]] = {
    0: ("r u poor?", "r they poor?"),
    1: ("Not much bro", "Not much"),
    5: ("You must be new here", "They must be new here"),
    10: ("You're getting there", "They're getting there"),
    20: ("Not bad", "Not bad"),
    100: ("That's pretty good", "That's pretty good"),
    200: (
        "You're either rich, or you don't know how to spend your inches wisely",
        "They're either rich, or they don't know how to spend their inches wisely",
    ),
    500: ("God DAMN", "God DAMN"),
    1000: ("You must be a collector or sum", "They must be a collector or sum"),
    5000: ("Jesus fucking christ man", "Jesus fucking christ man"),
    10_000: (
        "You use this bot way too fucking much",
        "They use this bot way too fucking much",
    ),
    20_000: (
        "Are you mentally OK? Do u need a hug??",
        "Are they mentally OK? Do they need a hug??",
    ),
    100_000: (
        "Dude just give up this is too much",
        "Dude tell them to just give up this is too much",
    ),
    1_000_000: (
        "Okay. You win. I give up. I fucking quit. You win the game. Fuck you.",
        "Okay. They win. I give up. I fucking quit. They win the game. Fuck em.",
    ),
}

InteractionChannel = (
    discord.abc.Messageable
    | discord.PartialMessageable
    | discord.Thread
    | discord.VoiceChannel
    | discord.StageChannel
    | discord.TextChannel
    | discord.CategoryChannel
    | discord.StoreChannel
    | discord.Thread
    | discord.PartialMessageable
    | discord.ForumChannel
)

from .bot import DatabaseWrapper as DatabaseWrapper, Bot as Bot
from .formatters import (
    IntFormatType as IntFormatType,
    MarkdownFormat as MarkdownFormat,
    Article as Article,
    format_int as format_int,
    format_inches as format_inches,
    format_time as format_time,
    format_cooldown as format_cooldown,
    format_iterable as format_iterable,
    format_ordinal as format_ordinal,
    format_amount as format_amount,
    clean as clean,
)
from .errors import (
    PpMissing as PpMissing,
    PpNotBigEnough as PpNotBigEnough,
    InvalidArgumentAmount as InvalidArgumentAmount,
)
from .helpers import (
    limit_text as limit_text,
    compare as compare,
    find_nearest_number as find_nearest_number,
    Record as Record,
    Object as Object,
    DatabaseWrapperObject as DatabaseWrapperObject,
    DifferenceTracker as DifferenceTracker,
    RecordNotFoundError as RecordNotFoundError,
    Embed as Embed,
    RowLevelLockMode as RowLevelLockMode,
    IntegerHolder as IntegerHolder,
    is_weekend as is_weekend,
    SlashCommandMappingManager as SlashCommandMappingManager,
    format_slash_command as format_slash_command,
)
from .cards import Rank as Rank, Suit as Suit, Deck as Deck, Hand as Hand
from .command import (
    ExtendBucketType as ExtendBucketType,
    CooldownFactory as CooldownFactory,
    CooldownTierInfoDict as CooldownTierInfoDict,
    CommandOnCooldown as CommandOnCooldown,
    RedisCooldownMapping as RedisCooldownMapping,
    CommandCategory as CommandCategory,
    Command as Command,
)
from .managers import (
    DuplicateReplyListenerError as DuplicateReplyListenerError,
    ReplyManager as ReplyManager,
    DatabaseTimeoutManager as DatabaseTimeoutManager,
    wait_for_component_interaction as wait_for_component_interaction,
    ChangelogManager as ChangelogManager,
)
from .command_logs import CommandLog as CommandLog
from .streaks import Streaks as Streaks
from .items import (
    UnknownItemError as UnknownItemError,
    UselessItem as UselessItem,
    LegacyItem as LegacyItem,
    MultiplierItem as MultiplierItem,
    BuffItem as BuffItem,
    ToolItem as ToolItem,
    Item as Item,
    InventoryItem as InventoryItem,
    ItemManager as ItemManager,
    MissingTool as MissingTool,
)
from .pps import (
    BoostType as BoostType,
    Pp as Pp,
    PpExtras as PpExtras,
    DatabaseTimeout as DatabaseTimeout,
)
from .paginator import (
    PaginatorActions as PaginatorActions,
    CategorisedPaginatorActions as CategorisedPaginatorActions,
    Paginator as Paginator,
    CategorisedPaginator as CategorisedPaginator,
)
from .generate_rewards import give_random_reward as give_random_reward
from .minigames import (
    Minigame as Minigame,
    ReverseMinigame as ReverseMinigame,
    RepeatMinigame as RepeatMinigame,
    FillInTheBlankMinigame as FillInTheBlankMinigame,
    ClickThatButtonMinigame as ClickThatButtonMinigame,
    MinigameDialogueManager as MinigameDialogueManager,
)
from .donations import Donation
