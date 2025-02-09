import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="사용 가능한 모든 명령어를 보여줍니다")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎵 사자봇 도움말",
            description="디스코드 음악 재생 봇입니다.\n모든 명령어는 슬래시(/) 명령어로 사용할 수 있습니다.",
            color=discord.Color.blue()
        )

        # 음악 재생 명령어
        music_commands = """
        `/재생 [노래제목/URL]` - YouTube에서 노래를 검색하여 재생합니다 (Spotify 개발 중)
        `/정지` - 현재 재생 중인 노래를 정지하고 음성 채널에서 나갑니다
        `/스킵` - 현재 재생 중인 노래를 건너뜁니다
        `/대기열` - 재생 대기 중인 노래 목록을 보여줍니다
        """
        embed.add_field(name="🎵 음악 명령어", value=music_commands, inline=False)

        # 관리자 명령어
        admin_commands = """
        `/음악채널설정` - 노래봇 명령어를 사용할 수 있는 채널을 설정합니다
        `/음악채널확인` - 현재 설정된 노래봇 채널을 확인합니다
        """
        embed.add_field(name="⚙️ 관리자 명령어", value=admin_commands, inline=False)

        # 주의사항
        notes = """
        • 음악 명령어는 설정된 채널에서만 사용할 수 있습니다
        • 음악을 재생하려면 음성 채널에 먼저 접속해야 합니다
        • 관리자 명령어는 서버 관리자만 사용할 수 있습니다
        """
        embed.add_field(name="📝 주의사항", value=notes, inline=False)

        # 푸터 추가
        embed.set_footer(text="문의사항이나 버그 제보는 공식서버에 남겨주세요.\nhttps://discord.gg/ptx9u9D4WV")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))