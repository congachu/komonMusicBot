import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="사용 가능한 모든 명령어를 보여줍니다")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🦁 사자봇 도움말",
            description="디스코드 다기능 봇입니다. 음악, 경제, 게임 기능을 제공합니다.\n모든 명령어는 `/`(슬래시) 명령어로 사용할 수 있습니다.",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🎵 음악 명령어",
            value=(
                "**/재생 [노래제목/URL]** - YouTube에서 노래를 검색하여 재생\n"
                "**/정지** - 현재 재생 중인 노래를 정지하고 음성 채널에서 나감\n"
                "**/스킵** - 현재 재생 중인 노래를 건너뜀\n"
                "**/대기열** - 현재 재생 목록을 표시"
            ),
            inline=False
        )

        embed.add_field(
            name="💰 경제 시스템",
            value=(
                "**/잔고** - 현재 잔액 확인\n"
                "**/송금 [@유저] [금액]** - 다른 유저에게 LC 송금\n"
                "**/꽁돈** - 1시간마다 무료 LC 획득\n"
                "**/이자** - 하루에 한 번 은행 이자 받기 (10,000 LC 이상 필요)\n"
                "**/순위** - 서버 내 유저 잔고 순위 확인"
            ),
            inline=False
        )

        embed.add_field(
            name="🃏 블랙잭 게임",
            value=(
                "**/블랙잭 [금액]** - 블랙잭 게임 시작\n"
                "**히트** - 추가 카드 받기\n"
                "**스탠드** - 현재 카드 유지하고 결과 확인"
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ 관리자 명령어 (개발자 전용)",
            value=(
                "**/보상금 [@유저] [금액]** - 특정 유저에게 LC 추가\n"
                "**/벌금 [@유저] [금액]** - 특정 유저 LC 감소"
            ),
            inline=False
        )

        embed.add_field(
            name="🔧 채널 설정",
            value=(
                "**/채널설정 [음악/게임/로그]** - 특정 기능을 사용할 채널 설정\n"
                "**/채널확인** - 현재 설정된 채널 확인"
            ),
            inline=False
        )

        embed.add_field(
            name="📝 주의사항",
            value=(
                "• 모든 명령어는 **설정된 채널**에서만 사용 가능\n"
                "• 음악 재생 전 반드시 **음성 채널에 접속**해야 함\n"
                "• `/보상금` 및 `/벌금` 명령어는 **개발자만 사용 가능**\n"
                "• `/이자`는 하루 한 번만 가능하며, 잔고 10,000 LC 이상 필요"
            ),
            inline=False
        )

        embed.set_footer(text="문의사항이나 버그 제보는 공식 서버에서 알려주세요.\nhttps://discord.gg/ptx9u9D4WV")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
