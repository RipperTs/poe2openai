import asyncio
import fastapi_poe as fp


# Create an asynchronous function to encapsulate the async for loop
async def get_responses(api_key, messages):
    async for partial in fp.get_bot_response(messages=messages, bot_name="GPT-3.5-Turbo", api_key=api_key):
        print(partial)


# Replace <api_key> with your actual API key, ensuring it is a string.
api_key = "zhL4vaN8oMCDffMxiFeDkNRYEaqhJcxNmI5-OUV8Kgw"
message = fp.ProtocolMessage(role="user", content="Hello world")

# Run the event loop
# For Python 3.7 and newer
asyncio.run(get_responses(api_key, [message]))

# For Python 3.6 and older, you would typically do the following:
# loop = asyncio.get_event_loop()
# loop.run_until_complete(get_responses(api_key))
# loop.close()