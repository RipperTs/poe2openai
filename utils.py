class PoeUtils:
    """
    常用工具类
    """
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
