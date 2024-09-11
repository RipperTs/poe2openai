import os
import time
import uuid
import uvicorn
import json

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional, List
from fastapi_poe.types import ProtocolMessage, ToolDefinition, QueryRequest, ToolCallDefinition, ToolResultDefinition
from fastapi_poe.types import PartialResponse as BotMessage
from fastapi_poe.client import stream_request_base, PROTOCOL_VERSION
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

app = FastAPI()
# 跨域问题处理
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 加载环境变量
load_dotenv()

# 默认参数
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "GPT-3.5-Turbo")
BASE_URL = os.environ.get("BASE_URL", default="https://api.poe.com/bot/")


def format_messages(openai_format_messages: list) -> tuple[list, Optional[List[ToolCallDefinition]], list]:
    """
    将 OpenAI 格式的信息转换为 POE 格式的信息。
    :param openai_format_messages:
    :return:
    """
    # 普通消息
    ordinary_messages = []
    # 工具调用消息
    tool_calls_messages = []
    # 工具结果消息
    tool_results_messages = []
    for msg in openai_format_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # 系统消息, 原始消息数据
        if role == "system":
            ordinary_msg = ProtocolMessage(
                role=role,
                content=content,
                content_type="text/plain"
            )
            ordinary_messages.append(ordinary_msg)

        # 用户消息, 这里的content可能是字符串或者列表
        elif role == "user":
            if isinstance(content, list):
                text = ""
                url = ""
                for ctx in content:
                    type = ctx.get("type", "text")
                    if type == "text":
                        text = ctx.get("text", "")
                    if type == "image_url":
                        url = ctx.get("image_url", {}).get("url", "")
                        # todo: 处理图片, 这里可能是完整的URL,也可能是base64编码

                ordinary_msg = ProtocolMessage(
                    role=role,
                    content=text
                )
                ordinary_messages.append(ordinary_msg)
            else:
                ordinary_msg = ProtocolMessage(
                    role=role,
                    content=content,
                )
                ordinary_messages.append(ordinary_msg)

        #  机器人消息
        elif role == "assistant":
            tool_calls = msg.get("tool_calls", [])
            if len(tool_calls) == 0:
                ordinary_msg = ProtocolMessage(
                    role="bot",
                    content=content,
                )
                ordinary_messages.append(ordinary_msg)
            else:
                for tool in tool_calls:
                    tool_calls_messages.append(ToolCallDefinition(**tool))

        # 工具消息
        elif role == "tool":
            tool_results_messages.append(ToolResultDefinition(**msg))
        else:
            raise ValueError(f"Invalid role: {role}")

    return ordinary_messages, tool_calls_messages, tool_results_messages


def functions2Tools(tools, functions):
    """
    functions转tools
    :param functions:
    :return:
    """
    if len(functions) == 0 and len(tools) > 0:
        return tools
    if len(functions) == 0 and len(tools) == 0:
        return []
    tools = []
    for function in functions:
        tools.append({
            "type": "function",
            "function": function
        })
    return tools


async def stream_request(
        api_key: str,
        ordinary_messages: list,
        tool_calls_messages: Optional[List[ToolCallDefinition]],
        tool_results_messages: list,
        bot_name: str,
        temperature: float,
        tools_dict_list: list
) -> AsyncGenerator[BotMessage, None]:
    """
    流式请求
    :param api_key: API_KEY
    :param ordinary_messages: 普通消息
    :param tool_calls_messages: 工具调用消息
    :param tool_results_messages: 工具结果消息
    :param bot_name: 机器人名称
    :param temperature: 温度
    :param tools_dict_list: 工具列表
    :return:
    """
    tools = [ToolDefinition(**tools_dict) for tools_dict in tools_dict_list]
    additional_params = {
        "temperature": temperature,
        "skip_system_prompt": False
    }

    # 构建查询请求
    request = QueryRequest(
        query=ordinary_messages,
        conversation_id="",
        user_id="",
        message_id="",
        version=PROTOCOL_VERSION,
        type="query",
        **additional_params,
    )

    # 发送请求到poe服务
    async for message in stream_request_base(
            request=request,
            bot_name=bot_name,
            api_key=api_key,
            tools=tools if tools else None,
            tool_calls=tool_calls_messages if tool_calls_messages else None,
            tool_results=tool_results_messages if tool_results_messages else None,
    ):
        yield message


async def stream_response(
        poe_bot_stream_partials: AsyncGenerator[BotMessage, None],
        bot_name: str,
        tools: list
) -> AsyncGenerator[str, None]:
    # Create a base response template
    response_template = {
        "id": str(uuid.uuid4()),
        "object": "chat.completion.chunk",
        "created": time.time(),
        "model": bot_name,
        "choices": [
            {
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": ""
                },
                "logprobs": None,
                "finish_reason": None,
            }
        ],
    }
    is_use_tool = False
    async for partial in poe_bot_stream_partials:
        # 有工具传入并且partial.data不为空时，直接返回data, 也就是原始数据输出
        if len(tools) > 0 and partial.data is not None:
            is_use_tool = True
            yield f"data: {json.dumps(partial.data, ensure_ascii=False)}\n\n"
        else:
            # 其他响应正常使用模板处理
            response_template["choices"][0]["delta"]["content"] = partial.text
            yield f"data: {json.dumps(response_template)}\n\n"

    if is_use_tool is False:
        # Termination sequence
        response_template["choices"][0]["delta"] = {}  # Empty 'delta' field
        # Set 'finish_reason' to 'stop'
        response_template["choices"][0]["finish_reason"] = "stop"
        yield f"data: {json.dumps(response_template)}\n\ndata: [DONE]\n\n"
    else:
        yield f"data: [DONE]\n\n"

@app.get("/")
async def index():
    return {"message": "Hi, Poe!"}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    # Assuming the header follows the standard format: "Bearer $API_KEY"
    api_key = authorization.split(" ")[1]
    body = await request.json()

    # Extract bot_name (model) and messages from the request body
    bot_name = body.get("model", DEFAULT_MODEL)
    openai_format_messages = body.get("messages", [])
    is_stream = body.get("stream", False)
    temperature = body.get("temperature", 0.7)
    tools = functions2Tools(body.get("tools", []), body.get("functions", []))

    # 将 OpenAI 格式的信息转换为 POE 格式的信息。
    ordinary_messages, tool_calls_messages, tool_results_messages = format_messages(openai_format_messages)

    # 获取机器人流式响应
    poe_bot_stream_partials = stream_request(
        api_key, ordinary_messages, tool_calls_messages,
        tool_results_messages, bot_name, temperature, tools
    )

    if is_stream:
        # 流式输出
        stream = stream_response(poe_bot_stream_partials, bot_name, tools)
        return StreamingResponse(
            stream,
            media_type="text/event-stream",
        )

    response = await not_stream_response(
        poe_bot_stream_partials, bot_name, tools
    )
    return JSONResponse(content=response)


async def not_stream_response(
        poe_bot_stream_partials: AsyncGenerator[BotMessage, None],
        bot_name: str,
        tools: list
) -> dict:
    """
    非流式输出
    :param poe_bot_stream_partials:
    :param bot_name:
    :return:
    """

    def get_from_list(lst, index, default=None):
        return lst[index] if index < len(lst) else default

    response_template = {
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
                    "content": "",
                },
                "logprobs": None,
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 9, "completion_tokens": 12, "total_tokens": 21},
    }

    content = ""
    is_use_tool = False
    function_name = []
    arguments = []
    arguments_only_content = ""
    id = []
    async for partial in poe_bot_stream_partials:
        if len(tools) > 0 and partial.data is not None:
            is_use_tool = True
            choices = get_from_list(partial.data.get("choices", []), 0, {})
            tool_calls = choices.get("delta", {}).get("tool_calls", [])
            function_content = get_from_list(tool_calls, 0, {}).get("function", {})
            tool_function_name = function_content.get("name", "")

            if tool_function_name != "":
                function_name.append(tool_function_name)
                if arguments_only_content != "":
                    arguments.append(arguments_only_content)
                    arguments_only_content = ""

            function_id = get_from_list(tool_calls, 0, {}).get("id", "")
            if function_id != "":
                id.append(function_id)

            function_arguments = function_content.get("arguments", "")
            arguments_only_content += function_arguments
            item_content = choices.get("delta", {}).get("content", None)
            if item_content is not None:
                content += item_content
        else:
            content += partial.text

    if is_use_tool is False:
        response_template["choices"][0]["message"]["content"] = content
    else:
        # 使用工具时数据结构
        arguments.append(arguments_only_content)
        tool_calls = []
        for i in range(len(id)):
            tool_calls.append({
                "id": id[i],
                "type": "function",
                "function": {
                    "name": function_name[i],
                    "arguments": arguments[i]
                }
            })
        response_template["choices"][0] = {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content if content != "" else None,
                "tool_calls": tool_calls
            },
            "logprobs": None,
            "finish_reason": "tool_calls",
        }

    return response_template


if __name__ == "__main__":
    try:
        import uvloop
    except ImportError:
        uvloop = None
    if uvloop:
        uvloop.install()

    LISTEN_PORT = int(os.environ.get("LISTEN_PORT", default=9881))
    RELOAD = os.environ.get("RELOAD", default="True").lower() == "true"
    # 启动服务
    uvicorn.run("main:app", host="0.0.0.0", port=LISTEN_PORT, workers=1, reload=RELOAD)
