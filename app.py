import os
import uvicorn

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException

from service.chat_service import ChatService

app = FastAPI()
load_dotenv()

chat_service = ChatService()


@app.post("/v1/chat/completions")
async def completions(request: Request):
    """
    获取聊天机器人的回复
    :param request:
    :return:
    """
    headers = dict(request.headers)
    authorization = headers.get("authorization", "")
    api_key = authorization.replace("Bearer ", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await chat_service.completions(request, api_key)


@app.get("/v1/models")
async def models():
    """
    获取支持的模型列表
    :return:
    """
    return {"models": ["GPT-3.5-Turbo"]}


if __name__ == '__main__':
    try:
        import uvloop
    except ImportError:
        uvloop = None
    if uvloop:
        uvloop.install()

    LISTEN_PORT = int(os.environ.get("LISTEN_PORT", default=9881))
    RELOAD = os.environ.get("RELOAD", default="true").lower() == "true"
    # Run the FastAPI app with Uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=LISTEN_PORT, workers=1, reload=RELOAD)
