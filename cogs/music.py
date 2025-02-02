import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
from dotenv import load_dotenv
import os
import googleapiclient.discovery

load_dotenv()


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}  # 서버별 재생 대기열
        self.current_song = {}  # 현재 재생 중인 노래 정보

        # YouTube 다운로드 옵션
        self.ytdl_format_options = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'cookiefile': '/home/ubuntu/komonMusicBot/cookies.txt',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }

        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_format_options)

    async def search_youtube(self, query):
        """YouTube에서 가장 연관성 높은 영상 검색"""
        try:
            api_service_name = "youtube"
            api_version = "v3"
            api_key = os.getenv("YOUTUBE_API_KEY")  # 환경 변수에서 API 키 가져오기

            youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=api_key)

            request = youtube.search().list(
                q=query,
                part="snippet",
                maxResults=1,
                type="video"
            )
            response = request.execute()

            if not response['items']:
                return None

            video_id = response['items'][0]['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            return {
                'title': response['items'][0]['snippet']['title'],
                'url': video_url,
                'duration': 0,  # YouTube API는 duration을 직접 제공하지 않음
                'thumbnail': response['items'][0]['snippet']['thumbnails']['default']['url']
            }
        except Exception as e:
            print(f"YouTube API 검색 중 오류: {e}")
            return None

    async def get_audio_source(self, url):
        """오디오 소스 추출"""
        try:
            # 직접 다운로드되는 오디오 URL 찾기
            info = self.ytdl.extract_info(url, download=False)
            formats = info.get('formats', [])

            # 오디오 URL 찾기 (가장 높은 품질의 오디오)
            audio_url = None
            for f in formats:
                if f.get('acodec') != 'none' and f.get('url'):
                    audio_url = f['url']
                    break

            if not audio_url:
                print("적절한 오디오 URL을 찾을 수 없습니다.")
                return None

            # FFmpeg 옵션 개선
            source = await discord.FFmpegOpusAudio.from_probe(
                audio_url,
                executable=os.getenv("FFMPEG"),
                **{
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn -acodec libopus'
                }
            )
            return source
        except Exception as e:
            print(f"오디오 소스 추출 중 오류: {e}")
            return None

    async def play_next(self, ctx):
        """다음 노래 재생"""
        if not ctx.guild.id in self.queue or len(self.queue[ctx.guild.id]) == 0:
            # 대기열 비어있으면 연결 해제
            await ctx.voice_client.disconnect()
            return

        # 다음 노래 가져오기
        next_song = self.queue[ctx.guild.id].pop(0)

        try:
            audio_source = await self.get_audio_source(next_song['url'])
            if not audio_source:
                await ctx.send("오디오 소스를 가져오는 데 실패했습니다.")
                return

            ctx.voice_client.play(audio_source,
                                  after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))

            # 현재 노래 정보 업데이트
            self.current_song[ctx.guild.id] = next_song

            # 노래 시작 알림
            embed = discord.Embed(title="🎵 지금 재생 중", description=next_song['title'], color=discord.Color.blue())
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"노래 재생 중 오류: {e}")
            await ctx.send("노래를 재생하는 중 오류가 발생했습니다.")

    @app_commands.command(name="재생", description="YouTube에서 노래를 검색하여 재생합니다")
    async def play(self, interaction: discord.Interaction, query: str):
        try:
            # 디퍼드 응답
            await interaction.response.defer()

            music_settings_cog = self.bot.get_cog('GuildSetting')
            if not await music_settings_cog.check_music_channel_permission(interaction):
                await interaction.followup.send("이 채널에서는 음악 명령어를 사용할 수 없습니다.", ephemeral=True)
                return

            # 음성 채널 연결 확인
            if interaction.user.voice is None:
                await interaction.followup.send("음성 채널에 먼저 접속해주세요.")
                return

            voice_channel = interaction.user.voice.channel

            # YouTube 검색
            song = await self.search_youtube(query)
            if not song:
                await interaction.followup.send("노래를 찾을 수 없습니다.")
                return

            # 음성 채널 연결
            voice_client = interaction.guild.voice_client
            if voice_client is None:
                voice_client = await voice_channel.connect()
            elif voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)

            # 대기열 초기화
            if interaction.guild.id not in self.queue:
                self.queue[interaction.guild.id] = []

            # 노래 대기열에 추가
            self.queue[interaction.guild.id].append(song)

            # 현재 재생 중인 노래가 없으면 바로 재생
            if not voice_client.is_playing():
                # ctx 대신 interaction 전달
                await self.play_next(await self.bot.get_context(interaction))
            else:
                # 대기열에 추가됨 알림
                embed = discord.Embed(title="🎵 대기열 추가", description=song['title'], color=discord.Color.green())
                await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"재생 중 오류: {e}")
            try:
                await interaction.followup.send("노래를 재생하는 중 오류가 발생했습니다.")
            except:
                pass

    @app_commands.command(name="정지", description="현재 재생 중인 노래를 정지합니다")
    async def stop(self, interaction: discord.Interaction):
        # 음악봇 채널 권한 확인
        music_settings_cog = self.bot.get_cog('GuildSetting')
        if not await music_settings_cog.check_music_channel_permission(interaction):
            await interaction.response.send_message("이 채널에서는 음악 명령어를 사용할 수 없습니다.", ephemeral=True)
            return

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            self.queue[interaction.guild.id] = []  # 대기열 초기화
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("음악 재생을 중지하고 음성 채널에서 나갔습니다.")
        else:
            await interaction.response.send_message("현재 재생 중인 음악이 없습니다.", ephemeral=True)

    @app_commands.command(name="대기열", description="현재 음악 대기열을 확인합니다")
    async def queue_list(self, interaction: discord.Interaction):
        # 음악봇 채널 권한 확인
        music_settings_cog = self.bot.get_cog('MusicBotSettings')
        if not await music_settings_cog.check_music_channel_permission(interaction):
            await interaction.response.send_message("이 채널에서는 음악 명령어를 사용할 수 없습니다.", ephemeral=True)
            return

        if interaction.guild.id not in self.queue or len(self.queue[interaction.guild.id]) == 0:
            await interaction.response.send_message("대기열이 비어있습니다.", ephemeral=True)
            return

        # 현재 재생 중인 노래와 대기열 노래들 표시
        current = self.current_song.get(interaction.guild.id, None)
        queue = self.queue[interaction.guild.id]

        embed = discord.Embed(title="🎵 음악 대기열", color=discord.Color.blue())

        if current:
            embed.add_field(name="현재 재생 중", value=current['title'], inline=False)

        queue_text = "\n".join([f"{i + 1}. {song['title']}" for i, song in enumerate(queue)])
        embed.add_field(name="대기열", value=queue_text or "대기열이 비어있습니다.", inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))