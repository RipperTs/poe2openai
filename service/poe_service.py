import os
from typing import List, Literal, Optional, Dict

from httpx_sse._decoders import SSEDecoder
from pydantic import BaseModel
import json

import httpx
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse, Response

from utils.date_utils import date_serializer


class ProtocolMessage(BaseModel):
    role: Literal["system", "user", "bot"]
    sender_id: Optional[str] = None
    content: str
    content_type: Optional[str] = "text/markdown"
    timestamp: Optional[int] = 0
    message_id: Optional[str] = ""
    attachments: Optional[List] = []
    feedback: Optional[List] = []


class QueryRequest(BaseModel):
    version: Optional[str] = '1.0'
    type: Optional[str] = 'query'
    query: List[ProtocolMessage]
    user_id: Optional[str] = ""
    conversation_id: Optional[str] = ""
    message_id: Optional[str] = ""
    metadata: Optional[str] = ""
    api_key: Optional[str] = "<missing>"
    access_key: Optional[str] = "<missing>"
    temperature: Optional[float] = 0.7
    skip_system_prompt: Optional[bool] = False
    logit_bias: Dict[str, float] = {}
    stop_sequences: List[str] = []
    language_code: Optional[str] = "en"
    bot_query_id: Optional[str] = ""
    tools: Optional[List] = []


class PoeService:
    def __init__(self):
        self.default_model = os.environ.get("DEFAULT_MODEL", "GPT-3.5-Turbo")
        self.base_url = os.environ.get("BASE_URL", default="https://api.poe.com/bot/")
        # 构建流式输出客户端
        self.httpx_client = httpx.AsyncClient()

        self._event = ""
        self._data: List[str] = []
        self._last_event_id = ""
        self._retry: Optional[int] = None

    def convertMessage(self, messages: List):
        """
        消息体格式转换
        :param messages:
        :return:
        """
        if len(messages) == 0:
            return []
        messages = [
            ProtocolMessage(
                role=msg["role"].lower().replace("assistant", "bot"),
                content=msg["content"]
            )
            for msg in messages
        ]
        return messages

    def buildRequest(self, messages: List[ProtocolMessage], temperature: float,
                     tools: List) -> QueryRequest:
        """
        构建请求体
        :param messages:
        :param temperature:
        :param tools:
        :return:
        """
        request_data = QueryRequest(query=messages,
                                    user_id="aikey-wslmf",
                                    temperature=temperature,
                                    skip_system_prompt=False,
                                    tools=tools,
                                    metadata="")
        return request_data

    async def sendRequest(self, request_data: QueryRequest, bot_name: str,
                          api_key: str, is_stream: bool = False):
        """
        发送请求
        :param request_data:
        :param bot_name:
        :return:
        """
        url = f"{self.base_url}{bot_name}"
        headers = {
            'content-type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        # 请求体转json
        request_data_json = json.dumps(request_data.dict(), ensure_ascii=False, default=date_serializer)
        # 构建请求
        req = self.httpx_client.build_request(
            method='post',
            url=url,
            headers=headers,
            content=request_data_json,
            timeout=60
        )

        # 发送请求
        r = await self.httpx_client.send(req, stream=is_stream)

        # 检查响应状态码
        if r.status_code != 200:
            return {"error": "HTTP request failed", "status_code": r.status_code, "response": r.text}

        if is_stream is False:
            content = await r.aread()
            return Response(content, status_code=200, headers=dict(r.headers), media_type='text/plan',
                            background=BackgroundTask(r.aclose))

        return StreamingResponse(self._stream_response(r),
                                 status_code=200, headers=dict(r.headers),
                                 media_type='text/event-stream', background=BackgroundTask(r.aclose))

    async def _stream_response(self, response):
        """
        流式输出响应处理
        :return:
        """
        event_buffer = ""
        async for chunk in response.aiter_text():
            event_buffer += chunk
            while "\r\n\r\n" in event_buffer:
                event, event_buffer = event_buffer.split("\r\n\r\n", 1)
                if event.startswith("event: json"):
                    data = event.split("data: ", 1)[1].strip()

                    try:
                        json_data = json.loads(data)
                        print("JSON事件数据:", json.dumps(json_data, ensure_ascii=False, indent=2))
                        yield json.dumps(json_data)  # 这里你可以根据需要调整返回数据的格式
                    except json.JSONDecodeError as e:
                        print("JSON 解码错误:", str(e))

                elif event.startswith("event: text"):
                    data = event.split("data: ", 1)[1].strip()
                    print("文本事件数据:", data)
                    yield data  # 这里你可以根据需要调整返回数据的格式
                elif event.startswith("event: done"):
                    print("事件结束")
                    yield event
                else:
                    print("未知事件类型:", event)
                    yield event  # 处理未知事件类型
