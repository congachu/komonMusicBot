import random
import discord
from discord import app_commands
from discord.ext import commands


class Card:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __str__(self):
        suits = {'hearts': '♥', 'diamonds': '♦', 'clubs': '♣', 'spades': '♠'}
        values = {1: 'A', 11: 'J', 12: 'Q', 13: 'K', **{i: str(i) for i in range(2, 11)}}
        return f"{suits[self.suit]}{values[self.value]}"


class Deck:
    def __init__(self):
        self.cards = [Card(suit, value) for suit in ['hearts', 'diamonds', 'clubs', 'spades'] for value in range(1, 14)]
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop()


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # 진행 중인 게임 저장

    async def ensure_user(self, user_id):
        """유저가 존재하는지 확인 후 없으면 추가"""
        self.bot.cursor.execute("SELECT money FROM users WHERE uuid = %s", (user_id,))
        user_data = self.bot.cursor.fetchone()
        if not user_data:
            self.bot.cursor.execute("INSERT INTO users (uuid, money) VALUES (%s, 1000)", (user_id,))
            self.bot.conn.commit()
            return 1000
        return user_data[0]

    async def check_game_channel(self, interaction):
        """게임 채널에서만 실행되도록 확인"""
        settings_cog = self.bot.get_cog("GuildSetting")
        if settings_cog and not await settings_cog.check_channel_permission(interaction, "game"):
            await interaction.response.send_message("이 채널에서는 게임 명령어를 사용할 수 없습니다.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="블랙잭", description="블랙잭 게임을 시작합니다.")
    async def blackjack(self, interaction: discord.Interaction, amount: int):
        """블랙잭 게임 시작"""
        if not await self.check_game_channel(interaction):
            return

        user_id = interaction.user.id
        if user_id in self.games:
            await interaction.response.send_message("이미 진행 중인 게임이 있습니다. 현재 게임을 완료해주세요.", ephemeral=True)
            return

        await interaction.response.defer()

        current_balance = await self.ensure_user(user_id)
        if amount <= 0 or current_balance < amount:
            await interaction.followup.send("올바른 금액을 입력하세요.", ephemeral=True)
            return

        deck = [i for i in range(1, 14)] * 4
        random.shuffle(deck)

        player_hand, dealer_hand = [deck.pop(), deck.pop()], [deck.pop(), deck.pop()]
        self.games[user_id] = {
            "deck": deck,
            "player_hand": player_hand,
            "dealer_hand": dealer_hand,
            "amount": amount,
            "message": None  # 메시지 저장
        }

        view = self.create_game_buttons(interaction)
        message = await self.update_game_message(interaction, user_id, view)
        self.games[user_id]["message"] = message  # 메시지 저장

    def create_game_buttons(self, interaction):
        """버튼 뷰 생성"""
        view = discord.ui.View()
        user_id = interaction.user.id

        hit_button = discord.ui.Button(label="히트", style=discord.ButtonStyle.primary)
        stand_button = discord.ui.Button(label="스탠드", style=discord.ButtonStyle.secondary)

        async def hit_callback(interaction: discord.Interaction):
            if user_id not in self.games:
                return await interaction.response.send_message("진행 중인 게임이 없습니다.", ephemeral=True)

            await interaction.response.defer()
            game = self.games[user_id]
            game["player_hand"].append(game["deck"].pop())

            if sum(game["player_hand"]) > 21:
                await self.end_game(interaction, user_id, "bust")
            else:
                await self.update_game_message(interaction, user_id, view)

        async def stand_callback(interaction: discord.Interaction):
            if user_id not in self.games:
                return await interaction.response.send_message("진행 중인 게임이 없습니다.", ephemeral=True)

            await interaction.response.defer()
            game = self.games[user_id]
            while sum(game["dealer_hand"]) < 17:
                game["dealer_hand"].append(game["deck"].pop())

            await self.end_game(interaction, user_id, "stand")

        hit_button.callback = hit_callback
        stand_button.callback = stand_callback
        view.add_item(hit_button)
        view.add_item(stand_button)

        return view

    async def update_game_message(self, interaction, user_id, view=None):
        """게임 상태 업데이트 (임베드 메시지)"""
        game = self.games[user_id]
        player_total = sum(game["player_hand"])
        dealer_first = game["dealer_hand"][0]

        embed = discord.Embed(
            title="🃏 블랙잭 게임 진행 중",
            color=discord.Color.blue()
        )
        embed.add_field(name="딜러의 패", value=f"🂠 {dealer_first}, ??", inline=False)
        embed.add_field(name="당신의 패", value=f"{', '.join(map(str, game['player_hand']))} (총합: {player_total})", inline=False)
        embed.set_footer(text=f"배팅 금액: {game['amount']:,} LC")

        if game["message"] is None:
            return await interaction.followup.send(embed=embed, view=view)
        else:
            await game["message"].edit(embed=embed, view=view)

    async def end_game(self, interaction, user_id, reason):
        """게임 종료 및 결과 처리 (임베드 메시지)"""
        game = self.games.pop(user_id, None)
        if not game:
            return await interaction.followup.send("게임 데이터가 없습니다.", ephemeral=True)

        player_total = sum(game["player_hand"])
        dealer_total = sum(game["dealer_hand"])
        amount = game["amount"]
        winnings = 0

        if reason == "bust":
            result = "패배 (21 초과)"
            color = discord.Color.red()
            winnings = -amount
        else:
            if player_total > 21:
                result = "패배 (21 초과)"
                color = discord.Color.red()
                winnings = -amount
            elif dealer_total > 21 or player_total > dealer_total:
                result = "🎉 승리!"
                color = discord.Color.green()
                winnings = amount
            elif player_total < dealer_total:
                result = "패배"
                color = discord.Color.red()
                winnings = -amount
            else:
                result = "무승부"
                color = discord.Color.gold()

        self.bot.cursor.execute("UPDATE users SET money = money + %s WHERE uuid = %s", (winnings, user_id))
        self.bot.conn.commit()

        new_balance = await self.ensure_user(user_id)
        dealer_cards = ", ".join(str(c) for c in game["dealer_hand"])
        player_cards = ", ".join(str(c) for c in game["player_hand"])

        embed = discord.Embed(title="🎰 블랙잭 게임 종료", color=color)
        embed.add_field(name="딜러의 패", value=f"{dealer_cards} (총합: {dealer_total})", inline=False)
        embed.add_field(name="당신의 패", value=f"{player_cards} (총합: {player_total})", inline=False)
        embed.add_field(name="결과", value=result, inline=False)
        embed.set_footer(text=f"현재 잔액: {new_balance:,} LC")

        if game["message"]:
            await game["message"].edit(embed=embed, view=None)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
