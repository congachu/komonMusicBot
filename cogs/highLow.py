import random
import discord
from discord import app_commands
from discord.ext import commands


class HighLow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    async def ensure_user(self, user_id):
        """유저가 존재하는지 확인 후 없으면 추가"""
        self.bot.cursor.execute("SELECT money FROM users WHERE uuid = %s", (user_id,))
        user_data = self.bot.cursor.fetchone()
        if not user_data:
            self.bot.cursor.execute("INSERT INTO users (uuid, money) VALUES (%s, 10000)", (user_id,))
            self.bot.conn.commit()
            return 10000
        return user_data[0]

    async def check_game_channel(self, interaction):
        settings_cog = self.bot.get_cog("GuildSetting")
        if settings_cog and not await settings_cog.check_channel_permission(interaction, "game"):
            await interaction.response.send_message("이 채널에서는 게임 명령어를 사용할 수 없습니다.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="하이로우", description="카드의 다음 숫자가 높을지 낮을지 맞히세요!")
    async def highlow(self, interaction: discord.Interaction, amount: int):
        if not await self.check_game_channel(interaction):
            return

        """하이로우 게임 시작"""
        user_id = interaction.user.id

        if user_id in self.games:
            await interaction.response.send_message("이미 진행 중인 게임이 있습니다.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("베팅 금액은 1LC 이상이어야 합니다.", ephemeral=True)
            return

        current_balance = await self.ensure_user(user_id)
        if current_balance < amount:
            await interaction.response.send_message("잔액이 부족합니다.", ephemeral=True)
            return

        await interaction.response.defer()

        # 현재 카드 설정
        current_card = random.randint(1, 13)
        self.games[user_id] = {"current_card": current_card, "amount": amount}

        view = HighLowView(self.bot, user_id)

        embed = discord.Embed(title="🔼 하이로우 게임 시작!", color=discord.Color.blue())
        embed.add_field(name="현재 카드", value=self.card_to_string(current_card), inline=False)
        embed.set_footer(text="하이 또는 로우 버튼을 눌러주세요!")

        await interaction.followup.send(embed=embed, view=view)

    async def check_highlow(self, interaction, user_id, choice):
        """하이로우 결과 체크"""
        game = self.games.pop(user_id, None)
        if not game:
            await interaction.response.send_message("진행 중인 게임이 없습니다.", ephemeral=True)
            return

        next_card = random.randint(1, 13)
        win = (choice == "high" and next_card > game["current_card"]) or \
              (choice == "low" and next_card < game["current_card"])

        winnings = int(game["amount"]*0.2) if win else -game["amount"]

        self.bot.cursor.execute("UPDATE users SET money = money + %s WHERE uuid = %s", (winnings, user_id))
        self.bot.conn.commit()

        new_balance = await self.ensure_user(user_id)

        result_text = "**✅ 승리! 1.2배 획득!**" if win else "**❌ 패배! 전액 손실!**"
        color = discord.Color.green() if win else discord.Color.red()

        embed = discord.Embed(title="🎴 하이로우 결과", color=color)
        embed.add_field(name="이전 카드", value=self.card_to_string(game["current_card"]), inline=False)
        embed.add_field(name="다음 카드", value=self.card_to_string(next_card), inline=False)
        embed.add_field(name="📌 결과", value=result_text, inline=False)
        embed.set_footer(text=f"현재 잔액: {new_balance:,} LC")

        await interaction.response.edit_message(embed=embed, view=None)

    @staticmethod
    def card_to_string(value):
        """숫자를 카드 문자로 변환"""
        return {1: "A", 11: "J", 12: "Q", 13: "K"}.get(value, str(value))


class HighLowView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="하이", style=discord.ButtonStyle.primary)
    async def high_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 게임에 참여할 수 없습니다.", ephemeral=True)
            return
        await self.bot.get_cog("HighLow").check_highlow(interaction, self.user_id, "high")

    @discord.ui.button(label="로우", style=discord.ButtonStyle.secondary)
    async def low_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 게임에 참여할 수 없습니다.", ephemeral=True)
            return
        await self.bot.get_cog("HighLow").check_highlow(interaction, self.user_id, "low")


async def setup(bot):
    await bot.add_cog(HighLow(bot))
