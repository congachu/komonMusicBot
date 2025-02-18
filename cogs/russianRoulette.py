import random
import discord
from discord import app_commands
from discord.ext import commands


class RussianRoulette(commands.Cog):
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

    @app_commands.command(name="러시안룰렛", description="러시안룰렛을 합니다. 1~6 중 하나를 선택하세요.")
    async def russian_roulette(self, interaction: discord.Interaction, amount: int, choice: int):
        if not await self.check_game_channel(interaction):
            return

        """러시안룰렛 게임"""
        user_id = interaction.user.id

        if amount <= 0:
            await interaction.response.send_message("베팅 금액은 1LC 이상이어야 합니다.", ephemeral=True)
            return

        current_balance = await self.ensure_user(user_id)
        if current_balance < amount:
            await interaction.response.send_message("잔액이 부족합니다.", ephemeral=True)
            return

        if choice < 1 or choice > 6:
            await interaction.response.send_message("1~6 중 하나를 선택하세요.", ephemeral=True)
            return

        await interaction.response.defer()

        bullet_position = random.randint(1, 6)
        survived = bullet_position != choice
        winnings = int(amount*0.2) if survived else -amount

        self.bot.cursor.execute("UPDATE users SET money = money + %s WHERE uuid = %s", (winnings, user_id))
        self.bot.conn.commit()

        new_balance = await self.ensure_user(user_id)

        result_text = "**✅ 생존! 1.2배 획득!**" if survived else "**💀 사망! 전액 손실!**"
        color = discord.Color.green() if survived else discord.Color.red()

        embed = discord.Embed(title="🔫 러시안룰렛 결과", color=color)
        embed.add_field(name="당신이 선택한 총알 위치", value=f"{choice}/6", inline=False)
        embed.add_field(name="실제 총알 위치", value=f"{bullet_position}/6", inline=False)
        embed.add_field(name="📌 결과", value=result_text, inline=False)
        embed.set_footer(text=f"현재 잔액: {new_balance:,} LC")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RussianRoulette(bot))
