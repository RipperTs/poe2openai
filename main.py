import os
import time
import uuid
import uvicorn
import json

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import AsyncGenerator
from fastapi_poe.types import ProtocolMessage
from fastapi_poe.client import get_bot_response, stream_request_base
import fastapi_poe as fp
import httpx
from dotenv import load_dotenv

app = FastAPI()
load_dotenv()

DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "GPT-3.5-Turbo")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", default=9881))
BASE_URL = os.environ.get("BASE_URL", default="https://api.poe.com/bot/")


def openai_format_messages_to_poe_format(openai_format_messages: list) -> list:
    """Convert OpenAI formatted messages to POE formatted messages."""
    poe_format_messages = [
        # Convert 'assistant' to 'bot' or we get an error
        ProtocolMessage(
            role=msg["role"].lower().replace("assistant", "bot"),
            content=msg["content"]
        )
        for msg in openai_format_messages
    ]
    return poe_format_messages


async def get_poe_bot_stream_partials(
        api_key: str, poe_format_messages: list, bot_name: str,
        temperature: float,
        tools_dict_list: list
) -> AsyncGenerator[str, None]:
    # 构建工具列表
    tools = [fp.ToolDefinition(**tools_dict) for tools_dict in tools_dict_list]
    print(tools)
    # 构建查询请求
    request = fp.QueryRequest(query=poe_format_messages,
                              user_id="aikey-wslmf",
                              message_id=str(uuid.uuid4()),
                              temperature=temperature,
                              skip_system_prompt=False,
                              metadata="")
    print(request)
    async for partial in stream_request_base(
            request=request,
            bot_name=bot_name,
            api_key=api_key,
            base_url=BASE_URL,
            tools=tools
    ):
        print(partial)
        yield partial.text


async def stream_partials_to_openai_stream_response(
        poe_bot_stream_partials: AsyncGenerator[str, None],
        bot_name: str
) -> AsyncGenerator[str, None]:
    # Create a base response template
    openai_stream_response_template = {
        "id": str(uuid.uuid4()),
        "object": "chat.completion.chunk",
        "created": time.time(),
        "model": bot_name,
        "choices": [
            {
                "index": 0,
                "delta": {
                    "content": "",  # Placeholder, to be filled for each partial response
                    "logprobs": None,
                    "finish_reason": None,
                },
            }
        ],
    }

    async for partial in poe_bot_stream_partials:
        # Fill the required field for this partial response
        openai_stream_response_template["choices"][0]["delta"]["content"] = partial

        # Create the SSE formatted string, and then yield
        yield f"data: {json.dumps(openai_stream_response_template)}\n\n"

    # Termination sequence
    openai_stream_response_template["choices"][0]["delta"] = {}  # Empty 'delta' field

    # Set 'finish_reason' to 'stop'
    openai_stream_response_template["choices"][0]["finish_reason"] = "stop"
    yield f"data: {json.dumps(openai_stream_response_template)}\n\ndata: [DONE]\n\n"


async def stream_partials_to_openai_nonstream_response(
        poe_bot_stream_partials: AsyncGenerator[str, None],
        bot_name: str
) -> dict:
    openai_nonstream_response_template = {
        "id": str(uuid.uuid4()),
        "object": "chat.completion",
        "created": time.time(),
        "model": bot_name,
        "system_fingerprint": "fp_44709d6fcb",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "\n\nHello there, how may I assist you today?",
                },
                "logprobs": None,
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 9, "completion_tokens": 12, "total_tokens": 21},
    }

    content = ""
    async for chunk in poe_bot_stream_partials:
        content += chunk
    openai_nonstream_response_template["choices"][0]["message"]["content"] = content

    return openai_nonstream_response_template


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    # Assuming the header follows the standard format: "Bearer $API_KEY"
    api_key = authorization.split(" ")[1]
    body = await request.json()
    print(body)

    # Extract bot_name (model) and messages from the request body
    bot_name = body.get("model", DEFAULT_MODEL)
    openai_format_messages = body.get("messages", [])
    is_stream = body.get("stream", False)
    temperature = body.get("temperature", 0.7)
    functions = body.get("functions", [])

    if len(functions) > 0:
        raise HTTPException(status_code=500, detail="functions is not supported in this version")

    tools = body.get("tools", [])

    # Convert OpenAI formatted messages to POE formatted messages
    poe_format_messages = openai_format_messages_to_poe_format(openai_format_messages)

    # Get poe bot response
    poe_bot_stream_partials = get_poe_bot_stream_partials(
        api_key, poe_format_messages, bot_name, temperature, tools
    )

    if is_stream:
        # 流式输出
        stream = stream_partials_to_openai_stream_response(poe_bot_stream_partials, bot_name)
        return StreamingResponse(
            stream,
            media_type="text/json",
        )
    else:
        # 非流式输出, 仅用于new-api测试模型
        response = await stream_partials_to_openai_nonstream_response(
            poe_bot_stream_partials, bot_name
        )


if __name__ == "__main__":
    try:
        import uvloop
    except ImportError:
        uvloop = None
    if uvloop:
        uvloop.install()
    uvicorn.run(app, host="0.0.0.0", port=LISTEN_PORT, workers=1)
