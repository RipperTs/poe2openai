from typing import AsyncGenerator, Optional, List
from fastapi_poe.types import PartialResponse as BotMessage
import uuid
import time
import json


class PoeResponse:
    """
    Poe消息响应
    """

    async def stream_response(self,
                              poe_bot_stream_partials: AsyncGenerator[BotMessage, None],
                              bot_name: str,
                              tools: list
                              ) -> AsyncGenerator[str, None]:
        """
        流式输出
        :param poe_bot_stream_partials:
        :param bot_name:
        :param tools:
        :return:
        """
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

    async def not_stream_response(self,
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
