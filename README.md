# Sancho

A coding agent built from scratch in Python, one small step at a time.

Sancho follows Thorsten Ball's [How to Build an Agent](https://ampcode.com/how-to-build-an-agent), which builds the same thing in Go. His point: an agent is not magic, it's "an LLM, a loop, and enough tokens". Python lets us show that with even less ceremony.

Each step below is one commit, so you can check out any step and run it.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python main.py
```

## Before the code: four things about the API

Sancho talks to Claude through the Messages API. The whole agent rests on four facts about it:

1. **It is stateless.** Claude remembers nothing between calls. Every request carries the whole conversation so far, so keeping the conversation is the client's job.
2. **Roles alternate.** The conversation is a list of messages with `"role": "user"` and `"role": "assistant"`, taking turns, starting with the user.
3. **A reply is a list of content blocks, not a string.** For now we only care about `text` blocks. Later, tool calls arrive as blocks too.
4. **`stop_reason` says what happens next.** `"end_turn"` means Claude is done and it's our turn. Later, `"tool_use"` will mean Claude wants us to run something.

In Python the messages are plain dicts, exactly the JSON that goes over the wire, so what you read in the code is what the API sees.

## Step 1: a chatbot

The smallest useful thing: read a line, send it to Claude, print the answer, repeat.

```python
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
```

Things to notice:

- **`conversation` is Sancho's whole memory.** Because the API is stateless, we send the full list every turn and append Claude's reply to it. Delete the second `append` and Sancho forgets everything it said.
- **`client.messages.create(...)` is the only line that talks to Claude.** It's one HTTP POST to `/v1/messages`, and it blocks until the reply is complete. `max_tokens` caps the length of the reply.
- **We print only the `text` blocks.** The model may also return a `thinking` block (its reasoning, empty by default), so we don't assume the first block is the answer.
- **Empty lines are skipped** because the API rejects a message with empty text.

Try it: tell Sancho your name, then ask for it a few turns later. It remembers, but only because we resend the history.

This is a chatbot, not yet an agent. It can talk, but it can't do anything. That's step 2.
