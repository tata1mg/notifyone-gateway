ARG SYS_PLATFORM

FROM --platform=$SYS_PLATFORM python:3.9.10-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Args passed in the build command
ARG SERVICE_NAME

RUN apt-get update && \
    apt-get install -y \
        git \
        gcc \
        openssh-server \
        curl \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev \
        pkg-config

RUN echo "Y" | apt-get install procps

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create home ubuntu service
RUN mkdir -p /home/ubuntu/apps/$SERVICE_NAME/logs

# switch to code folder
WORKDIR /home/ubuntu/apps/$SERVICE_NAME

# Copy and install requirements
COPY pyproject.toml uv.lock /home/ubuntu/apps/$SERVICE_NAME/
RUN uv sync --frozen --no-dev

# Copy code folder
COPY . .

# Create a limited access user and change ownership of the application directory
RUN useradd -m appuser && \
    chown -R appuser:appuser /home/ubuntu/apps/$SERVICE_NAME

# Switch to limited access user
USER appuser

CMD ["python3", "-m", "app.service"]
