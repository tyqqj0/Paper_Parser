# syntax=docker/dockerfile:1.6
# 单阶段构建，适合性能有限的服务器
FROM python:3.11-slim-bullseye

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app
 
# 移除 Debian 默认的 deb822 源文件，避免与自定义源混用
RUN rm -f /etc/apt/sources.list.d/debian.sources

# 配置清华源（Bullseye）
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main contrib non-free" >> /etc/apt/sources.list

# 配置pip使用清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn

# 优化 pip 体验与稳定性
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=0

# 一次性安装所有依赖，减少层数和构建时间
RUN --mount=type=cache,id=apt-cache,sharing=locked,target=/var/cache/apt \
    --mount=type=cache,id=apt-lists,sharing=locked,target=/var/lib/apt/lists \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=15 update && \
    apt-get install -y --no-install-recommends \
    curl \
    && pip install -U pip==25.2 setuptools==80.9.0 wheel==0.45.1

# 复制并安装Python依赖（利用Docker层缓存）
COPY requirements.txt .
RUN --mount=type=cache,id=pip-cache,sharing=locked,target=/root/.cache/pip \
    --mount=type=cache,id=pip-wheels,sharing=locked,target=/wheels \
    pip wheel --prefer-binary --wheel-dir=/wheels -r requirements.txt && \
    pip install --no-index --find-links=/wheels -r requirements.txt

# 复制应用代码
COPY . .

# 设置权限
RUN chown -R appuser:appuser /app
USER appuser

# 设置Python路径（优先使用本地 vendored 的 semanticscholar 包）
ENV PYTHONPATH=/app:/app/app/utils
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 健康检查（与应用实际路由一致）
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令（强制使用 asyncio 事件循环，避免与 uvloop 的兼容问题）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]