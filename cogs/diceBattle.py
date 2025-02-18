import random
import discord
from discord import app_commands
from discord.ext import commands


class DiceBattle(commands.Cog):
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

    @app_commands.command(name="주사위배틀", description="1:1 주사위 배틀을 개최합니다.")
    async def dice_battle(self, interaction: discord.Interaction, amount: int):
        if not await self.check_game_channel(interaction):
            return

        """주사위 배틀 시작 (개최자가 먼저 베팅)"""
        user_id = interaction.user.id

        if user_id in self.games:
            await interaction.response.send_message("이미 진행 중인 배틀이 있습니다.", ephemeral=True)
            return

        current_balance = await self.ensure_user(user_id)
        if amount <= 0 or current_balance < amount:
            await interaction.response.send_message("올바른 금액을 입력하세요.", ephemeral=True)
            return

        # 개최자 주사위 굴리기 (숫자는 아직 공개되지 않음)
        host_dice = random.randint(1, 6)
        self.games[user_id] = {
            "host_id": user_id,
            "host_dice": host_dice,
            "amount": amount,
            "message": None,
            "participant_id": None,
        }

        view = DiceBattleView(self.bot, user_id, amount)
        embed = discord.Embed(title="🎲 주사위 배틀 개최!", color=discord.Color.blue())
        embed.add_field(name="개최자", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="베팅 금액", value=f"{amount:,} LC", inline=True)
        embed.add_field(name="참가 방법", value="아래 버튼을 눌러 참여하세요! (선착순 1명)", inline=False)
        embed.set_footer(text="참가자가 주사위를 굴리면 결과가 공개됩니다.")

        message = await interaction.response.send_message(embed=embed, view=view)
        self.games[user_id]["message"] = message


class DiceBattleView(discord.ui.View):
    def __init__(self, bot, host_id, amount):
        super().__init__(timeout=60)
        self.bot = bot
        self.host_id = host_id
        self.amount = amount

    @discord.ui.button(label="주사위 굴리기", style=discord.ButtonStyle.primary)
    async def roll_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        """참가자가 버튼을 눌러 주사위를 굴림"""
        await interaction.response.defer()  # ✅ 응답 지연 (필수)

        game = self.bot.get_cog("DiceBattle").games.get(self.host_id)

        if not game:
            await interaction.followup.send("이 배틀은 종료되었거나 존재하지 않습니다.", ephemeral=True)
            return

        user_id = interaction.user.id

        if user_id == self.host_id:
            await interaction.followup.send("자신이 개최한 배틀에는 참가할 수 없습니다.", ephemeral=True)
            return

        # 중복 참가 방지 (선착순 1명만 가능)
        if game["participant_id"]:
            await interaction.followup.send("이미 다른 참가자가 참여했습니다.", ephemeral=True)
            return

        # 참가자의 잔액 확인
        current_balance = await self.bot.get_cog("DiceBattle").ensure_user(user_id)
        if current_balance < game["amount"]:
            await interaction.followup.send("베팅 금액이 부족하여 참여할 수 없습니다.", ephemeral=True)
            return

        # 참가자 등록 및 주사위 굴리기
        game["participant_id"] = user_id
        player_dice = random.randint(1, 6)

        # 게임 결과 계산
        host_dice = game["host_dice"]
        amount = game["amount"]

        if player_dice > host_dice:
            winner = user_id
            loser = self.host_id
            result = f"{interaction.user.mention} 님이 승리했습니다!"
            color = discord.Color.green()
        elif player_dice < host_dice:
            winner = self.host_id
            loser = user_id
            result = f"<@{self.host_id}> 님이 승리했습니다!"
            color = discord.Color.red()
        else:
            winner = None
            loser = None
            result = "무승부입니다!"
            color = discord.Color.gold()

        # DB 업데이트
        if winner:
            self.bot.cursor.execute("UPDATE users SET money = money + %s WHERE uuid = %s", (amount, winner))
            self.bot.cursor.execute("UPDATE users SET money = money - %s WHERE uuid = %s", (amount, loser))
        self.bot.conn.commit()

        # 결과 임베드 생성
        embed = discord.Embed(title="🎲 주사위 배틀 결과", color=color)
        embed.add_field(name="개최자 주사위", value=f"🎲 {host_dice}", inline=True)
        embed.add_field(name="참가자 주사위", value=f"🎲 {player_dice}", inline=True)
        embed.add_field(name="결과", value=result, inline=False)
        embed.set_footer(text=f"배팅 금액: {amount:,} LC")

        # 기존 메시지 수정 전에 None 체크
        if game["message"]:
            await game["message"].edit(embed=embed, view=None)  # ✅ 기존 메시지를 수정
        else:
            await interaction.followup.send(embed=embed)  # ✅ 기존 메시지가 없으면 새로 생성

        # 게임 종료
        self.bot.get_cog("DiceBattle").games.pop(self.host_id, None)


async def setup(bot):
    await bot.add_cog(DiceBattle(bot))
