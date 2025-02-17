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
        self.games = {}

    async def ensure_user(self, user_id):
        self.bot.cursor.execute("SELECT money FROM users WHERE uuid = %s", (user_id,))
        user_data = self.bot.cursor.fetchone()
        if not user_data:
            self.bot.cursor.execute("INSERT INTO users (uuid, money) VALUES (%s, 10000)", (user_id,))
            self.bot.conn.commit()
            return 10000
        return user_data[0]

    def calculate_hand(self, hand):
        total = 0
        aces = 0

        for card in hand:
            if card.value == 1:
                aces += 1
            elif card.value >= 11:
                total += 10
            else:
                total += card.value

        for _ in range(aces):
            if total + 11 <= 21:
                total += 11
            else:
                total += 1

        return total

    @app_commands.command(name="블랙잭", description="블랙잭 게임을 시작합니다.")
    async def blackjack(self, interaction: discord.Interaction, amount: int):
        user_id = interaction.user.id

        if user_id in self.games:
            await interaction.response.send_message("이미 진행 중인 게임이 있습니다.", ephemeral=True)
            return

        await interaction.response.defer()

        current_balance = await self.ensure_user(user_id)
        if amount <= 0 or current_balance < amount:
            await interaction.followup.send("올바른 금액을 입력하세요.", ephemeral=True)
            return

        deck = Deck()
        player_hand = [deck.draw(), deck.draw()]
        dealer_hand = [deck.draw(), deck.draw()]

        self.games[user_id] = {
            "deck": deck,
            "player_hand": player_hand,
            "dealer_hand": dealer_hand,
            "amount": amount,
            "status": "playing",
            "message": None
        }

        view = BlackjackView(self.bot, user_id)
        await self.update_game_message(interaction, user_id, view)

    async def update_game_message(self, interaction, user_id, view):
        """기존 임베드를 수정하여 업데이트"""
        game = self.games[user_id]
        player_total = self.calculate_hand(game["player_hand"])
        dealer_first = game["dealer_hand"][0]

        embed = discord.Embed(
            title="🃏 블랙잭 게임 진행 중",
            color=discord.Color.blue()
        )
        embed.add_field(name="딜러의 패", value=f"🂠 {dealer_first}, ??", inline=False)
        embed.add_field(name="당신의 패", value=f"{', '.join(map(str, game['player_hand']))} (총합: {player_total})", inline=False)
        embed.set_footer(text=f"배팅 금액: {game['amount']:,} LC")

        if game["message"] is None:
            game["message"] = await interaction.followup.send(embed=embed, view=view)
        else:
            await game["message"].edit(embed=embed, view=view)

    async def end_game(self, interaction, user_id, reason, view):
        game = self.games.pop(user_id, None)
        if not game:
            await interaction.followup.send("게임 데이터가 없습니다.", ephemeral=True)
            return

        player_total = self.calculate_hand(game["player_hand"])
        dealer_total = self.calculate_hand(game["dealer_hand"])
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

        view.stop()

        # 기존 메시지가 없으면 새로운 메시지를 생성
        if game["message"]:
            await game["message"].edit(embed=embed, view=None)
        else:
            await interaction.followup.send(embed=embed)


class BlackjackView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="히트", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if interaction.user.id != self.user_id:
            await interaction.followup.send("이 게임에 참여할 수 없습니다.", ephemeral=True)
            return

        game = self.bot.get_cog("Blackjack").games.get(self.user_id)
        if not game or game["status"] != "playing":
            await interaction.followup.send("게임이 이미 종료되었습니다.", ephemeral=True)
            return

        game["player_hand"].append(game["deck"].draw())
        player_total = self.bot.get_cog("Blackjack").calculate_hand(game["player_hand"])

        if player_total > 21:
            await self.bot.get_cog("Blackjack").end_game(interaction, self.user_id, "bust", self)
        else:
            await self.bot.get_cog("Blackjack").update_game_message(interaction, self.user_id, self)

    @discord.ui.button(label="스탠드", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if interaction.user.id != self.user_id:
            await interaction.followup.send("이 게임에 참여할 수 없습니다.", ephemeral=True)
            return

        game = self.bot.get_cog("Blackjack").games.get(self.user_id)
        if not game or game["status"] != "playing":
            await interaction.followup.send("게임이 이미 종료되었습니다.", ephemeral=True)
            return

        # 딜러가 17 이상이 될 때까지 카드 뽑기
        while self.bot.get_cog("Blackjack").calculate_hand(game["dealer_hand"]) < 17:
            game["dealer_hand"].append(game["deck"].draw())

        await self.bot.get_cog("Blackjack").end_game(interaction, self.user_id, "stand", self)


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
