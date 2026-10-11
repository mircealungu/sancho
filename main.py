"""Sancho: a basic chat agent, inspired by Thorsten Ball's "How to Build an Agent"."""

import anthropic

MODEL = "claude-sonnet-5-5"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def main():
    conversation = []
    print("Sancho. At your service 🫡 (Ctrl-D to quit)")

    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input.strip():
            continue

        conversation.append({"role": "user", "content": user_input})
        message = client.messages.create(model=MODEL, max_tokens=16000, messages=conversation)
        conversation.append({"role": "assistant", "content": message.content})

        for block in message.content:
            if block.type == "text":
                print("Sancho:", block.text)


if __name__ == "__main__":
    main()
