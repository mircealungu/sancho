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


def run(blocks):
    results = []

    for block in blocks:
        if block.type != "tool_use":
            continue

        function = FUNCTIONS[block.name]
        print(f"\033[90m🔧 {block.name}({block.input})\033[0m")
        result = function(**block.input)
        results.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            }
        )

    return results
