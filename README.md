# Poe2OpenAI

poe官方sdk转换openai接口规范, 您必须拥有 poe 订阅会员权限, 然后到 [https://poe.com/api_key](https://poe.com/api_key) 页面拿到您的key   

注意, 如果您的会员到期, 此key会立即失效, 当您重新续费后, 此key会自动变更.   

无法在国内网络访问 poe ,因此请配置代理服务.

## 如何使用

```shell
# Docker 启动
docker-compose up -d

# 更新镜像
1. 停止容器
docker-compose down

2. 删除镜像
docker rmi registry.cn-hangzhou.aliyuncs.com/ripper/poe2openai

3. 重新构建
docker-compose up -d
```

## Development

```shell
# 打包镜像(使用阿里云容器镜像服务)
docker build --platform linux/amd64 -f ./Dockerfile -t registry.cn-hangzhou.aliyuncs.com/ripper/poe2openai:latest .
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
- [x] 非流式输出
- [ ] Function Call
- [x] Tools Call
- [ ] 图片解析