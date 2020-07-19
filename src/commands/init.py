import random
import discord
from discord import Embed
from main import GAMES
from discord.ext import commands
from discord.ext.commands import MissingPermissions, CheckFailure, MissingRequiredArgument
import utils.decorators as decorators
from utils.decorators import check_category, is_arg_in_modes, check_channel, has_role_or_above
from utils.utils import is_url_image
from modules.rank import Rank
from modules.game import Game


class Init(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def init_elo_by_anddy(self, ctx):
        """Init the bot in the server.

        Initialize the bot to be ready on a guild.
        This command creates every channel needed for the Bot to work.
        Can be used anywhere. Need to have manage_roles
        Read https://github.com/AnddyAnddy/discord-elo-bot/wiki/How-to-set-up
        """
        guild = ctx.guild
        if not discord.utils.get(guild.roles, name="Elo Admin"):
            await guild.create_role(name="Elo Admin",
                                    # permissions=discord.Permissions.all_channel(),
                                    colour=discord.Colour(0xAA0000))
            await ctx.send("Elo admin role created. Since I don't know the " \
                "layout of your roles, I let you put this new role above "\
                "normal users.")

        if not discord.utils.get(guild.roles, name="20 games double xp"):
            for elem in (100, 50, 20):
                await guild.create_role(name=f"{elem} games double xp",
                    colour=discord.Colour(0x5AE78E))
            await ctx.send("Premium roles created. Since I don't know the " \
                "layout of your roles, I let you put this new role above "\
                "normal users.")

        if not discord.utils.get(guild.categories, name='Elo by Anddy'):
            perms_secret_chan = {
                guild.default_role:
                    discord.PermissionOverwrite(read_messages=False),
                guild.me:
                    discord.PermissionOverwrite(read_messages=True),
                discord.utils.get(guild.roles, name="Elo Admin"):
                    discord.PermissionOverwrite(read_messages=True)
            }

            base_cat = await guild.create_category(name="Elo by Anddy")
            await guild.create_text_channel(name="Init",
                                            category=base_cat,
                                            overwrites=perms_secret_chan)
            await guild.create_text_channel(name="Moderators",
                                            category=base_cat,
                                            overwrites=perms_secret_chan)
            await guild.create_text_channel(name="Info_chat", category=base_cat)
            await guild.create_text_channel(name="Register", category=base_cat)
            await guild.create_text_channel(name="Submit", category=base_cat)
            await guild.create_text_channel(name="Autosubmit", category=base_cat)
            await guild.create_text_channel(name="Game_announcement",
                                            category=base_cat)
            await guild.create_text_channel(name="Bans",
                                            category=base_cat)
            await guild.create_category(name="Solo elo")

            await guild.create_category(name="Teams elo")

            await ctx.send("Elo by Anddy created, init done, use !help !")

        if ctx.guild.id not in GAMES:
            GAMES[guild.id] = Game(guild.id)

    @commands.command()
    @has_role_or_above('Elo Admin')
    @check_channel('init')
    async def add_mode(self, ctx, mode):
        """Add a mode to the game modes.

        Example: !add_mode 4
        Will add the mode 4vs4 into the available modes, a channel will be
        created and the leaderboard will now have a 4 key.
        Can be used only in init channel by a manage_roles having user."""
        if mode.isdigit() and int(mode) > 0:
            nb_p = int(mode)
            if GAMES[ctx.guild.id].add_mode(nb_p):
                guild = ctx.message.guild
                solo_cat = discord.utils.get(guild.categories, name="Solo elo")
                teams_cat = discord.utils.get(guild.categories, name="Teams elo")
                await guild.create_text_channel(f'{nb_p}vs{nb_p}',
                                                category=solo_cat)
                await guild.create_text_channel(f'{nb_p}vs{nb_p}',
                                                category=teams_cat)
                await ctx.send(embed=Embed(color=0x00FF00,
                                           description="The game mode has been added."))
                if not discord.utils.get(guild.roles, name=f"{mode}vs{mode} Elo Player"):

                    await guild.create_role(name=f"{mode}vs{mode} Elo Player",
                        colour=discord.Colour(random.randint(0, 0xFFFFFF)))
                    await ctx.send(f"{mode}vs{mode} Elo Player role created")
                return

        await ctx.send(embed=Embed(color=0x000000,
                                   description="Couldn't add the game mode."))

    @commands.command()
    @has_role_or_above('Elo Admin')
    @check_channel('init')
    @is_arg_in_modes(GAMES)
    async def delete_mode(self, ctx, mode):
        GAMES[ctx.guild.id].remove_mode(int(mode))
        await ctx.send(embed=Embed(color=0x00FF00,
                                   description="The mode has been deleted, please delete the channel."))


    @commands.command()
    @has_role_or_above('Elo Admin')
    @check_channel('init')
    @is_arg_in_modes(GAMES)
    # @args_at_pos_digits((0, 3, 4))
    # @rank_update(GAMES, (0, 3, 4))
    async def add_rank(self, ctx, mode, name, image_url, from_points, to_points):
        """Add a rank and set this rank to everyone having required points.

        mode is the N in NvsN.
        name is the name of the rank. Must be in " "
        from_points is the points required to have this rank.
        to_points is the max points of this rank.
        """
        game = GAMES[ctx.guild.id]
        mode = int(mode)
        from_points = int(from_points)
        to_points = int(to_points)
        if to_points < from_points:
            await ctx.send("To points must be greater than from points")
            return
        if not is_url_image(image_url):
            await ctx.send("The url doesn't lead to an image. (png jpg jpeg)")
            return
        if name in game.ranks[mode]:
            await ctx.send("The rank couldn't be added, maybe it already exists.")
            return

        game.ranks[mode][name] = Rank(mode, name, image_url, from_points, to_points)
        await ctx.send("The rank was added and the players got updated.")

    @commands.command()
    @check_channel('init')
    @is_arg_in_modes(GAMES)
    async def setpickmode(self, ctx, mode, new_mode):
        """Set the pickmode to the new_mode set

        :param: new_mode must be a number [0, 1, 2, 3]:
            [random teams, balanced random, random cap, best cap]
        """
        game = GAMES[ctx.guild.id]
        mode = int(mode)
        new_mode = int(new_mode)
        if new_mode not in range(3):
            await ctx.send("Wrong new_mode given, read help pickmode")
            return
        pickmodes = ["random teams", "balanced random", "random cap", "best cap"]
        game.queues[mode].mode = new_mode
        game.queues[mode].pick_function = game.queues[mode].modes[new_mode]
        await ctx.send(f"Pickmode changed to {pickmodes[new_mode]}!")


    @commands.command()
    @check_channel('init')
    async def setfavpos(self, ctx, *args):
        """The arguments will now be in the list that players can pick as position.

        example:
        !setfavpos gk dm am st
        will allow the players to use
        !pos st gk am dm
        """
        game = GAMES[ctx.guild.id]
        setattr(game, "available_positions", list(args))
        await ctx.send(f"The available_positions are now {game.available_positions}")



    @commands.command()
    @check_channel('init')
    async def add_map(self, ctx, emoji, name):
        """Add the map in the available maps."""
        await ctx.send(GAMES[ctx.guild.id].add_map(emoji, name))


    @commands.command()
    @check_channel('init')
    async def delete_map(self, ctx, name):
        """Delete the map from the available maps."""
        await ctx.send(GAMES[ctx.guild.id].delete_map(name))

    @commands.command()
    @check_channel('init')
    @is_arg_in_modes(GAMES)
    async def setmappick(self, ctx, mode, pickmode):
        """Set the way to pick maps.

        0: Maps aren't used
        1: The map is randomly picked
        2: The map is picked with emojis
        """
        if not pickmode.isdigit() or int(pickmode) not in range(3):
            await ctx.send(embed=Embed(color=0x000000,
                description="Incorrect pickmode, read !help pickmode."))
            return
        pickmode = int(pickmode)
        mode = int(mode)
        game = GAMES[ctx.guild.id]
        game.queues[mode].mapmode = pickmode
        pickmodes = ["Maps aren't used", "The map is randomly picked",
            "The map is picked with emojis"]
        await ctx.send(embed=Embed(color=0x00FF00,
            description=f"The pick mode is set to: {pickmodes[pickmode]}."))

def setup(bot):
    bot.add_cog(Init(bot))
