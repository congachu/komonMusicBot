import discord
from discord import app_commands
from discord.ext import commands


class GuildSetting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def setup_music_settings_table(self):
        cursor = None
        try:
            cursor = self.bot.get_cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS music_bot_settings (
                    guild_id BIGINT PRIMARY KEY,
                    allowed_channel_id BIGINT,
                    UNIQUE(guild_id)
                )
            """)
            self.bot.conn.commit()
        except Exception as e:
            self.bot.conn.rollback()
            print(f"테이블 생성 중 오류: {e}")
            raise e
        finally:
            cursor.close()

    @app_commands.command(name="음악채널설정", description="노래봇을 사용할 수 있는 채널을 설정합니다.")
    async def set_music_channel(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        cursor = None
        try:
            cursor = self.bot.get_cursor()
            await self.setup_music_settings_table()

            cursor.execute("""
                INSERT INTO music_bot_settings 
                    (guild_id, allowed_channel_id)
                VALUES (%s, %s)
                ON CONFLICT (guild_id) 
                DO UPDATE SET 
                    allowed_channel_id = EXCLUDED.allowed_channel_id
            """, (interaction.guild.id, interaction.channel.id))

            self.bot.conn.commit()
            await interaction.response.send_message(
                f"{interaction.channel.mention} 채널에서만 노래봇 명령어를 사용할 수 있습니다.", ephemeral=True)

        except Exception as e:
            self.bot.conn.rollback()
            print(f"채널 설정 중 오류: {e}")
            await interaction.response.send_message("채널 설정 중 오류가 발생했습니다.", ephemeral=True)
        finally:
            cursor.close()

    @app_commands.command(name="음악채널확인", description="현재 노래봇 사용 가능한 채널을 확인합니다.")
    async def check_music_channel(self, interaction: discord.Interaction):
        cursor = None
        try:
            cursor = self.bot.get_cursor()
            await self.setup_music_settings_table()

            cursor.execute("""
                SELECT allowed_channel_id
                FROM music_bot_settings
                WHERE guild_id = %s
            """, (interaction.guild.id,))

            settings = cursor.fetchone()

            if not settings:
                await interaction.response.send_message("설정된 음악 채널이 없습니다.", ephemeral=True)
                return

            allowed_channel = interaction.guild.get_channel(settings[0])

            embed = discord.Embed(title="음악 채널 설정", color=discord.Color.blue())
            embed.add_field(
                name="허용된 채널",
                value=allowed_channel.mention if allowed_channel else "설정되지 않음",
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"채널 확인 중 오류: {e}")
            await interaction.response.send_message("채널 확인 중 오류가 발생했습니다.", ephemeral=True)
        finally:
            cursor.close()

    async def check_music_channel_permission(self, interaction: discord.Interaction) -> bool:
        cursor = None
        try:
            cursor = self.bot.get_cursor()
            cursor.execute("""
                SELECT allowed_channel_id 
                FROM music_bot_settings 
                WHERE guild_id = %s
            """, (interaction.guild.id,))

            result = cursor.fetchone()

            # If no channel is set, allow all channels
            if not result or result[0] is None:
                return True

            # Check if the interaction is in the allowed channel
            return interaction.channel.id == result[0]

        except Exception as e:
            print(f"권한 확인 중 오류: {e}")
            return False
        finally:
            cursor.close()


async def setup(bot):
    await bot.add_cog(GuildSetting(bot))