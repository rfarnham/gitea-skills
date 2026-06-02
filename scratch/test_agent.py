import asyncio
from google.antigravity import Agent, LocalAgentConfig

async def main():
    config = LocalAgentConfig(
        system_instructions="You are a helpful assistant.",
    )
    async with Agent(config) as agent:
        resp = await agent.chat("Hello! Can you hear me?")
        print(await resp.text())

if __name__ == "__main__":
    asyncio.run(main())
