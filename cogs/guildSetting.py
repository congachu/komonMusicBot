import discord
from discord import app_commands
from discord.ext import commands


class GuildSetting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def setup_guild_settings_table(self):
        """ 새로운 테이블 구조 반영 """
        cursor = None
        try:
            cursor = self.bot.get_cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guild_setting (
                    guild_id BIGINT PRIMARY KEY,
                    allowed_music_channel BIGINT,
                    allowed_game_channel BIGINT,
                    allowed_log_channel BIGINT,
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

    @app_commands.command(name="채널설정", description="명령어를 사용할 채널을 설정합니다.")
    @app_commands.describe(channel_type="설정할 채널 유형을 선택하세요.")
    @app_commands.choices(
        channel_type=[
            app_commands.Choice(name="음악 채널", value="music"),
            app_commands.Choice(name="게임 채널", value="game"),
            app_commands.Choice(name="로그 채널", value="log"),
        ]
    )
    async def set_channel(self, interaction: discord.Interaction, channel_type: app_commands.Choice[str]):
        """ 특정 기능(음악, 게임, 로그)의 명령어를 사용할 채널을 설정 """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        cursor = None
        try:
            cursor = self.bot.get_cursor()
            await self.setup_guild_settings_table()

            column_name = f"allowed_{channel_type.value}_channel"

            cursor.execute(f"""
                    INSERT INTO guild_setting 
                        (guild_id, {column_name})
                    VALUES (%s, %s)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET 
                        {column_name} = EXCLUDED.{column_name}
                """, (interaction.guild.id, interaction.channel.id))

            self.bot.conn.commit()
            await interaction.response.send_message(
                f"{interaction.channel.mention} 채널에서 **{channel_type.name}** 명령어를 사용할 수 있습니다.", ephemeral=True)

        except Exception as e:
            self.bot.conn.rollback()
            print(f"채널 설정 중 오류: {e}")
            await interaction.response.send_message("채널 설정 중 오류가 발생했습니다.", ephemeral=True)
        finally:
            cursor.close()

    @app_commands.command(name="채널확인", description="설정된 명령어 사용 가능한 채널을 확인합니다.")
    async def check_channel(self, interaction: discord.Interaction):
        """ 설정된 채널 확인 """
        cursor = None
        try:
            cursor = self.bot.get_cursor()
            await self.setup_guild_settings_table()

            cursor.execute("""
                    SELECT allowed_music_channel, allowed_game_channel, allowed_log_channel
                    FROM guild_setting
                    WHERE guild_id = %s
                """, (interaction.guild.id,))

            settings = cursor.fetchone()

            if not settings:
                await interaction.response.send_message("설정된 채널이 없습니다.", ephemeral=True)
                return

            music_channel = interaction.guild.get_channel(settings[0]) if settings[0] else "설정되지 않음"
            game_channel = interaction.guild.get_channel(settings[1]) if settings[1] else "설정되지 않음"
            log_channel = interaction.guild.get_channel(settings[2]) if settings[2] else "설정되지 않음"

            embed = discord.Embed(title="설정된 명령어 사용 채널", color=discord.Color.blue())
            embed.add_field(name="🎵 음악 채널", value=music_channel.mention if isinstance(music_channel,
                                                                                      discord.TextChannel) else music_channel,
                            inline=False)
            embed.add_field(name="🎮 게임 채널", value=game_channel.mention if isinstance(game_channel,
                                                                                     discord.TextChannel) else game_channel,
                            inline=False)
            embed.add_field(name="📜 로그 채널",
                            value=log_channel.mention if isinstance(log_channel, discord.TextChannel) else log_channel,
                            inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"채널 확인 중 오류: {e}")
            await interaction.response.send_message("채널 확인 중 오류가 발생했습니다.", ephemeral=True)
        finally:
            cursor.close()

    async def check_channel_permission(self, interaction: discord.Interaction, tag: str) -> bool:
        """ 해당 채널에서 명령어 실행 가능 여부 확인 """
        cursor = None
        try:
            cursor = self.bot.get_cursor()
            column_name = f"allowed_{tag}_channel"

            cursor.execute(f"""
                    SELECT {column_name}
                    FROM guild_setting
                    WHERE guild_id = %s
                """, (interaction.guild.id,))

            result = cursor.fetchone()

            # 설정된 채널이 없으면 모든 채널에서 허용
            if not result or result[0] is None:
                return True

            # 현재 명령어가 실행된 채널이 허용된 채널인지 확인
            return interaction.channel.id == result[0]

        except Exception as e:
            print(f"권한 확인 중 오류: {e}")
            return False
        finally:
            cursor.close()


async def setup(bot):
    await bot.add_cog(GuildSetting(bot))
