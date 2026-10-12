# Sancho

A coding agent built from scratch in Python, one small step at a time.

Sancho follows Thorsten Ball's [How to Build an Agent](https://ampcode.com/how-to-build-an-agent), which builds the same
thing in Go. His point: an agent is not magic, it's "an LLM, a loop, and enough tokens". Python lets us show that with
even less ceremony.

Each step below ends at a git tag (`step1`, `step2`, ...), so you can check out any step and run it:

```bash
git checkout step1
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python main.py
```

## Before the code: four things about the API

Sancho talks to Claude through the Messages API. The whole agent rests on four facts about it:

1. **It is stateless.** Claude remembers nothing between calls. Every request carries the whole conversation so far, so
   keeping the conversation is the client's job.
2. **Roles alternate.** The conversation is a list of messages with `"role": "user"` and `"role": "assistant"`, taking
   turns, starting with the user.
3. **A reply is a list of content blocks, not a string.** For now we only care about `text` blocks. Later, tool calls
   arrive as blocks too.
4. **`stop_reason` says what happens next.** `"end_turn"` means Claude is done and it's our turn. Later, `"tool_use"`
   will mean Claude wants us to run something.

In Python the messages are plain dicts, exactly the JSON that goes over the wire, so what you read in the code is what
the API sees.

## Talking to Claude: a thin wrapper

All calls to Claude go through one small file, `claude.py`. It's the only file that imports `anthropic`.

It exists because I don't like one of the SDK's names. To get Claude's next answer, the SDK has you call
`client.messages.create(...)`, which reads as "create a message". So we wrap it in a function whose name says what we
actually want:

```python
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def get_next_answer(conversation):
    """Send the whole conversation to Claude and return its reply."""
    return client.messages.create(model=MODEL, max_tokens=16000, messages=conversation)
```

Underneath it's one HTTP POST to `/v1/messages`, which blocks until the reply is complete. `max_tokens` caps the length
of the reply. The wrapper only renames: it takes the conversation in the API's format and returns the API's reply object
unchanged.

In `main.py` we `import claude`, so every call reads `claude.get_next_answer(...)` and you can see exactly where the
code talks to Claude.

## Step 1: a chatbot

> [!TIP]
> Code for this step: `git checkout step1`

The smallest useful thing: read a line, send it to Claude, print the answer, repeat.

```python
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
        message = claude.get_next_answer(conversation)
        conversation.append({"role": "assistant", "content": message.content})

        for block in message.content:
            if block.type == "text":
                print("Sancho:", block.text)
```

Things to notice:

- **`conversation` is Sancho's whole memory.** Because the API is stateless, we send the full list every turn and append
  Claude's reply to it.
- **We print only the `text` blocks.** The model may also return a `thinking` block (its reasoning, empty by default),
  so we don't assume the first block is the answer.
- **Empty lines are skipped** because the API rejects a message with empty text.

This is a chatbot, not yet an agent. It can talk, but it can't do anything. That's step 2.

![Sancho step 1: a chat in the terminal](images/step1-chat.png)

## Step 2: A fool, but with a tool

> [!TIP]
> Code for this step: `git checkout step2`

An agent is a chatbot that can do things. Sancho's first ability: reading a file.

Claude can't touch your disk, but it can ask. We tell it which tools exist; when it wants one, it stops and replies with
a request instead of an answer; we run the tool and send back the result. Claude never runs anything itself. Sancho
does.

### Defining a tool

A tool is three things: a name, a description written for Claude, and a JSON Schema for its input.

```python
READ_FILE = {
    "name": "read_file",
    "description": "Read a file and return its contents as text. ...",
    "input_schema": {...},  # one string: "path"
}
```

The full definition is in `tools.py`, next to the function that does the work:

```python
def read_file(path):
    with open(path) as f:
        return f.read()
```

Things to notice:

- **The description is a prompt.** Claude decides when and how to call the tool from the description alone, so it says
  what the tool does and when to use it.
- **The definition is just data.** Nothing ties `READ_FILE` to `read_file`. Connecting the name Claude asks for to the
  function we run is our job.

### The round trip

1. **We send the tools** with every request, next to the conversation. `get_next_answer` gets a second argument,
   `tools`, and passes it on as `tools=tools`.
2. **Claude asks.** The reply's `stop_reason` is `"tool_use"`, and its content holds a `tool_use` block with an `id`,
   the tool's `name`, and its `input`.
3. **We run the tool and answer** with a user message holding a `tool_result` block. Its `tool_use_id` tells Claude
   which request this result belongs to.
4. **We call Claude again**, without waiting for the user, until `stop_reason` is `"end_turn"`.

### Running the tools

`tools.py` keeps two lookups: `DEFINITIONS`, the list we send to Claude, and `FUNCTIONS`, which maps each tool's name to
the Python function that does the work. `run` takes the tool calls from Claude's reply and turns each one into a
`tool_result`:

```python
def run(tool_calls):
    results = []

    for call in tool_calls:
        function = FUNCTIONS[call.name]
        print(f"\033[90m🔧 {call.name}({call.input})\033[0m")
        result = function(**call.input)
        results.append(
            {
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": result,
            }
        )

    return results
```

Things to notice:

- **`**call.input` unpacks the arguments.** `call.input` is a dict like `{"path": "requirements.txt"}`, and `**` turns
  it into `path="requirements.txt"`. So `run` works for any tool, whatever its arguments are called.
- **The gray 🔧 line** shows every tool call as it happens, so you can watch the agent act.

### The agent loop

The user's turn now hands over to `agent_loop`: keep asking Claude until it stops asking for tools.

```python
def agent_loop(conversation):
    """Keep asking Claude, and running the tools it asks for, until it's done."""
    while True:
        message = claude.get_next_answer(conversation, tools.DEFINITIONS)

        # Every reply goes into the conversation, tool calls included: the API
        # matches each tool_result to a tool_use in the previous assistant message,
        # and wants the reply's thinking blocks sent back unchanged.
        conversation.append({"role": "assistant", "content": message.content})

        text = claude.text_of(message)
        if text:
            print("Sancho:", text)

        if message.stop_reason != "tool_use":
            return

        tool_calls = claude.tool_calls_of(message)
        results = tools.run(tool_calls)
        conversation.append({"role": "user", "content": results})


def main():
    conversation = []
    print("Sancho. At your service 🫡 (Ctrl-D to quit)")

    try:
        while True:
            user_input = input("You: ")
            if not user_input.strip():
                continue

            conversation.append({"role": "user", "content": user_input})
            agent_loop(conversation)
    except (EOFError, KeyboardInterrupt):
        pass
```

Things to notice:

- **Two loops, two turns.** The loop in `main` is your turn: it waits for input. `agent_loop` is the agent working:
  one question from you can take several rounds with Claude, and you type nothing in between. `agent_loop` is the whole
  difference between the chatbot of step 1 and an agent.
- **There is one place that asks Claude.** Ask, record, show, stop if Claude is done; otherwise run the tools, answer,
  and ask again.
- **All results go back in one user message.** Claude can ask for several tools in one reply; the answers travel
  together.
- **A reply has two parts we care about:** the text to show, and the tool calls to run. `claude.text_of` and
  `claude.tool_calls_of` pick them out of the reply's blocks (a reply can also hold `thinking` blocks, which stay in the
  conversation untouched). Knowing the block format is `claude.py`'s job; deciding what to do with the parts is
  `main.py`'s.
- **We print the text of every reply**, not just the last one, so a "Let me look at that file" before a tool call isn't
  lost.
- **The `try` wraps the whole loop**, not just `input()`. So Ctrl-C also works while the agent is busy, and ends Sancho
  cleanly instead of with a traceback.

Ask about a file and watch Sancho read it:

![Sancho step 2: reading requirements.txt](images/step2-read-file.png)

Now ask about a file that doesn't exist:

![Sancho step 2: crashing on a missing file](images/step2-crash.png)

`open()` raises `FileNotFoundError`, nothing catches it, and Sancho dies. Fixing that is step 3.

## Step 3: when tools fail

> [!TIP]
> Code for this step: `git checkout step3`

A tool that fails shouldn't take Sancho down. The error is information: if Claude learns that `notex.txt` doesn't
exist, it can say so, or try another path. So instead of crashing, we send the error back as the tool's result:

```python
def run(tool_calls):
    results = []

    for call in tool_calls:
        try:
            print(f"\033[90m🔧 {call.name}({call.input})\033[0m")
            function = FUNCTIONS[call.name]
            result = function(**call.input)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": result,
                }
            )
        except Exception as e:
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": str(e),
                    "is_error": True,
                }
            )

    return results
```

Things to notice:

- **`"is_error": True`** tells Claude the tool failed, so it reads `str(e)` as an error message and not as the file's
  contents.
- **The lookup is inside the `try` too.** If Claude asks for a tool that doesn't exist, `FUNCTIONS[block.name]` raises
  `KeyError`, and that becomes an error result as well.
- **Every `tool_use` still gets exactly one `tool_result`.** The API requires an answer for each request, and failing
  is an answer.

Ask about `notex.txt` again, and Sancho tells you, in its own words, that the file isn't there.
