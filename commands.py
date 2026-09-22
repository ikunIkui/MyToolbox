import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class Command:
    name: str
    pattern: re.Pattern
    handler: Callable
    desc: str
    example: str


class CommandRegistry:
    def __init__(self):
        self.commands: list[Command] = []

    def register(self, name: str, pattern: str, desc: str, example: str = ""):
        def deco(fn):
            self.commands.append(
                Command(name, re.compile(pattern), fn, desc, example or desc)
            )
            return fn
        return deco

    def match(self, text: str):
        text = text.strip()
        for cmd in self.commands:
            m = cmd.pattern.match(text)
            if m:
                return cmd, m
        return None, None

    def help_text(self) -> str:
        lines = ["可用命令：", ""]
        for c in self.commands:
            lines.append(f"  {c.example:<30} {c.desc}")
        return "\n".join(lines)