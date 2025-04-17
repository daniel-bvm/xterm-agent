from nikolasigmoid/py-mcp-proxy:latest
copy . .


run curl -fsSL https://deb.nodesource.com/setup_23.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @openai/codex

run apt-get update && apt-get install sudo -y 
run pip install -r requirements.txt
