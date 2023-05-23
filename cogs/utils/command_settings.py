import toml
from typing import TypedDict


class GrowthCommandSettings(TypedDict):
    growth_rate: tuple[int, int]


class CommandSettings(TypedDict):
    grow: GrowthCommandSettings


_command_settings_toml = toml.load("config/commands.toml")
command_settings: CommandSettings = {
    "grow": {"growth_rate": tuple(_command_settings_toml["grow"]["growth_rate"])}
}
