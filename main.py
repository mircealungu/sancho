"""Sancho: a basic chat agent, inspired by Thorsten Ball's "How to Build an Agent"."""

import claude
import tools


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

        while True:

            message = claude.get_next_answer(conversation, tools.DEFINITIONS)
            conversation.append({"role": "assistant", "content": message.content})
            claude.show(message)

            if message.stop_reason != "tool_use":
                break

            results = tools.run(message.content)
            conversation.append({"role": "user", "content": results})


if __name__ == "__main__":
    main()
