from nikolasigmoid/py-mcp-proxy:latest

env DEBIAN_FRONTEND=noninteractive

run apt-get update \
    && apt-get install -y screen sudo build-essential cmake git libjson-c-dev libwebsockets-dev curl net-tools lolcat cowsay jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

run git clone https://github.com/tsl0922/ttyd.git \
    && cd ttyd \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make \
    && make install

env HTTP_DISPLAY_URL="http://localhost:7681"

copy requirements.txt .
run pip install -r requirements.txt

env PATH="$PATH:/usr/games"

copy config.json .
copy terminal_controller.py .
copy system_prompt.txt .

expose 7681
env NO_STREAMING=0