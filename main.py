import os
import discord
from discord.ext import commands
from discord import Activity, ActivityType
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class AClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.synced = False
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST")
        )
        self.cursor = self.conn.cursor()

    async def setup_hook(self):
        # cogs 폴더 내 모든 .py 파일을 로드합니다.
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")  # .py 확장자 제거
        if not self.synced:  # 명령어를 한 번만 동기화
            await self.tree.sync()
            self.synced = True
        print("준비 완료")

    async def on_ready(self):
        server_count = len(self.guilds)  # 현재 봇이 가입된 서버 개수
        await self.change_presence(
            activity=discord.Game(f"🦁 {server_count}개의 서버에서 활동 중! 🎵")
        )
        print(f"{self.user}로 로그인 완료 | 현재 {server_count}개 서버에서 사용 중")

    def close_db(self):
        self.cursor.close()
        self.conn.close()

client = AClient()

@client.event
async def on_close():
    client.close_db()

async def update_status():
    server_count = len(client.guilds)
    await client.change_presence(
        activity=discord.Game(f"🦁 {server_count}개의 서버에서 활동 중! 🎵")
    )

@client.event
async def on_guild_join(guild):
    await update_status()

@client.event
async def on_guild_remove(guild):
    await update_status()

@client.event
async def on_voice_state_update(member, before, after):
    if member.id == client.user.id:  # 봇 자신인지 확인
        if after.channel and not before.channel:  # 음성 채널에 새로 들어간 경우
            await member.edit(deafen=True)  # 헤드셋 끄기 (소리 듣기 차단)

# 봇 실행
try:
    client.run(os.getenv("DISCORD_TOKEN"))
except Exception as e:
    print(f"봇 실행 중 오류 발생: {e}")