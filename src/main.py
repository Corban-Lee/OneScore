"""Entry point for the application script"""

import asyncio

from bot import Bot

async def main():
    """Main entry point for the application"""

    # Grab the bot token from the token file
    with open('TOKEN', 'r', encoding='utf-8') as file:
        token = file.read()

    async with Bot() as bot:
        await bot.load_extension_from_file('bot.levels')
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
