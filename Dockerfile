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
        curl

RUN echo "Y" | apt-get install procps

RUN pip install --user pipenv
RUN pip install --upgrade pip

# Create home ubuntu service
RUN mkdir -p /home/ubuntu/apps/$SERVICE_NAME/logs

# switch to code folder
WORKDIR /home/ubuntu/apps/$SERVICE_NAME

# Copy and install requirements
COPY Pipfile Pipfile.lock /home/ubuntu/apps/$SERVICE_NAME/
RUN /root/.local/bin/pipenv sync --system

# Copy code folder
COPY . .

CMD ["python3", "-m", "app.service"]