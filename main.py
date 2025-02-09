import os
import asyncio
import discord
from discord.ext import commands
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class AClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.synced = False
        self.setup_db_connection()

    async def setup_hook(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        if not self.synced:
            await self.tree.sync()
            self.synced = True
        print("✅ 준비 완료")

    async def on_ready(self):
        await self.update_status()
        print(f"✅ {self.user} 로그인 완료 | 현재 {len(self.guilds)}개 서버에서 사용 중")

    def setup_db_connection(self):
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                sslmode='prefer',
                connect_timeout=10,
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"❌ 데이터베이스 연결 오류: {e}")
            self.conn, self.cursor = None, None

    def ensure_db_connection(self):
        try:
            if not self.conn or self.conn.closed:
                print("⚠️ 데이터베이스 재연결 시도 중...")
                self.setup_db_connection()
            return self.conn is not None
        except Exception as e:
            print(f"❌ 데이터베이스 상태 확인 중 오류: {e}")
            return False

    async def update_status(self):
        while True:
            try:
                server_count = len(self.guilds)
                await self.change_presence(
                    activity=discord.Game(f"🦁 {server_count}개의 서버에서 활동 중! 🎵")
                )
                await asyncio.sleep(600)  # 10분마다 업데이트
            except Exception as e:
                print(f"❌ 상태 업데이트 오류: {e}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.update_status()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.update_status()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.user.id:
            if after.channel is None:
                await asyncio.sleep(5)
                if not any(member for member in before.channel.members if not member.bot):
                    await member.guild.voice_client.disconnect()
                    print("🛑 봇이 음성 채널에서 자동 퇴장했습니다.")

client = AClient()

try:
    client.run(os.getenv("DISCORD_TOKEN"))
except KeyboardInterrupt:
    print("🛑 봇이 중지되었습니다.")
except Exception as e:
    print(f"❌ 봇 실행 중 오류 발생: {e}")
