import asyncio
import discord
from discord.ext import commands
from discord import app_commands, VoiceState, Member
import yt_dlp
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}  # 서버별 재생 대기열
        self.current_song = {}  # 현재 재생 중인 노래 정보

        # Spotify API 설정
        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
            )
        )

        # YouTube 다운로드 옵션 최적화
        self.ytdl_format_options = {
            'format': 'bestaudio[ext=webm]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'cookiefile': os.getenv("YTDL_COOKIE_FILE", "./cookies.txt"),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }

        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_format_options)

    async def search_youtube(self, query):
        """yt-dlp를 사용하여 YouTube에서 비디오 검색 (속도 개선)"""
        try:
            info = self.ytdl.extract_info(query, download=False)
            if 'entries' in info:
                video = info['entries'][0]
            else:
                video = info

            return {
                'title': video.get('title', 'Unknown Title'),
                'url': video.get('url', ''),
                'duration': video.get('duration', 0),
                'thumbnail': video.get('thumbnail', '')
            }
        except Exception as e:
            print(f"YouTube 검색 중 오류 발생: {e}")
            return None

    async def get_audio_source(self, url):
        """YouTube URL에서 오디오 소스를 추출"""
        try:
            info = self.ytdl.extract_info(url, download=False)
            audio_url = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), None)
            if not audio_url:
                print("오디오 URL을 찾을 수 없습니다.")
                return None

            return discord.FFmpegOpusAudio(audio_url, executable="ffmpeg", before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
        except Exception as e:
            print(f"오디오 소스 추출 중 오류 발생: {e}")
            return None

    async def play_next(self, ctx):
        """다음 노래 재생 및 메시지 업데이트"""
        if ctx.guild.id not in self.queue or not self.queue[ctx.guild.id]:
            await ctx.send("🎵 대기열이 비어 있습니다. 3분 동안 새로운 곡이 추가되지 않으면 퇴장합니다.")
            await asyncio.sleep(180)  # 3분 대기

            # 3분 후에도 여전히 대기열이 비어 있고, 재생 중이지 않다면 퇴장
            if ctx.guild.id not in self.queue or not self.queue[ctx.guild.id]:
                if ctx.guild.voice_client and not ctx.guild.voice_client.is_playing():
                    await ctx.voice_client.disconnect()
                    await ctx.send("🔇장시간 미사용으로 음성 채널을 떠났습니다.")
            return

        next_song = self.queue[ctx.guild.id].pop(0)
        audio_source = await self.get_audio_source(next_song['url'])
        if not audio_source:
            await self.play_next(ctx)
            return

        ctx.voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
        self.current_song[ctx.guild.id] = next_song

        embed = discord.Embed(title="🎵 지금 재생 중", description=next_song['title'], color=discord.Color.blue())
        embed.set_thumbnail(url=next_song['thumbnail'])
        await ctx.send(embed=embed)

    async def check_music_channel(self, interaction):
        """음악 명령어가 올바른 채널에서 실행되는지 확인"""
        settings_cog = self.bot.get_cog("GuildSetting")
        if settings_cog and not await settings_cog.check_music_channel_permission(interaction):
            await interaction.response.send_message("이 채널에서는 음악 명령어를 사용할 수 없습니다.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="재생", description="YouTube에서 노래를 재생합니다")
    async def play(self, interaction: discord.Interaction, query: str):
        if not await self.check_music_channel(interaction):
            return

        await interaction.response.defer()

        if interaction.user.voice is None:
            await interaction.followup.send("음성 채널에 먼저 접속해주세요.", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

        song = await self.search_youtube(query)
        if not song:
            await interaction.followup.send("노래를 찾을 수 없습니다.", ephemeral=True)
            return

        if interaction.guild.id not in self.queue:
            self.queue[interaction.guild.id] = []

        self.queue[interaction.guild.id].append(song)

        if not voice_client.is_playing():
            await self.play_next(await self.bot.get_context(interaction))
        else:
            embed = discord.Embed(title="🎵 대기열 추가", description=song['title'], color=discord.Color.green())
            embed.set_thumbnail(url=song['thumbnail'])
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="정지", description="현재 재생 중인 노래를 정지합니다")
    async def stop(self, interaction: discord.Interaction):
        if not await self.check_music_channel(interaction):
            return

        await interaction.response.defer()

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            self.queue[interaction.guild.id] = []
            await interaction.guild.voice_client.disconnect()
            await interaction.followup.send_message("음악 재생을 중지하고 음성 채널에서 나갔습니다.")
        else:
            await interaction.followup.send_message("현재 재생 중인 음악이 없습니다.", ephemeral=True)

    @app_commands.command(name="스킵", description="현재 재생 중인 노래를 스킵합니다")
    async def skip(self, interaction: discord.Interaction):
        if not await self.check_music_channel(interaction):
            return

        await interaction.response.defer()

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.followup.send_message("현재 재생 중인 노래를 스킵했습니다.")
        else:
            await interaction.followup.send_message("현재 재생 중인 음악이 없습니다.", ephemeral=True)

    @app_commands.command(name="대기열", description="현재 음악 대기열을 확인합니다")
    async def queue_list(self, interaction: discord.Interaction):
        if not await self.check_music_channel(interaction):
            return

        await interaction.response.defer()

        if interaction.guild.id not in self.queue or not self.queue[interaction.guild.id]:
            await interaction.response.send_message("대기열이 비어있습니다.", ephemeral=True)
            return

        embed = discord.Embed(title="🎵 음악 대기열", color=discord.Color.blue())
        queue_text = "\n".join([f"{i + 1}. {song['title']}" for i, song in enumerate(self.queue[interaction.guild.id])])
        embed.add_field(name="대기열", value=queue_text or "대기열이 비어있습니다.", inline=False)
        await interaction.followup.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))
