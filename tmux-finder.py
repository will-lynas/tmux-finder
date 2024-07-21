#!/usr/bin/env python3
import subprocess
import argparse
import tempfile
from dataclasses import dataclass
import sys

GREY = '\033[38;5;242m'
RED = '\033[31m'
GREEN = '\033[32m'
BLUE = '\033[34m'
ENDC = '\033[0m'

@dataclass
class Pane:
    pane_id: int
    window_index: int
    pane_index: int
    window_name: str
    path: str

@dataclass
class Session:
    session_id: int
    session_name: str
    panes: list[Pane]

parser = argparse.ArgumentParser()
parser.add_argument("preview_line", nargs="?")
args = parser.parse_args()

def run_cmd(cmd, suppress=False):
    stderr = subprocess.DEVNULL if suppress else None
    return subprocess.check_output(cmd, shell=True, stderr=stderr).decode("utf-8")

def get_sessions() -> dict[int, Session]:
    lines = [line.split("|") for line in run_cmd(
        'tmux list-panes -a -F '
        '"#{pane_id}|#{session_name}|#{window_index}|#{pane_index}|#{window_name}|#{pane_current_path}|#{session_id}"'
        ).strip().split("\n")]
    sessions: dict[int, Session] = {}
    for line in lines:
        pane_id = int(line[0][1:]) # Remove %
        pane = Pane(
                pane_id = pane_id,
                window_index = int(line[2]),
                pane_index = int(line[3]),
                window_name = line[4] or "-",
                path = get_git_root(line[5]),
            )
        session_id = int(line[6][1:]) # Remove $
        if session_id in sessions:
            sessions[session_id].panes.append(pane)
        else:
            session_name = line[1] or "-"
            sessions[session_id] = Session(session_id, session_name, [pane])
    return sessions

def get_git_root(path):
    try:
        path = run_cmd(f"git -C '{path}' rev-parse --show-toplevel", suppress=True)
        return run_cmd(f"basename '{path}'").strip()
    except subprocess.CalledProcessError:
        return path

def pad_and_join(lines):
    section_lengths = [max(len(line[i]) for line in lines) for i in range(len(lines[0]))]
    out = ""
    for line in lines:
        for i in range(len(line)):
            out += line[i].ljust(section_lengths[i] + 1)
        out += "\n"
    return out

def do_fzf(lines):
    joined_lines = pad_and_join(lines)
    script_path = sys.argv[0]
    options = (f"--ansi "
               f"--preview='{script_path} {{}}'  "
               "--preview-window=right,wrap "
               "--height=100 "
               "--color='hl:white:underline,hl+:white:underline'")
    with (tempfile.NamedTemporaryFile(delete=False) as input_file,
          tempfile.NamedTemporaryFile() as output_file):
        with open(input_file.name, "w") as f:
            f.write(joined_lines)

        run_cmd(f'cat "{input_file.name}" | fzf {options} > "{output_file.name}"')

        with open(output_file.name) as f:
            return f.read().strip("\n")

if args.preview_line:
    session_id = int(args.preview_line.split(" ")[0])
    session = get_sessions()[session_id]
    out = f"{BLUE}{session.session_id} {session.session_name}{ENDC}\n\n"
    for pane in session.panes:
        out += f"{GREEN}{pane.window_name}{ENDC} {RED}{pane.path}{ENDC}\n"
    print(out.strip())

else:
    lines = []
    for session in get_sessions().values():
        panes = session.panes
        paths = list(set(pane.path for pane in panes))
        paths.sort(key=len)
        windows = list(set(pane.window_name for pane in panes))
        lines.append([
            f"{BLUE}{session.session_id} {session.session_name}{ENDC}",
            f"{RED}{' '.join(paths)}{ENDC}",
            f"{GREEN}{' '.join(windows)}{ENDC}",
            ])
    try:
        line = do_fzf(lines)
        session_id = line.split(" ")[0]
        run_cmd(f"tmux switch-client -t '${session_id}'")
    except subprocess.CalledProcessError:
        pass
