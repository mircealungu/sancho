READ_FILE = {
    "name": "read_file",
    "description": "Read a file and return its contents as text. "
    "Use this when you want to know what's inside a file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file, relative to the current folder.",
            }
        },
        "required": ["path"],
    },
}


def read_file(path):
    with open(path) as f:
        return f.read()


DEFINITIONS = [READ_FILE]
FUNCTIONS = {READ_FILE["name"]: read_file}


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
