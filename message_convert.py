from typing import Optional, List
from fastapi_poe.types import ProtocolMessage, ToolCallDefinition, ToolResultDefinition


class MessageConvert:
    """
    消息格式转换
    """

    def format_messages(self, openai_format_messages: list) -> tuple[list, Optional[List[ToolCallDefinition]], list]:
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
