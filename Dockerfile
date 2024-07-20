FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 升级pip到最新版本
RUN pip install --no-cache-dir --upgrade pip

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码到镜像中
COPY . .

# 暴露端口
EXPOSE 9881

# 设置环境变量
ENV DEFAULT_MODEL="GPT-3.5-Turbo"
ENV LISTEN_PORT=9881
ENV BASE_URL="https://api.poe.com/bot/"

# 运行应用程序
CMD ["python", "main.py"]