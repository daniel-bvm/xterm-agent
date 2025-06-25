docker build . -t xterm --pull

docker run --rm -it \
    --network=network-agent-external \
    -p 7000:80 \
    -p 7681:7681 \
    --add-host=localmodel:host-gateway \
    --volume $(pwd)/output:/workspace/output \
    -e LLM_BASE_URL="$LLM_BASE_URL" \
    -e LLM_API_KEY="$LLM_API_KEY" \
    -e LLM_MODEL_ID="$LLM_MODEL_ID" \
    -e EMBEDDING_MODEL_ID="$EMBEDDING_MODEL_ID" \
    -e EMBEDDING_URL="$EMBEDDING_URL" \
    -e EMBEDDING_API_KEY="$EMBEDDING_API_KEY" \
    -e ETERNALAI_MCP_PROXY_URL=http://localmodel:4001/prompt \
    xterm
