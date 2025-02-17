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

        # 음악 명령어
        music_commands = """
            /재생 [노래제목/URL] - YouTube에서 노래를 검색하여 재생합니다 (Spotify 지원 예정)
            /정지 - 현재 재생 중인 노래를 정지하고 음성 채널에서 나갑니다
            /스킵 - 현재 재생 중인 노래를 건너뜁니다
            /대기열 - 재생 대기 중인 노래 목록을 보여줍니다
            """
        embed.add_field(name="🎵 음악 명령어", value=music_commands, inline=False)

        # 블랙잭 명령어
        blackjack_commands = """
            /블랙잭 [배팅금액] - 블랙잭 게임을 시작합니다.

            승리: 배팅금액 2배 획득
            무승부: 배팅금액 반환
            패배: 배팅금액 손실
            블랙잭 (A + 10): 2.5배 획득

            버튼 설명:
            - 히트: 카드를 추가로 뽑습니다 (21을 넘지 않도록 주의!)
            - 스탠드: 딜러의 턴을 시작합니다
            """
        embed.add_field(name="🃏 블랙잭 명령어", value=blackjack_commands, inline=False)

        # 경제 시스템 명령어
        economy_commands = """
            /잔고 - 현재 잔액을 확인합니다
            /송금 [@유저] [금액] - 다른 유저에게 LC를 송금합니다
            /꽁돈 - 1시간마다 무료 LC를 획득할 수 있습니다
            /이자 - 하루에 한 번 은행 이자를 받을 수 있습니다 (잔고 10,000 LC 이상)
            /순위 - 서버 내에서 가장 많은 돈을 가진 유저 순위를 확인합니다
            """
        embed.add_field(name="💰 경제 시스템", value=economy_commands, inline=False)

        # 채널 설정 명령어
        channel_settings = """
            /채널설정 [음악/게임/로그] - 특정 기능을 사용할 채널을 설정합니다
            /채널확인 - 현재 설정된 채널을 확인합니다
            """
        embed.add_field(name="⚙️ 채널 설정", value=channel_settings, inline=False)

        # 주의사항
        notes = """
            • 모든 명령어는 설정된 채널에서만 사용할 수 있습니다
            • 음악을 재생하려면 먼저 음성 채널에 접속해야 합니다
            • /보상금 및 /벌금 명령어는 개발자만 사용할 수 있습니다
            • /이자는 하루에 한 번만 받을 수 있으며, 최소 10,000 LC 이상의 잔고가 필요합니다
            """
        embed.add_field(name="⚠️ 주의사항", value=notes, inline=False)

        # 푸터 추가
        embed.set_footer(text="문의사항이나 버그 제보는 공식서버에 남겨주세요.\nhttps://discord.gg/ptx9u9D4WV")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))