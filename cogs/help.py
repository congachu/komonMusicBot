import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    help_categories = {
        "노래": {
            "🎵 음악 명령어": """
            **/재생 [노래제목/URL]** - YouTube에서 노래를 검색하여 재생  
            **/정지** - 현재 재생 중인 노래를 정지하고 음성 채널에서 나감  
            **/스킵** - 현재 재생 중인 노래를 건너뜀  
            **/대기열** - 현재 재생 목록을 표시  
            """
        },
        "경제": {
            "💰 경제 시스템": """
            **/잔고** - 현재 잔액 확인  
            **/송금 [@유저] [금액]** - 다른 유저에게 LC 송금  
            **/꽁돈** - 1시간마다 무료 LC 획득  
            **/이자** - 하루에 한 번 은행 이자 받기 (10,000 LC 이상 필요)  
            **/순위** - 서버 내 유저 잔고 순위 확인  
            """
        },
        "도박": {
            "🃏 블랙잭 게임": """
            **/블랙잭 [금액]** - 블랙잭 게임 시작  
            **히트** - 추가 카드 받기  
            **스탠드** - 현재 카드 유지하고 결과 확인  
            """
        },
        "관리자": {
            "⚙️ 관리자 명령어 (개발자 전용)": """
            **/보상금 [@유저] [금액]** - 특정 유저에게 LC 추가  
            **/벌금 [@유저] [금액]** - 특정 유저 LC 감소  
            """
        },
        "설정": {
            "🔧 채널 설정": """
            **/채널설정 [음악/게임/로그]** - 특정 기능을 사용할 채널 설정  
            **/채널확인** - 현재 설정된 채널 확인  
            """
        },
        "주의사항": {
            "📝 주의사항": """
            • 모든 명령어는 **설정된 채널**에서만 사용 가능  
            • 음악 재생 전 반드시 **음성 채널에 접속**해야 함  
            • `/보상금` 및 `/벌금` 명령어는 **개발자만 사용 가능**  
            • `/이자`는 하루 한 번만 가능하며, 잔고 10,000 LC 이상 필요  
            """
        }
    }

    @app_commands.command(name="도움말", description="사용 가능한 명령어를 확인합니다.")
    @app_commands.choices(
        query=[
            app_commands.Choice(name="노래", value="노래"),
            app_commands.Choice(name="경제", value="경제"),
            app_commands.Choice(name="도박", value="도박"),
            app_commands.Choice(name="관리자", value="관리자"),
            app_commands.Choice(name="설정", value="설정"),
            app_commands.Choice(name="주의사항", value="주의사항")
        ]
    )
    async def help(self, interaction: discord.Interaction, query: str = None):
        """도움말 명령어"""
        embed = discord.Embed(title="사자봇 도움말", color=discord.Color.gold())

        if query:
            # 특정 카테고리 요청 시 해당 카테고리만 표시
            category = self.help_categories.get(query)
            if category:
                for name, value in category.items():
                    embed.add_field(name=name, value=value, inline=False)
            else:
                await interaction.response.send_message("해당 카테고리는 존재하지 않습니다.", ephemeral=True)
                return
        else:
            # 쿼리가 없을 때 전체 카테고리 목록 표시
            embed.description = "사용 가능한 도움말 카테고리:\n" + "\n".join(
                [f"- `/도움말 {key}`" for key in self.help_categories.keys()]
            )

        embed.set_footer(text="문의사항이나 버그 제보는 공식 서버에서 알려주세요.\nhttps://discord.gg/ptx9u9D4WV")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
