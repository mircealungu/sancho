import os
import shlex
import subprocess

DEFAULT_TIMEOUT = 30  # seconds
MAX_OUTPUT = 10_000  # characters sent back to Claude

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


LIST_FOLDER = {
    "name": "list_folder",
    "description": "List what's in a folder, one name per line. Folders end with a slash. "
    "Not recursive: to see inside a subfolder, call it again with that subfolder. "
    "Hidden entries (starting with a dot, e.g. .gitignore) are left out unless you ask for them.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Folder to list, relative to the current folder. Defaults to the current folder.",
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Also list hidden entries. Defaults to false.",
            },
        },
    },
}


def list_folder(path=".", include_hidden=False):
    names = sorted(os.listdir(path))
    if not include_hidden:
        names = [name for name in names if not name.startswith(".")]
    if not names:
        return "(empty folder)"
    return "\n".join(
        name + "/" if os.path.isdir(os.path.join(path, name)) else name for name in names
    )


EDIT_FILE = {
    "name": "edit_file",
    "description": "Edit a file by replacing old_str with new_str. "
    "old_str must appear exactly once in the file, so include enough surrounding lines to make it unique. "
    "Read the file first, so old_str matches it exactly, including whitespace. "
    "To create a new file, pass an empty old_str and the whole content as new_str.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file, relative to the current folder.",
            },
            "old_str": {
                "type": "string",
                "description": "The exact text to replace. Empty to create a new file.",
            },
            "new_str": {
                "type": "string",
                "description": "The text to put in its place.",
            },
        },
        "required": ["path", "old_str", "new_str"],
    },
}


def edit_file(path, old_str, new_str):
    if old_str == new_str:
        raise ValueError("old_str and new_str are the same")

    if old_str == "":
        if os.path.exists(path):
            raise ValueError(f"{path} already exists; to change it, give the text to replace")
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w") as f:
            f.write(new_str)
        return f"Created {path}"

    with open(path) as f:
        content = f.read()

    count = content.count(old_str)
    if count == 0:
        raise ValueError(f"old_str not found in {path}")
    if count > 1:
        raise ValueError(f"old_str appears {count} times in {path}; include more context to make it unique")

    with open(path, "w") as f:
        f.write(content.replace(old_str, new_str))
    return f"Edited {path}"


RUN_PROGRAM = {
    "name": "run_program",
    "description": "Run a program on the user's computer and return its output (stdout and stderr together) "
    "and its exit code. The program runs in the current folder. "
    "There is no shell: give the program and each of its arguments separately, "
    "so pipes, redirects, globs and `cd` do not work. "
    "A non-zero exit code is not an error of this tool: it comes back with the output, so you can read it. "
    "Programs that run longer than the timeout are killed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "program": {
                "type": "string",
                "description": "The program to run, e.g. `python` or `git`.",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The arguments, one string each, e.g. [\"-m\", \"pytest\", \"-q\"]. Defaults to none.",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": f"Seconds to wait before killing the program. Defaults to {DEFAULT_TIMEOUT}.",
            },
        },
        "required": ["program"],
    },
}


def _command(program, args):
    """The program and its arguments as one list. args must be a list: list("status") would be 6 letters."""
    if args is None:
        args = []
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise TypeError(f'args must be a list of strings, e.g. ["status"], not {args!r}')
    return [program] + args


def run_program(program, args=None, timeout_seconds=DEFAULT_TIMEOUT):
    command = _command(program, args)
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,  # a program that waits for input must not hang Sancho
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as e:
        output = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        raise RuntimeError(
            f"{program} was killed after {timeout_seconds} seconds. Output so far:\n{_shorten(output)}"
        )

    return f"{_shorten(completed.stdout) or '(no output)'}\n[exit code {completed.returncode}]"


def _shorten(text):
    """Keep the start and the end of long output: the start says what ran, the end usually says what failed."""
    if len(text) <= MAX_OUTPUT:
        return text
    half = MAX_OUTPUT // 2
    return text[:half] + f"\n... ({len(text) - MAX_OUTPUT} characters left out) ...\n" + text[-half:]


DEFINITIONS = [READ_FILE, LIST_FOLDER, EDIT_FILE, RUN_PROGRAM]
FUNCTIONS = {
    READ_FILE["name"]: read_file,
    LIST_FOLDER["name"]: list_folder,
    EDIT_FILE["name"]: edit_file,
    RUN_PROGRAM["name"]: run_program,
}


NEEDS_CONFIRMATION = {RUN_PROGRAM["name"]}

yolo = False  # set by main.py for --yolo: confirm() then never asks


def confirm(call):
    """Ask the user before running a tool that acts on the world. Raises if they decline."""
    if yolo:
        return
    command = shlex.join(_command(call.input.get("program", ""), call.input.get("args")))
    try:
        answer = input(f"\033[33mRun `{command}`? [y/N] \033[0m")
    except EOFError:  # Ctrl-D: no answer is a no
        answer = ""
    if answer.strip().lower() not in ("y", "yes"):
        raise PermissionError("The user declined to run this program. Do not retry it; ask what they want instead.")


def run(tool_calls):
    results = []

    for call in tool_calls:
        try:
            print(f"\033[90m🔧 {call.name}({call.input})\033[0m")
            function = FUNCTIONS[call.name]
            if call.name in NEEDS_CONFIRMATION:
                confirm(call)
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
