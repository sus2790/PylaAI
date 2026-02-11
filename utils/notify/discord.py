"""Discord webhook notification utilities."""
from typing import Optional
import io
import aiohttp
import discord
from discord import Webhook
from PIL import Image

from utils.config.loader import load_toml_as_dict


async def async_notify_user(
    message_type: Optional[str] = None,
    screenshot: Optional[Image.Image] = None
) -> None:
    """
    Send a Discord notification with optional screenshot.

    Args:
        message_type: Type of message ("completed", "bot_is_stuck", or brawler name)
        screenshot: Optional PIL Image to attach
    """
    config = load_toml_as_dict("cfg/general_config.toml")
    user_id = config.get("discord_id", "")
    webhook_url = config.get("personal_webhook", "")

    if not webhook_url:
        print("Couldn't notify: no webhook configured.")
        return

    if message_type == "completed":
        status_line = "Pyla has completed all its targets!"
        ping = f"<@{user_id}>"
    elif message_type == "bot_is_stuck":
        status_line = "Your bot is currently stuck!"
        ping = f"<@{user_id}>"
    else:
        status_line = f"Pyla completed brawler goal for {message_type}!"
        ping = f"<@{user_id}>"

    if screenshot is None:
        # Send text-only message
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, session=session)
            await webhook.send(content=f"{ping}\n{status_line}", username="Pyla notifier")
        return

    buffer = io.BytesIO()
    screenshot.save(buffer, format="PNG")
    buffer.seek(0)
    file = discord.File(buffer, filename="screenshot.png")

    embed = discord.Embed(description=status_line)
    embed.set_image(url="attachment://screenshot.png")

    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(webhook_url, session=session)
        print("Sending webhook")
        await webhook.send(embed=embed, file=file, username="Pyla notifier", content=ping)


class DiscordNotifier:
    """Wrapper for Discord notification functionality."""

    def __init__(self, config_path: str = "cfg/general_config.toml") -> None:
        self.config_path = config_path

    async def send_completion_notification(
        self,
        screenshot: Optional[Image.Image] = None
    ) -> None:
        """Send notification that all targets are completed."""
        await async_notify_user("completed", screenshot)

    async def send_stuck_notification(
        self,
        screenshot: Optional[Image.Image] = None
    ) -> None:
        """Send notification that the bot is stuck."""
        await async_notify_user("bot_is_stuck", screenshot)

    async def send_brawler_notification(
        self,
        brawler_name: str,
        screenshot: Optional[Image.Image] = None
    ) -> None:
        """Send notification for brawler goal completion."""
        await async_notify_user(brawler_name, screenshot)
