import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import pytz
import asyncio
import os

intents = discord.Intents.default()
client = commands.Bot(command_prefix="/", intents=intents)

target_time = None
mention_role = None
channel_id = None
countdown_started = False

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@client.tree.command(name="targettime")
@app_commands.describe(time="Horário alvo no formato HH:MM:SS (UTC-3)")
async def set_target_time(interaction: discord.Interaction, time: str):
    global target_time
    try:
        now = datetime.now(pytz.timezone("America/Sao_Paulo"))
        hour, minute, second = map(int, time.split(":"))
        target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        if target_time < now:
            target_time += timedelta(days=1)
        await interaction.response.send_message(f"🤖 TargetTime definida para: {target_time.strftime('%H:%M:%S')} (UTC-3)", ephemeral=False)
    except:
        await interaction.response.send_message("Formato inválido. Use HH:MM:SS", ephemeral=True)

@client.tree.command(name="mentions")
@app_commands.describe(role="Mencione o grupo ou pessoa (ex: @everyone ou @user)")
async def set_mentions(interaction: discord.Interaction, role: str):
    global mention_role
    mention_role = role
    await interaction.response.send_message(f"🤖 Mentions definida para: {mention_role}", ephemeral=False)

@client.tree.command(name="channel")
@app_commands.describe(channel="Canal onde o countdown será exibido")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global channel_id
    channel_id = channel.id
    await interaction.response.send_message(f"🤖 Channel definido para: {channel.mention}", ephemeral=False)

@client.tree.command(name="start")
async def start_countdown(interaction: discord.Interaction):
    global countdown_started
    if not all([target_time, mention_role, channel_id]):
        missing = []
        if not target_time:
            missing.append("TargetTime")
        if not mention_role:
            missing.append("Mentions")
        if not channel_id:
            missing.append("Channel")
        await interaction.response.send_message(f"🤖 O(s) campos {', '.join(missing)} ainda não foram definidos! Defina-os antes de iniciar o bot!", ephemeral=False)
        return

    if countdown_started:
        await interaction.response.send_message("O countdown já foi iniciado.", ephemeral=True)
        return

    countdown_started = True
    channel = client.get_channel(channel_id)
    await interaction.response.send_message(
        f"🤖 Bot iniciado! Assim que faltar 1 hora para o termino do bid, que será {target_time.strftime('%H:%M:%S')} (UTC-3), irei:\n"
        f"✅ Notificar {mention_role} no canal {channel.mention} a cada 5 minutos.\n"
        f"✅ Quando faltar 1 minuto para o término do bid, o countdown será segundo a segundo.",
        ephemeral=False
    )
    client.loop.create_task(countdown_loop())

@client.tree.command(name="stop")
@app_commands.describe(reason="(Opcional) Motivo para parar o countdown")
async def stop_countdown(interaction: discord.Interaction, reason: str = "sem motivo especificado"):
    global countdown_started
    if countdown_started:
        countdown_started = False
        await interaction.response.send_message(f"🛑 Countdown interrompido manualmente. Motivo: {reason}")
    else:
        await interaction.response.send_message("🤖 Nenhum countdown está ativo no momento.", ephemeral=True)

async def countdown_loop():
    global countdown_started
    channel = client.get_channel(channel_id)
    tz = pytz.timezone("America/Sao_Paulo")

    aviso_10s = [50, 40, 30, 20, 10]

    while countdown_started:
        now = datetime.now(tz)
        diff = target_time - now
        total_seconds = int(diff.total_seconds())

        if diff <= timedelta(hours=1) and diff > timedelta(minutes=1):
            if diff.seconds % 300 < 5:
                mins = diff.seconds // 60
                await channel.send(f"{mention_role} Faltam {mins} minutos para o bid encerrar.")
                await asyncio.sleep(300 - (diff.seconds % 300))
            else:
                await asyncio.sleep(1)

        elif 60 >= total_seconds > 10:
            if total_seconds == 60:
                await channel.send(f"{mention_role} Faltam 1 minuto para o bid encerrar.")
            elif total_seconds in aviso_10s:
                await channel.send(f"{mention_role} Faltam {total_seconds} segundos para o bid encerrar.")
            await asyncio.sleep(1)

        elif 10 >= total_seconds > 0:
            await channel.send(f"{mention_role} Faltam {total_seconds} segundos para o bid encerrar.")
            await asyncio.sleep(1)

        elif total_seconds <= 0:
            await channel.send(f"{mention_role} O bid encerrou agora!")
            countdown_started = False
            break

        else:
            await asyncio.sleep(1)

client.run(os.environ['YOUR_BOT_TOKEN'])
