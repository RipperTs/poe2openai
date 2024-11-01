import os
import uvicorn

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from message_convert import MessageConvert
from poe_request import PoeRequest
from poe_response import PoeResponse
from utils import PoeUtils

load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 默认参数
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "GPT-3.5-Turbo")
BASE_URL = os.environ.get("BASE_URL", default="https://api.poe.com/bot/")

poe_request = PoeRequest()
poe_response = PoeResponse()
message_convert = MessageConvert()
poe_utils = PoeUtils()


@app.get("/")
async def index():
    return {"message": "Hi, Poe!"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str = Header(None)):
    """
    文本生成
    :param request:
    :param authorization:
    :return:
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    # 解析API KEY
    api_key = authorization.split(" ")[1]
    body = await request.json()

    # 从请求体中提取bot_name（模型）和消息
    bot_name = body.get("model", DEFAULT_MODEL)
    openai_format_messages = body.get("messages", [])
    is_stream = body.get("stream", False)
    temperature = body.get("temperature", 0.7)
    tools = poe_utils.functions2Tools(body.get("tools", []), body.get("functions", []))

    # 将 OpenAI 格式的信息转换为 POE 格式的信息。
    ordinary_messages, tool_calls_messages, tool_results_messages = message_convert.format_messages(
        openai_format_messages)

    # 获取机器人流式响应
    poe_bot_stream_partials = poe_request.stream_request(
        api_key, ordinary_messages, tool_calls_messages,
        tool_results_messages, bot_name, temperature, tools
    )

    if is_stream:
        # 流式输出
        stream = poe_response.stream_response(poe_bot_stream_partials, bot_name, tools)
        return StreamingResponse(
            stream,
            media_type="text/event-stream",
        )

    response = await poe_response.not_stream_response(
        poe_bot_stream_partials, bot_name, tools
    )
    return JSONResponse(content=response)


if __name__ == "__main__":
    try:
        import uvloop
    except ImportError:
        uvloop = None
    if uvloop:
        uvloop.install()

    LISTEN_PORT = int(os.environ.get("LISTEN_PORT", default=9881))
    RELOAD = os.environ.get("RELOAD", default="True").lower() == "true"
    uvicorn.run("main:app", host="0.0.0.0", port=LISTEN_PORT, workers=1, reload=RELOAD)
