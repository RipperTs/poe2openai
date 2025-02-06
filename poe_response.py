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

        :param poe_bot_stream_partials: 异步生成器，返回 BotMessage
        :param bot_name: 机器人名称
        :param tools: 工具列表
        :return: 异步生成器返回处理后的流式数据
        """
        response_template = {
            "id": str(uuid.uuid4()),
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": bot_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        # 正常响应时使用content字段；若推理过程处于进行中，则临时使用reasoning_content字段显示当前chunk的内容。
                        "content": ""
                    },
                    "logprobs": None,
                    "finish_reason": None,
                }
            ],
        }

        # 标记是否进入推理状态
        in_reasoning = False
        is_use_tool = False

        async for partial in poe_bot_stream_partials:
            # 如果有工具并且partial.data不为空，则直接返回原始数据
            if len(tools) > 0 and partial.data is not None:
                is_use_tool = True
                yield f"data: {json.dumps(partial.data, ensure_ascii=False)}\n\n"
                continue

            # 跳过无用的Thinking...输出
            if 'Thinking...' in partial.text:
                continue

            # 非推理状态下
            if not in_reasoning:
                if partial.text.startswith("```text\n"):
                    # 进入推理状态：去除开头标识
                    current_chunk = partial.text[len("```text\n"):]
                    # 如果当前chunk同时包含结束标识符，则立即结束推理
                    if current_chunk.strip().endswith("```"):
                        # 去掉结尾的 "```" 标识
                        final_text = current_chunk.strip()[:-3]
                        response_template["choices"][0]["delta"]["content"] = final_text
                        response_template["choices"][0]["delta"].pop("reasoning_content", None)
                        in_reasoning = False
                    else:
                        response_template["choices"][0]["delta"]["reasoning_content"] = current_chunk
                        response_template["choices"][0]["delta"]["content"] = None
                        in_reasoning = True
                else:
                    # 普通响应处理：直接写入content字段，并删除可能残留的reasoning_content字段
                    response_template["choices"][0]["delta"]["content"] = partial.text
                    response_template["choices"][0]["delta"].pop("reasoning_content", None)
            else:
                # 如果已经进入推理状态，则本次返回的chunk只显示当前内容，不做累积
                if partial.text.strip().endswith("```"):
                    # 当前chunk带有结束标识，则取出结束标识前的文本，并结束推理状态
                    current_chunk = partial.text.rstrip()[:-3]
                    response_template["choices"][0]["delta"]["content"] = current_chunk
                    response_template["choices"][0]["delta"].pop("reasoning_content", None)
                    in_reasoning = False
                else:
                    # 仍在推理状态，直接覆盖reasoning_content（不累加之前内容）
                    response_template["choices"][0]["delta"]["reasoning_content"] = partial.text
                    response_template["choices"][0]["delta"]["content"] = None

            yield f"data: {json.dumps(response_template, ensure_ascii=False)}\n\n"

        if not is_use_tool:
            # 流式输出结束时，发送终止序列
            response_template["choices"][0]["delta"] = {}  # 清空delta字段
            response_template["choices"][0]["finish_reason"] = "stop"
            yield f"data: {json.dumps(response_template, ensure_ascii=False)}\n\ndata: [DONE]\n\n"
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
            "created": int(time.time()),
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
                # OpenAI的思考模型直接跳过无用的Thinking...输出内容
                if 'Thinking...' in partial.text:
                    continue
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
