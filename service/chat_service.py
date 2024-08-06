import os

from starlette.exceptions import HTTPException
from starlette.requests import Request

from service.poe_service import PoeService

poe_service = PoeService()


class ChatService:
    def __init__(self):
        self.default_model = os.environ.get("DEFAULT_MODEL", "GPT-3.5-Turbo")

    async def completions(self, request: Request, api_key: str):
        """
        获取聊天机器人的回复
        :param request:
        :return:
        """
        body = await request.json()
        bot_name = body.get("model", self.default_model)
        messages = poe_service.convertMessage(body.get("messages", []))
        if len(messages) == 0:
            raise HTTPException(status_code=400, detail="messages is required")

        is_stream = body.get("stream", False)
        temperature = body.get("temperature", 0.7)
        tools = self.functions2Tools(body.get("tools", []), body.get("functions", []))
        # 构建请求体
        request_data = poe_service.buildRequest(messages, temperature, tools)
        # 发送请求
        return await poe_service.sendRequest(request_data, bot_name, api_key, is_stream)

    def functions2Tools(self, tools, functions):
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
