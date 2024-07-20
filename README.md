# Poe2OpenAI

poe官方sdk转换openai接口规范, 您必须拥有 poe 订阅会员权限, 然后到 [https://poe.com/api_key](https://poe.com/api_key) 页面拿到您的key   

注意, 如果您的会员到期, 此key会立即失效, 当您重新续费后, 此key会自动变更.   

无法在国内网络访问 poe ,因此请配置代理服务.

## 使用

```shell
# docker镜像
docker pull registry.cn-hangzhou.aliyuncs.com/ripper/poe2openai

# 运行
docker run -dit --name poe2openai --restart=always -p 9881:9881 registry.cn-hangzhou.aliyuncs.com/ripper/poe2openai

# 更新
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower -cR
```

```shell
# 请求示例
curl --location 'http://127.0.0.1:9881/v1/chat/completions' \
--header 'Content-Type: application/json;charset=utf-8' \
--header 'Authorization: Bearer <POE API_KEY>' \
--data '{
  "model": "GPT-3.5-Turbo",
  "messages": [
    {
      "role": "user",
      "content": "hi"
    }
  ],
  "stream":true
}'
```

## 功能

- [x] 流式输出
- [x] 非流式输出 (仅用于测试连通性)
- [ ] 模型列表
- [ ] Function Call
- [ ] 图片解析
- [ ] Embedding