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

        # YouTube 다운로드 옵션
        self.ytdl_format_options = {
            'format': 'bestaudio[ext=webm]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',  # opus 코덱 사용
                'preferredquality': '192',  # 비트레이트 조정
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

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        # 봇이 강제로 연결이 끊겼는지 확인
        if member.id == self.bot.user.id and before.channel and not after.channel:
            # 봇이 음성 채널에서 나갔을 때
            guild_id = before.channel.guild.id
            if guild_id in self.queue:
                # 대기열 초기화
                self.queue[guild_id] = []
                self.current_song.pop(guild_id, None)
                print(f"봇이 강제로 연결이 끊겼습니다. 대기열을 초기화했습니다. (서버 ID: {guild_id})")

    async def get_spotify_playlist_tracks(self, playlist_url):
        """스포티파이 플레이리스트의 트랙 목록 가져오기"""
        try:
            # 플레이리스트 ID 추출
            playlist_id = playlist_url.split("/")[-1].split("?")[0]

            # 플레이리스트 트랙 목록 가져오기 (최대 50개로 제한)
            results = self.spotify.playlist_tracks(playlist_id, limit=50)
            tracks = results['items']

            # 트랙 제목과 아티스트 이름 추출
            track_list = []
            for track in tracks:
                track_name = track['track']['name']
                artist_name = track['track']['artists'][0]['name']
                track_list.append(f"{track_name} {artist_name}")

            return track_list
        except Exception as e:
            print(f"스포티파이 플레이리스트 처리 중 오류: {e}")
            return None

    async def search_youtube(self, query):
        """yt-dlp를 사용하여 YouTube에서 비디오 검색"""
        # 유튜브 링크인지 확인 (예: https://www.youtube.com/watch?v=...)
        if query.startswith("https://www.youtube.com/watch?v=") or query.startswith("https://youtu.be/"):
            # 링크인 경우, 해당 링크를 그대로 사용
            video_url = query
            try:
                # 영상 정보 추출
                info = self.ytdl.extract_info(video_url, download=False)
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'url': video_url,
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', '')
                }
            except Exception as e:
                print(f"유튜브 링크 처리 중 오류: {e}")
                return None
        else:
            # 텍스트인 경우, yt-dlp를 사용하여 검색
            ydl_opts = {
                'format': 'bestaudio/best',
                'default_search': 'ytsearch1',  # 첫 번째 결과만 가져오기
                'quiet': True,  # 로그 출력 방지
                'extract_flat': False,  # 전체 정보 추출
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    if not info or 'entries' not in info or not info['entries']:
                        print("검색 결과가 없습니다.")
                        return None

                    # 첫 번째 결과 가져오기
                    video = info['entries'][0]
                    print(f"검색 결과: {video}")  # 디버깅용 로그
                    return {
                        'title': video.get('title', 'Unknown Title'),
                        'url': video.get('url', ''),
                        'duration': video.get('duration', 0),
                        'thumbnail': video.get('thumbnail', '')
                    }
            except Exception as e:
                print(f"yt-dlp 검색 중 오류: {e}")
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
                    'options': '-vn -acodec libopus -b:a 192k'  # 비트레이트 조정
                }
            )
            return source
        except Exception as e:
            print(f"오디오 소스 추출 중 오류: {e}")
            return None

    async def play_next(self, ctx):
        """다음 노래 재생"""
        if ctx.voice_client is None:  # 봇이 음성 채널에 연결되어 있지 않으면 종료
            print("봇이 음성 채널에 연결되어 있지 않습니다.")
            return

        if not ctx.guild.id in self.queue or len(self.queue[ctx.guild.id]) == 0:
            # 대기열 비어있으면 연결 해제
            await ctx.voice_client.disconnect()
            return

        # 다음 노래 가져오기
        next_song = self.queue[ctx.guild.id].pop(0)

        try:
            # 현재 재생 중인 오디오가 있다면 중지
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
                await asyncio.sleep(1)  # 잠시 대기

            audio_source = await self.get_audio_source(next_song['url'])
            if not audio_source:
                await ctx.send("오디오 소스를 가져오는 데 실패했습니다.", ephemeral=True)
                return

            # after 콜백을 사용하여 다음 노래 재생
            ctx.voice_client.play(audio_source,
                                  after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))

            # 현재 노래 정보 업데이트
            self.current_song[ctx.guild.id] = next_song

            # 노래 시작 알림
            embed = discord.Embed(title="🎵 지금 재생 중", description=next_song['title'], color=discord.Color.blue())
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"노래 재생 중 오류: {e}")
            await ctx.send("노래를 재생하는 중 오류가 발생했습니다.", ephemeral=True)

    @app_commands.command(name="재생", description="YouTube 또는 스포티파이 플레이리스트에서 노래를 재생합니다")
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
                await interaction.followup.send("음성 채널에 먼저 접속해주세요.", ephemeral=True)
                return

            voice_channel = interaction.user.voice.channel

            # 스포티파이 플레이리스트인지 확인
            if "open.spotify.com/playlist" in query:
                # 스포티파이 플레이리스트 트랙 목록 가져오기
                await interaction.followup.send("스포티파이는 현재 개발 중입니다.", ephemeral=True)
                return
                track_list = await self.get_spotify_playlist_tracks(query)
                if not track_list:
                    await interaction.followup.send("스포티파이 플레이리스트를 처리하는 중 오류가 발생했습니다.", ephemeral=True)
                    return

                # 각 트랙을 YouTube에서 검색하여 대기열에 추가
                for track in track_list:
                    song = await self.search_youtube(track)
                    if song:
                        if interaction.guild.id not in self.queue:
                            self.queue[interaction.guild.id] = []
                        self.queue[interaction.guild.id].append(song)
                        await asyncio.sleep(1)  # 트랙 간 간격 추가

                # 현재 재생 중인 노래가 없으면 바로 재생
                voice_client = interaction.guild.voice_client
                if voice_client is None:
                    voice_client = await voice_channel.connect()
                elif voice_client.channel != voice_channel:
                    await voice_client.move_to(voice_channel)

                if not voice_client.is_playing():
                    await self.play_next(await self.bot.get_context(interaction))

                # 플레이리스트 추가 완료 알림
                await interaction.followup.send(f"플레이리스트에 {len(track_list)}개의 노래가 추가되었습니다.", ephemeral=True)
                return

            # YouTube 검색 또는 링크 처리
            song = await self.search_youtube(query)
            if not song:
                await interaction.followup.send("노래를 찾을 수 없습니다.", ephemeral=True)
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
                await self.play_next(await self.bot.get_context(interaction))
            else:
                # 대기열에 추가됨 알림
                embed = discord.Embed(title="🎵 대기열 추가", description=song['title'], color=discord.Color.green())
                await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"재생 중 오류: {e}")
            try:
                await interaction.followup.send("노래를 재생하는 중 오류가 발생했습니다.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="정지", description="현재 재생 중인 노래를 정지합니다")
    async def stop(self, interaction: discord.Interaction):
        # 음악봇 채널 권한 확인
        music_settings_cog = self.bot.get_cog('GuildSetting')
        if not await music_settings_cog.check_music_channel_permission(interaction):
            await interaction.response.send_message("이 채널에서는 음악 명령어를 사용할 수 없습니다.", ephemeral=True)
            return

        await interaction.response.defer()  # 인터랙션 지연

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            self.queue[interaction.guild.id] = []  # 대기열 초기화
            await interaction.guild.voice_client.disconnect()
            await interaction.followup.send("음악 재생을 중지하고 음성 채널에서 나갔습니다.", ephemeral=True)
        else:
            await interaction.followup.send("현재 재생 중인 음악이 없습니다.", ephemeral=True)

    @app_commands.command(name="스킵", description="현재 재생 중인 노래를 스킵합니다")
    async def skip(self, interaction: discord.Interaction):
        # 음악봇 채널 권한 확인
        music_settings_cog = self.bot.get_cog('GuildSetting')
        if not await music_settings_cog.check_music_channel_permission(interaction):
            await interaction.response.send_message("이 채널에서는 음악 명령어를 사용할 수 없습니다.", ephemeral=True)
            return

        await interaction.response.defer()  # 인터랙션 지연

        voice_client = interaction.guild.voice_client
        if voice_client is None or not voice_client.is_connected():
            await interaction.followup.send("봇이 음성 채널에 연결되어 있지 않습니다.", ephemeral=True)
            return

        if voice_client.is_playing():
            voice_client.stop()
            await interaction.followup.send("현재 재생 중인 노래를 스킵했습니다.", ephemeral=True)
        else:
            await interaction.followup.send("현재 재생 중인 음악이 없습니다.", ephemeral=True)

    @app_commands.command(name="대기열", description="현재 음악 대기열을 확인합니다")
    async def queue_list(self, interaction: discord.Interaction):
        # 음악봇 채널 권한 확인
        music_settings_cog = self.bot.get_cog('GuildSetting')
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