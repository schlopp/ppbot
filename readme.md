# pp bot

The official GitHub repository of the Discord bot "pp bot", currently being rewritten.

## The #1 most addictive, weird, and stupid pp growing Discord bot.

But you probably already know that. You're just curious about how this whole thing works. See all the code and shit like that. Feel free to snoop around! You'll find the majority of the code inside the `/cogs` folder, where groups of commands are - somewhat - neatly packed into different files called "cogs". These are built using a mix of Novus, VoxelBotUtils and our own internal tools up in the `/cogs/utils` folder. If you're a bit fimiliar with Python and discord.py or pycord, it'll be pretty fimiliar to you.

## I want to run the bot on my own machine!

Good for you! To get started with self-hosting pp bot, make sure you have the latest version of python installed. Then, install the packages listed in `/requirements.txt`:

```sh
$ pip install -r requirements.txt
```

Now head on over to the `/config` folder and create a file called `config.toml`. Copy over the contents of `config.example.toml` into it and edit all the values to your liking. Some important things you should change include the bot token, PostgreSQL and Redis details. Pp bot needs both PostgreSQL and Redis to run successfully, so make sure you got those two installed as well.

Running the bot for the first time ain't that complicated. Assuming you haven't skipped the previous steps, all you have to do is run:

```sh
$ vbu run-bot
```

Having some issues with `vbu` not being a detected command on your system? You can instead do `python -m vbu run-bot` or, if you're on Windows, look up a tutorial on how to add your Python scripts folder to path. Preferably one from an Indian guy, they generally know best.

From here on out, go wild! Give yourself a gazillion inches with the admin commands! (I wont tell you where they're hidden, muhahaha.) Create entirely new commands/items! If you went through the trouble of running this thing yourself, you deserve all the power. Just make it clear you're not the official bot. Don't want any confusion.

## Can I contribute my own features?

As of right now, what you're able to contribute will be very limited. This repository doesn't even contain the code of the current pp bot; in fact it contains the rewrite I'm currently developing. Pp bot was one of the projects I've ever coded, and as a result, the old code is entirely dogshit. For the last year I've been rewriting every single thing about pp bot, making it look better, feel smoother, load faster and more entertaining.  

As a result of this rewrite, code contributions will **likely be rejected.** It's nothing personal, it's just that the project is very incomplete and I need a lil' more time before I can start dealing with other peoples' code. Once the rewrite is officially released, I'll be more open to contributions from you, the community.

An exception to this is dialogue contributions. All the minigames in pp bot need custom, funny dialogue. The bulk of this dialogue is contained inside the `config/minigames.toml` file. Feel free to add new dialogue options to this file, and submit them as PRs. I'll be sure to take a look at them <3
