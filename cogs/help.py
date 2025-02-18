import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="사용 가능한 명령어 목록을 확인합니다.")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="음악", value="music"),
            app_commands.Choice(name="경제", value="economy"),
            app_commands.Choice(name="도박", value="gambling"),
            app_commands.Choice(name="설정", value="settings"),
        ]
    )
    async def help(self, interaction: discord.Interaction, category: str = None):
        """도움말 명령어"""
        embed = discord.Embed(title="🦁 사자봇 도움말", color=discord.Color.gold())

        if category is None:
            # 전체 카테고리 목록 출력
            embed.description = "사자봇의 모든 명령어를 확인할 수 있습니다.\n아래 카테고리 중 하나를 선택하여 자세한 도움말을 확인하세요."
            embed.add_field(name="🎵 음악", value="`/도움말 음악`", inline=True)
            embed.add_field(name="💰 경제", value="`/도움말 경제`", inline=True)
            embed.add_field(name="🎲 도박", value="`/도움말 도박`", inline=True)
            embed.add_field(name="⚙️ 설정", value="`/도움말 설정`", inline=True)
        elif category == "music":
            embed.description = "**🎵 음악 명령어**"
            embed.add_field(name="`/재생 [노래제목/URL]`", value="YouTube에서 노래를 검색하여 재생", inline=False)
            embed.add_field(name="`/정지`", value="현재 재생 중인 노래를 정지하고 음성 채널에서 나감", inline=False)
            embed.add_field(name="`/스킵`", value="현재 재생 중인 노래를 건너뜀", inline=False)
            embed.add_field(name="`/대기열`", value="재생 대기 중인 노래 목록 확인", inline=False)
        elif category == "economy":
            embed.description = "**💰 경제 명령어**"
            embed.add_field(name="`/잔고`", value="현재 잔액을 확인", inline=False)
            embed.add_field(name="`/송금 [@유저] [금액]`", value="다른 유저에게 LC를 송금", inline=False)
            embed.add_field(name="`/꽁돈`", value="1시간마다 무료 LC 획득 가능", inline=False)
            embed.add_field(name="`/이자`", value="은행 이자 수령 (하루 1회, 10,000 LC 이상 보유 시)", inline=False)
            embed.add_field(name="`/순위`", value="서버 내 잔액 순위 확인", inline=False)
        elif category == "gambling":
            embed.description = "**🎲 도박 명령어**"
            embed.add_field(name="`/블랙잭 [금액]`", value="딜러와 블랙잭 승부 (21점에 가까운 쪽이 승리)", inline=False)
            embed.add_field(name="`/하이로우 [금액]`", value="카드의 다음 숫자가 높을지 낮을지 예측", inline=False)
            embed.add_field(name="`/슬롯머신 [금액]`", value="슬롯머신을 돌려 동일한 그림이 나오면 당첨", inline=False)
            embed.add_field(name="`/러시안룰렛 [금액] [1~6]`", value="1/6 확률로 즉사하는 러시안룰렛", inline=False)
            embed.add_field(name="`/주사위배틀 [금액]`", value="개최자가 먼저 주사위를 굴리고 참가자와 대결", inline=False)
        elif category == "settings":
            embed.description = "**⚙️ 설정 명령어**"
            embed.add_field(name="`/채널설정 [음악/게임/로그]`", value="특정 기능을 사용할 채널을 설정", inline=False)
            embed.add_field(name="`/채널확인`", value="현재 설정된 채널 확인", inline=False)
        else:
            embed.description = "올바른 카테고리를 선택하세요."
            embed.add_field(name="🎵 음악", value="`/도움말 음악`", inline=True)
            embed.add_field(name="💰 경제", value="`/도움말 경제`", inline=True)
            embed.add_field(name="🎲 도박", value="`/도움말 도박`", inline=True)
            embed.add_field(name="⚙️ 설정", value="`/도움말 설정`", inline=True)

        embed.set_footer(text="문의사항이나 버그 제보는 공식서버에 남겨주세요.\nhttps://discord.gg/ptx9u9D4WV")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
