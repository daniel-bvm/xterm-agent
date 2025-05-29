import json
import requests # type: ignore

messages = []

while True:
    user_input = input("User: ")
    if user_input == "quit":
        break

    messages.append({"role": "user", "content": user_input})

    payload = {
        "messages": messages,
    }
    stream = requests.post("http://localhost:7000/prompt", json=payload, stream=True)

    response = {}
    for line in stream.iter_lines():
        if line:
            line = line.decode("utf-8")
            line = line.split("data: ")[1]
            if line != "[DONE]":
                response = json.loads(line)
    
    # print(response)
    response_content = response["choices"][0]["delta"]["content"]
    messages.append({"role": "assistant", "content": response_content})
    print("AI:", response_content)
