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
