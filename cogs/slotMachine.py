import random
import discord
from discord import app_commands
from discord.ext import commands


class SlotMachine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @app_commands.command(name="슬롯머신", description="슬롯머신을 돌려서 보상을 획득하세요!")
    async def slot_machine(self, interaction: discord.Interaction, amount: int):
        if not await self.check_game_channel(interaction):
            return

        user_id = interaction.user.id

        if amount <= 0:
            await interaction.response.send_message("베팅 금액은 1LC 이상이어야 합니다.", ephemeral=True)
            return

        current_balance = await self.ensure_user(user_id)
        if current_balance < amount:
            await interaction.response.send_message("잔액이 부족합니다.", ephemeral=True)
            return

        await interaction.response.defer()

        # 슬롯 기호
        symbols = ["🍒", "🍋", "🍉", "🔔", "⭐", "💎"]
        slot_result = [random.choice(symbols) for _ in range(3)]

        # 승리 판별
        if slot_result[0] == slot_result[1] == slot_result[2]:  # 잭팟 (5배)
            winnings = amount * 4
            result_text = "**🎉 잭팟! 5배 보상 획득!**"
        elif slot_result[0] == slot_result[1] or slot_result[1] == slot_result[2] or slot_result[0] == slot_result[2]:  # 2개 일치 (2배)
            winnings = amount
            result_text = "**✨ 2개 일치! 2배 보상 획득!**"
        else:  # 손실
            winnings = -amount
            result_text = "**😢 아쉽네요! 다음 기회에...**"

        # 데이터베이스 업데이트
        self.bot.cursor.execute("UPDATE users SET money = money + %s WHERE uuid = %s", (winnings, user_id))
        self.bot.conn.commit()

        # 새로운 잔액 조회
        new_balance = await self.ensure_user(user_id)

        # 결과 임베드 생성
        embed = discord.Embed(title="🎰 슬롯머신 결과!", color=discord.Color.gold())
        embed.add_field(name="🎲 슬롯 결과", value=" | ".join(slot_result), inline=False)
        embed.add_field(name="📌 결과", value=result_text, inline=False)

        if winnings > 0:
            embed.add_field(name="💰 획득 금액", value=f"+{winnings:,} LC", inline=False)
        else:
            embed.add_field(name="💸 손실 금액", value=f"-{abs(winnings):,} LC", inline=False)

        embed.set_footer(text=f"현재 잔액: {new_balance:,} LC")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SlotMachine(bot))
