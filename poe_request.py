from typing import AsyncGenerator, Optional, List
from fastapi_poe.types import ToolDefinition, QueryRequest, ToolCallDefinition
from fastapi_poe.types import PartialResponse as BotMessage
from fastapi_poe.client import stream_request_base, PROTOCOL_VERSION


class PoeRequest:
    """
    poe请求
    """
    async def stream_request(self,
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
