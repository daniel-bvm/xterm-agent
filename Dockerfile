from nikolasigmoid/py-mcp-proxy:latest

env DEBIAN_FRONTEND=noninteractive
copy requirements.txt .

run apt-get update \
    && apt-get install -y screen sudo build-essential cmake git libjson-c-dev libwebsockets-dev curl net-tools lolcat cowsay \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

run git clone https://github.com/tsl0922/ttyd.git \
    && cd ttyd \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make \
    && sudo make install

env HTTP_DISPLAY_URL="http://localhost:7681"
run pip install -r requirements.txt
expose 7681

env PATH="$PATH:/usr/games"

copy config.json .
copy terminal_controller.py .
copy system_prompt.txt .