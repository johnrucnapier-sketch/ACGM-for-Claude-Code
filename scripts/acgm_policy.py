"""Platform-neutral ACGM policy. No transcript format or hook output dependencies."""
from __future__ import annotations

import re
import posixpath
from dataclasses import dataclass

FIELDS = (
    "ACGM-EVIDENCE",
    "ACGM-CURRENT-STATE",
    "ACGM-VERIFY-AFTER",
    "ACGM-ROLLBACK",
)

# A field whose value is a template, a shrug, or an inherited claim is absent.
PLACEHOLDER = re.compile(
    r"^\s*(?:<[^>]*>|\(.*\)|todo|tbd|n/?a|none|-+|\.\.\.|待定|略|同上|见上)\s*$",
    re.IGNORECASE,
)
MIN_FIELD_CHARS = 12

# Segment separators that bind separate operations into one invocation.
SEPARATORS = re.compile(r";|&&|\|\||(?<!\|)\|(?!\|)|\n")
# Segments that only prepare the environment are not separate operations.
PREPARATORY = re.compile(r"^\s*(?:cd|export|set|umask|source|\.)\b")
SUBSTITUTION = re.compile(r"\$\(|`")

# Bash that reads without changing state. Used to confirm evidence exists.
READ_ONLY_BASH = re.compile(
    r"^\s*(?:ls|cat|head|tail|wc|stat|file|find|grep|rg|ps|df|du|which|type|env|"
    r"pwd|echo|printf|date|shasum|sha256sum|md5|diff|jq|sort|uniq|awk|sed(?!\s+-i)|"
    r"git\s+(?:status|log|show|diff|ls-tree|ls-files|rev-parse|rev-list|describe|"
    r"branch(?!\s+-[dD])|remote|config\s+--get|cat-file|hash-object|fetch)|"
    r"claude\s+plugin\s+(?:list|details|validate)|npm\s+(?:view|ls)|python3?\s+-c|"
    # Remote inspections. Without these every `ssh host 'uptime'` would reach the
    # gate, and a gate that fires on routine checks is one the operator learns to
    # route around (E-021).
    r"uptime|hostname|whoami|id|nproc|free|lscpu|lsblk|nvcc|"
    r"tmux\s+(?:ls|list-sessions|list-windows|list-panes|has-session)|"
    r"journalctl|systemctl\s+(?:show|status|is-active|is-enabled|list-units)|"
    r"docker\s+(?:ps|images|logs|inspect)|"
    r"kubectl\s+(?:get|describe|logs))\b"
)

# `nvidia-smi` reads, until it is asked to write: -pl sets a power limit, -ac and
# -lgc pin clocks, -pm changes persistence mode, -r resets the device. Listing the
# query forms and requiring the segment to end there keeps the write forms out,
# where a bare `nvidia-smi\b` alternative above would have admitted all of them.
NVIDIA_SMI_READ_ONLY = re.compile(
    r"^\s*nvidia-smi"
    r"(?:\s+(?:-L|--list-gpus|-q|--query|--query-[\w-]+=\S*|--format=\S*|"
    r"-i\s*\S+|--id=\S+|-l\s*\d*|-f\s*\S+))*\s*$"
)

# Remote payloads are rarely one verb. Measured against this operator's own
# history on 2026-09-11, the commonest shapes are polling loops and status
# probes -- `until pgrep -f job; do sleep 10; done`, `for f in a b; do tail $f;
# done`. Per-segment verb matching cannot see that those change nothing, and
# gating them all would have denied 42% of every remote command ever run here.
# That is the rate at which a gate stops being read and starts being routed
# around (E-021), so the structure has to be understood rather than refused.
STRUCTURE = re.compile(r"^\s*(?:do|done|then|else|fi|esac|;;|\{|\}|\(\)|:)\s*$")
# Prefixes that sit in front of the real command without being one. Stripping
# them and classifying what is left is strictly safer than matching on them:
# `sudo rm -rf x` becomes `rm -rf x` and is still refused, while `sudo sshd -T`
# becomes a config dump and stops being treated as an unknown.
PREFIXES = (
    re.compile(r"^\s*(?:do|then|else)\s+"),
    re.compile(r"^\s*(?:while|until|if|elif)\s+"),
    re.compile(r"^\s*sudo(?:\s+-[A-Za-z]+(?:\s+\S+)?)*\s+"),
    re.compile(r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+"),
)
LOOP_HEAD = re.compile(r"^\s*for\s+\w+\s+in\b")
COND_HEAD = re.compile(r"^\s*(?:while|until|if|elif)\s+")
# Read-only verbs that only ever appear inside such payloads.
READ_ONLY_HELPER = re.compile(
    r"^\s*(?:sleep|pgrep|pidof|tr|cut|paste|test|\[|true|false|seq|nl|column|"
    r"basename|dirname|readlink|realpath|numfmt|md5sum|sha1sum|"
    r"ss|ip\s+(?:a|addr|link|route)\b|lsof|netstat|uname|"
    r"systemctl\s+list-unit-files|pip3?\s+(?:show|list|--version)|"
    r"python3?\s+-m\s+pip\s+(?:show|list))\b"
)
# Deliberately absent from that list, each caught by a test: a bare `nvidia-smi`
# would have admitted `nvidia-smi -pl 300`, which rewrites a power limit;
# `watch` and `timeout N` take an arbitrary command as their argument, so
# matching on the wrapper says nothing about what runs underneath it.

READ_ONLY_TOOLS = {"Read", "Grep", "Glob", "NotebookRead", "WebFetch", "WebSearch"}
EVIDENCE_WINDOW = 12


FIELD_COMMENT = re.compile(r"^\s*#\s*(ACGM-[A-Z-]+)\s*[:：]\s*(.*)$")


def split_command(command: str) -> tuple[str, str]:
    """Separate the ACGM field comments from the operation itself.

    The fields live in the command from v0.8. They used to be read from the
    agent's most recent message, which put the check on the wrong side of a race:
    the transcript is not always flushed when the hook runs, so identical calls
    were sometimes accepted and sometimes denied for "missing fields" (E-027).
    Worse, a stale read surfaced an *earlier* turn's fields and authorised an
    operation they were never written for (E-025).

    The command is the one thing the hook always receives intact, and it is the
    thing being authorised. Fields carried on it cannot be stale, cannot be
    missing due to timing, and cannot belong to a different call.
    """
    fields, rest = [], []
    for line in command.splitlines():
        (fields if FIELD_COMMENT.match(line) else rest).append(line)
    return "\n".join(fields), "\n".join(rest)


def missing_fields(field_block: str) -> list[str]:
    present = {}
    for line in field_block.splitlines():
        match = FIELD_COMMENT.match(line)
        if match:
            present[match.group(1)] = match.group(2).strip().strip("`").strip()
    absent = []
    for field in FIELDS:
        value = present.get(field, "")
        if len(value) < MIN_FIELD_CHARS or PLACEHOLDER.match(value):
            absent.append(field)
    return absent


# Words that name the tool, not the thing being operated on.
NOT_A_TARGET = {
    "sudo", "env", "time", "xargs", "git", "npm", "pip", "brew", "claude", "plugin",
    "marketplace", "systemctl", "launchctl", "install", "uninstall", "update",
    "remove", "enable", "disable", "reset", "clean", "push", "force", "branch",
    "checkout", "rebase", "stash", "drop", "clear", "table", "database", "from",
    "delete", "truncate", "shred", "rmdir", "pkill", "shutdown", "reboot", "mkfs",
    "filter", "refresh", "global", "recursive", "hard",
}
TOKEN = re.compile(r"[A-Za-z0-9_.@:~/-]{3,}")


def target_tokens(command: str) -> list[str]:
    """Words from the command that name what it acts on.

    Used to bind the four fields to *this* operation. Flags and the names of the
    tools themselves are excluded; what remains is paths, ids, branch names and
    similar operands.
    """
    # The shell filter already stripped heredoc bodies and /dev/null redirects
    # before deciding this was destructive; here the raw invocation is fine,
    # because any token in it is still a token of *this* call.
    tokens = []
    for raw in TOKEN.findall(command):
        word = raw.strip("'\"`,;")
        if not word or word.startswith("-"):
            continue
        if word.lower() in NOT_A_TARGET:
            continue
        if any(ch in word for ch in "/@:") or len(word) >= 5:
            tokens.append(word)
    return tokens


def fields_name_this_target(text: str, command: str) -> bool:
    """True if the fields mention something the command actually acts on.

    Without this, the gate can be satisfied by evidence written for an earlier
    operation: the fields stay the most recent assistant text, so the next
    destructive call inherits them. Observed 2026-08-05 — a command passed on
    fields written for the previous one, and the pass was initially misread as
    the command not being destructive at all.

    A basename also counts, so a field may cite a path in a different but
    equivalent form.
    """
    tokens = target_tokens(command)
    if not tokens:
        return True  # nothing identifiable to bind to; do not invent a failure
    haystack = text.lower()
    for token in tokens:
        needle = token.lower()
        if needle in haystack:
            return True
        base = needle.rstrip("/").rsplit("/", 1)[-1]
        if len(base) >= 4 and base in haystack:
            return True
    return False


def split_segments(command: str) -> list[str]:
    """Split on shell separators, ignoring any that sit inside quotes.

    A ';' or a newline inside a quoted argument is data, not an operation
    boundary -- the shell does not treat it as one either. Splitting on it made a
    single `python3 -c "..."` look like twenty-two operations, and STANDALONE
    then had no satisfiable form: no way of writing that command could pass. A
    gate that states an impossible requirement teaches the operator to route
    around it (E-021), which is the failure this project is least able to afford.

    Note what is deliberately *not* done here: the quoted body is not stripped
    before the destructive filter runs. `sh -c "rm -rf /"` carries its verb
    inside quotes, and dropping it would trade a false positive for a false
    negative. Per this gate's own policy, misses are the worse error.

    Unbalanced quotes fall back to the naive split, which over-segments. That
    direction can only deny, never permit.
    """
    segments: list[str] = []
    current: list[str] = []
    quote = ""
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            if char == "\\" and quote == '"' and index + 1 < len(command):
                current.append(char)
                current.append(command[index + 1])
                index += 2
                continue
            if char == quote:
                quote = ""
            current.append(char)
            index += 1
            continue
        if char in "'\"":
            quote = char
            current.append(char)
            index += 1
            continue
        if char in ";\n":
            segments.append("".join(current))
            current = []
            index += 1
            continue
        if command.startswith("&&", index) or command.startswith("||", index):
            segments.append("".join(current))
            current = []
            index += 2
            continue
        # A lone ampersand also starts another command. Keep descriptor
        # redirects (>&, <&, &>) intact instead of treating them as background.
        if char == "|" or (char == "&" and
                (index == 0 or command[index - 1] not in "><") and
                not command.startswith("&>", index)):
            segments.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    if quote:
        return SEPARATORS.split(command)
    segments.append("".join(current))
    return segments


def operative_segments(command: str) -> list[str]:
    """Segments that actually do something, ignoring environment setup."""
    return [
        segment.strip()
        for segment in split_segments(command)
        if segment.strip() and not PREPARATORY.match(segment)
    ]


def bash_is_read_only(command: str) -> bool:
    """Reuse the remote payload policy; transports never enter the verb list."""
    _, command = split_command(command)
    segments = [s.strip() for s in split_segments(command) if s.strip() and not re.match(r"^cd\s+", s.strip())]
    if not segments:
        return False
    for segment in segments:
        remote = parse_remote(segment)
        if remote:
            if remote.error or remote.kind != "ssh" or not remote.payload:
                return False
            if not payload_is_read_only(remote.payload):
                return False
        elif not payload_is_read_only(segment):
            return False
    return True


def shell_words(text: str) -> list[tuple[str, bool]] | None:
    """Bounded shell lexer: preserve quoted operators, reject malformed input."""
    words = []
    current = []
    quote = ""
    quoted = started = False
    index = 0
    def flush():
        nonlocal current, quoted, started
        if started:
            words.append(("".join(current), quoted))
        current, quoted, started = [], False, False
    while index < len(text):
        ch = text[index]
        if ch == "\\" and quote != "'":
            if index + 1 == len(text):
                return None
            index += 1
            current.append(text[index])
            started = True
        elif quote:
            if ch == quote:
                quote = ""
            else:
                current.append(ch)
        elif ch in "'\"":
            quote, quoted, started = ch, True, True
        elif ch.isspace():
            flush()
        elif ch in ";&|<>()":
            flush()
            op = ch
            while index + 1 < len(text) and text[index + 1] in ";&|<>()":
                index += 1
                op += text[index]
            words.append((op, False))
        elif ch == "#" and not started:
            break
        else:
            current.append(ch)
            started = True
        index += 1
    if quote:
        return None
    flush()
    return words


@dataclass(frozen=True)
class Remote:
    kind: str
    host: str = ""
    payload: str = ""
    error: str = ""


def command_words(segment: str) -> list[tuple[str, bool]] | None:
    words = shell_words(segment)
    if words is None:
        return None
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0][0]):
        words = words[1:]
    if words and posixpath.basename(words[0][0]) in ("sudo", "command", "env"):
        wrapper = posixpath.basename(words.pop(0)[0])
        while words and words[0][0].startswith("-"):
            option = words.pop(0)[0]
            if wrapper == "sudo" and option in ("-u", "-g"):
                if not words:
                    return None
                words.pop(0)
            elif option not in ("--", "-n", "-E", "-H"):
                return None
        while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0][0]):
            words.pop(0)
    if words:
        words[0] = (posixpath.basename(words[0][0]), words[0][1])
    return words


def parse_remote(segment: str) -> Remote | None:
    words = command_words(segment)
    if not words:
        # Malformed known transport must not disappear during tokenization.
        if re.search(r"(?:^|\s)(?:/\S*/)?(?:ssh|scp|rsync)\b", segment):
            return Remote("ssh", error="unparseable remote command")
        return None
    kind = words[0][0]
    if kind not in ("ssh", "scp", "rsync"):
        return None
    if SUBSTITUTION.search(segment):
        return Remote(kind, error="computed remote transport")
    if kind != "ssh":
        allowed = {"-a", "-r", "-v", "--delete", "--dry-run", "-n"} if kind == "rsync" else {"-r", "-p", "-q", "-v"}
        if any(w.startswith("-") and w not in allowed for w, _ in words[1:]):
            return Remote(kind, error="unsupported transfer option")
        return Remote(kind, payload=segment)
    index = 1
    while index < len(words) and words[index][0].startswith("-"):
        flag = words[index][0]
        if flag == "--":
            index += 1
            break
        if flag in ("-T", "-t", "-tt", "-n", "-q", "-v", "-vv", "-vvv", "-4", "-6"):
            index += 1
            continue
        option = flag[:2]
        if option not in ("-p", "-i", "-l", "-o"):
            return Remote(kind, error="unsupported SSH option or identity override")
        if len(flag) > 2:
            value = flag[2:]
        else:
            index += 1
            if index >= len(words):
                return Remote(kind, error="missing SSH option value")
            value = words[index][0]
        if option == "-o":
            key = re.split(r"[=\s]", value, maxsplit=1)[0].lower()
            if key not in ("connecttimeout", "batchmode", "serveraliveinterval",
                           "serveralivecountmax", "stricthostkeychecking"):
                return Remote(kind, error="unsupported SSH option or identity override")
        index += 1
    if index >= len(words):
        return Remote(kind, error="missing SSH host")
    host = words[index][0]
    if not re.fullmatch(r"(?:[\w.-]+@)?[\w.-]+", host):
        return Remote(kind, error="nonliteral SSH host")
    rest = words[index + 1:]
    # Outer redirects execute locally, never inside the remote payload.
    if any(not quoted and re.search(r"[<>&|;()]", word) for word, quoted in rest):
        return Remote(kind, host, error="unsupported outer SSH shell operator")
    payload = " ".join(word for word, _ in rest)
    if shell_words(payload) is None:
        return Remote(kind, error="unparseable SSH payload")
    return Remote(kind, host.rsplit("@", 1)[-1], payload)


def ssh_payload(segment: str) -> str | None:
    remote = parse_remote(segment)
    if remote is None or remote.error:
        return ""
    return remote.payload or None


def payload_is_read_only(payload: str) -> bool:
    """Whether a remote payload only reads, understanding shell structure.

    This single policy is shared by remote routing and prior Bash evidence.

    A command substitution makes the answer unknowable from the text, and
    unknowable is not read-only.
    """
    if not payload.strip() or SUBSTITUTION.search(payload) or shell_words(payload) is None:
        return False
    if unsafe_read_syntax(payload):
        return False
    segments = [segment.strip() for segment in split_segments(payload) if segment.strip()]
    if any(re.match(r"^(?:source|\.|export|set|umask)\s", segment) for segment in segments):
        return False
    segments = [segment for segment in segments if not re.match(r"^cd\s+", segment)]
    if not segments:
        return False
    for segment in segments:
        if STRUCTURE.match(segment) or LOOP_HEAD.match(segment):
            continue
        stripped = segment
        for _ in range(6):  # bounded: `do sudo VAR=1 cmd` nests, runaway does not
            before = stripped
            for prefix in PREFIXES:
                stripped = prefix.sub("", stripped, count=1)
            if stripped == before:
                break
        if not stripped.strip():
            continue
        words = command_words(stripped)
        if not words or not safe_read_options(words):
            return False
        stripped = " ".join(word for word, _ in words)
        if (
            READ_ONLY_BASH.match(stripped)
            or READ_ONLY_HELPER.match(stripped)
            or NVIDIA_SMI_READ_ONLY.match(stripped)
        ):
            continue
        return False
    return True


def remote_needs_gate(command: str) -> bool:
    for segment in operative_segments(command):
        remote = parse_remote(segment)
        if not remote:
            continue
        if remote.error:
            return True
        if remote.kind in ("scp", "rsync"):
            if remote.kind == "rsync" and transfer_is_dry_run(segment):
                continue
            return True
        if remote.payload and not payload_is_read_only(remote.payload):
            return True
    return False


def transfer_is_dry_run(segment: str) -> bool:
    words = command_words(segment)
    if not words or words[0][0] != "rsync":
        return False
    # Deliberately narrow: arbitrary remote-shell/options can execute code even
    # during a transfer dry run. Never interpret scp -n as a dry run.
    found = False
    for word, _ in words[1:]:
        if word in ("--dry-run", "-n"):
            found = True
        elif word.startswith("-") and word not in ("-a", "-r", "-v", "--delete"):
            return False
    return found


def unsafe_read_syntax(command: str) -> bool:
    words = shell_words(command)
    if words is None:
        return True
    for i, (word, quoted) in enumerate(words):
        if not quoted and word in ("&", "(", ")", "()"):
            return True
        if not quoted and ("<" in word or ">" in word):
            # Only exact descriptor duplication / /dev/null output is harmless.
            following = words[i + 1][0] if i + 1 < len(words) else ""
            if word in (">", ">>") and following == "/dev/null":
                continue
            if word == ">&" and following.isdigit():
                continue
            return True
    return False


def journal_query_options(args: list[str], show: bool = False) -> bool:
    """Finite query argv only; unknown flags never inherit read-only status."""
    flags = {"--no-pager", "--all", "-a", "--quiet", "-q"}
    values = {"-p", "--property"} if show else {
        "-u", "--unit", "-S", "--since", "-U", "--until", "-n", "--lines",
        "-p", "--priority", "-o", "--output", "--boot"}
    flags |= {"--value"} if show else {
        "-b", "-f", "--follow", "-r", "--reverse", "--utc", "--no-hostname",
        "--list-boots", "--disk-usage"}
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in flags:
            index += 1
            continue
        option, sep, value = arg.partition("=")
        if option in values:
            if not sep:
                index += 1
                if index >= len(args):
                    return False
                value = args[index]
            if not value or value.startswith("-") or re.search(r"[$*?\[\]`~]", value):
                return False
        elif not (show and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@:-]*", arg)):
            return False
        index += 1
    return True


def safe_read_options(words: list[tuple[str, bool]]) -> bool:
    verb = words[0][0]
    args = [w for w, _ in words[1:]]
    if verb == "journalctl":
        return journal_query_options(args)
    if verb == "systemctl" and args[:1] == ["show"]:
        return journal_query_options(args[1:], show=True)
    # The legacy prefix regex includes executable/side-effectful variants. They
    # must not certify a mutation as evidence or a remote inspection.
    # Complex evaluators, output helpers and client configuration can execute or
    # write through options. Unknown forms are deliberately not read evidence.
    if verb in ("python", "python3", "awk", "env", "find", "sed", "sort",
                "jq", "file", "ip", "ss", "lsof", "npm", "pip", "pip3",
                "kubectl"):
        return False
    if verb in ("date", "uniq", "nvcc") and any(re.search(r"[$*?\[\]`~]", a) for a in args):
        return False
    if verb == "claude":
        return args == ["plugin", "list"]
    if verb == "date":
        return args in ([], ["-u"], ["--utc"]) or (len(args) == 1 and args[0].startswith("+"))
    if verb == "uniq":
        return len(args) <= 1 and all(not a.startswith("-") or a == "-" for a in args)
    if verb == "nvcc":
        return args == ["--version"]
    if verb == "hostname":
        return args in ([], ["-f"], ["-s"], ["-d"], ["-i"], ["-I"])
    if verb == "rg":
        # --pre runs a program; configuration can silently supply it.
        return False
    if verb == "git":
        return bool(args) and args[0] == "status" and all(
            a in ("--short", "-s", "--porcelain", "--porcelain=v1", "--porcelain=v2", "--branch", "-b")
            for a in args[1:])
    if verb == "tmux":
        return args in (["ls"], ["list-sessions"], ["list-windows"], ["list-panes"], ["has-session"])
    if verb == "docker":
        return bool(args) and args[0] in ("ps", "images", "logs", "inspect") and all(
            not a.startswith("-") or a in ("-a", "--all", "-q", "--quiet", "--no-trunc") for a in args[1:])
    if verb == "nvidia-smi" and any(a.startswith(("-f", "--filename")) for a in args):
        return False
    return True


@dataclass(frozen=True)
class ToolCall:
    name: str
    command: str = ""
    path: str = ""
    call_id: str = ""
    succeeded: bool = False
    started: int = -1
    finished: int = -1


def load_guards(path: str) -> list[tuple[str, str]]:
    """Explicit JSON config only; absence is optional, invalid presence is fatal."""
    import json
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or set(data) != {"remote_path_guards"}:
        raise ValueError("expected remote_path_guards configuration")
    guards = data["remote_path_guards"]
    if not isinstance(guards, list):
        raise ValueError("remote_path_guards must be a list")
    result = []
    for guard in guards:
        if not isinstance(guard, dict) or set(guard) != {"host", "prefixes"}:
            raise ValueError("guard requires host and prefixes")
        host, prefixes = guard["host"], guard["prefixes"]
        if not isinstance(host, str) or not re.fullmatch(r"[\w.-]+", host):
            raise ValueError("host must be a literal SSH alias")
        if not isinstance(prefixes, list) or not prefixes:
            raise ValueError("prefixes must be a nonempty list")
        for prefix in prefixes:
            if not isinstance(prefix, str) or not prefix.startswith("/") or re.search(r"[$*?\[\]`\n]", prefix):
                raise ValueError("prefix must be an absolute literal path")
            normalized = posixpath.normpath(prefix)
            if normalized == "/" or normalized.startswith("//"):
                raise ValueError("root and double-slash prefixes are unsupported")
            for other_host, other_prefix in result:
                if other_host != host and (under(normalized, other_prefix) or under(other_prefix, normalized)):
                    raise ValueError("overlapping prefixes have conflicting hosts")
            result.append((host, normalized))
    return result


def under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def literal_path(word: str, cwd: str = "") -> str | None:
    if re.search(r"[$*?\[\]`~]", word):
        return None
    if word.startswith("/"):
        return posixpath.normpath(word)
    if cwd and word and not word.startswith("-"):
        return posixpath.normpath(posixpath.join(cwd, word))
    return None


WRITE_VERBS = {"cp", "mv", "rm", "mkdir", "touch", "chmod", "chown", "truncate", "install", "tee", "rmdir", "shred"}
TEXT_VERBS = {"echo", "printf", "grep", "rg"}


def referenced_paths(segment: str, cwd: str = "") -> set[str]:
    words = command_words(segment)
    if not words:
        return set()
    return {p for w, _ in words[1:] if (p := literal_path(w.split("=", 1)[-1] if w.startswith("--") and "=" in w else w, cwd))}


def execution_problems(command: str, guards: list[tuple[str, str]], local_cwd: str = "") -> list[str]:
    """Hard context denials: fields/evidence cannot waive these."""
    problems = []
    cwd = local_cwd
    for segment in split_segments(command):
        words = command_words(segment)
        if words and words[0][0] == "cd" and len(words) == 2:
            cwd = literal_path(words[1][0], cwd) or ""
            continue
        remote = parse_remote(segment)
        if remote and remote.error:
            problems.append("REMOTE-PARSE — " + remote.error)
            continue
        if remote and remote.kind == "ssh":
            # Nested/opaque transport cannot inherit the outer host identity.
            if re.search(r"(?:^|\s)(?:ssh|scp|rsync)\s", remote.payload):
                problems.append("REMOTE-PARSE — nested transport is unsupported")
            if not payload_is_read_only(remote.payload) and re.search(r"[$*?\[\]`]|<<", remote.payload):
                problems.append("REMOTE-PARSE — computed or unsupported remote write target")
            remote_paths = {p for _, p in operation_targets(remote.payload)}
            if not payload_is_read_only(remote.payload):
                for word, _ in shell_words(remote.payload) or []:
                    if " " in word:
                        remote_paths |= {posixpath.normpath(p) for p in re.findall(r"/[^\s'\";]+", word)}
            for host, prefix in guards:
                if any(under(p, prefix) for p in remote_paths) and remote.host != host:
                    problems.append(f'HOST — This path belongs to remote host "{host}", not "{remote.host}".')
            continue
        if remote:  # transfers: host:path operands, local operands remain local
            for word, _ in (words or [])[1:]:
                match = re.fullmatch(r"(?:[\w.-]+@)?([\w.-]+):(/.*)", word)
                for host, prefix in guards:
                    candidate = posixpath.normpath(match[2] if match else word)
                    if under(candidate, prefix) and (not match or match[1] != host):
                        problems.append(f'HOST — This path belongs to remote host "{host}". Execute through the configured remote transport.')
            continue
        if not guards:
            continue
        if not words:
            if any(prefix in segment for _, prefix in guards):
                problems.append("CONTEXT — unparseable command contains a protected remote path")
            continue
        verb = words[0][0]
        paths = referenced_paths(segment, cwd)
        redirect_paths = set()
        for i, (word, quoted) in enumerate(words):
            if not quoted and ">" in word and i + 1 < len(words):
                p = literal_path(words[i + 1][0], cwd)
                if p:
                    redirect_paths.add(p)
        mutation = verb in WRITE_VERBS or (verb == "sed" and any(w.startswith(("-i", "--in-place")) for w, _ in words[1:]))
        # Unknown wrappers do not gain remote write privileges. Known textual
        # commands only write where their redirect points, never at search text.
        if not mutation and not SUBSTITUTION.search(segment) and (verb in TEXT_VERBS or payload_is_read_only(segment)):
            paths = redirect_paths
        else:
            paths |= redirect_paths
            # Opaque code arguments cannot claim the textual exemption given to
            # echo/printf/grep. This is a denial, never remote authorization.
            for word, _ in words[1:]:
                if " " in word:
                    paths |= {posixpath.normpath(p) for p in re.findall(r"/[^\s'\";]+", word)}
        for host, prefix in guards:
            if any(under(p, prefix) for p in paths):
                problems.append(f'CONTEXT — This path belongs to remote host "{host}". Execute through the configured remote transport.')
    return problems


def operation_targets(command: str) -> set[tuple[str, str]]:
    """Literal absolute targets (and explicitly cd-resolved targets), host-bound."""
    _, operation = split_command(command)
    targets = set()
    cwd = ""
    for segment in split_segments(operation):
        words = command_words(segment)
        if not words:
            continue
        if words[0][0] == "cd" and len(words) == 2:
            cwd = literal_path(words[1][0], cwd) or ""
            continue
        remote = parse_remote(segment)
        if remote:
            if remote.error:
                continue
            if remote.kind == "ssh":
                targets |= {(remote.host, p) for _, p in operation_targets(remote.payload)}
            else:
                for word, _ in words[1:]:
                    match = re.fullmatch(r"(?:[\w.-]+@)?([\w.-]+):(/.*)", word)
                    if match:
                        targets.add((match[1], posixpath.normpath(match[2])))
                    elif word.startswith("/"):
                        targets.add(("", posixpath.normpath(word)))
        else:
            targets |= {("", p) for p in referenced_paths(segment, cwd)}
    return targets


def evidence_targets(command: str) -> set[tuple[str, str]]:
    """Only inspection operands count. Echo/printf/search patterns are not reads."""
    _, command = split_command(command)
    targets = set()
    cwd = ""
    for segment in split_segments(command):
        words = command_words(segment)
        if not words:
            continue
        verb = words[0][0]
        if any(w in ("--help", "--version") for w, _ in words[1:]):
            continue
        if verb == "cd" and len(words) == 2:
            cwd = literal_path(words[1][0], cwd) or ""
            continue
        remote = parse_remote(segment)
        if remote:
            if not remote.error and remote.kind == "ssh":
                targets |= {(remote.host, p) for _, p in evidence_targets(remote.payload)}
            continue
        if verb in ("echo", "printf", "test", "[", "true", "false"):
            continue
        if verb in ("grep", "rg"):
            # Only explicit -- pattern files is supported for strong evidence.
            args = [w for w, _ in words[1:]]
            if "--" not in args:
                continue
            words = [(verb, False)] + [(w, False) for w in args[args.index("--") + 2:]]
        if verb not in ("stat", "ls", "cat", "head", "tail", "sha256sum", "shasum", "md5sum", "md5", "file", "wc", "find", "du", "readlink", "realpath", "grep", "rg", "git"):
            continue
        args = [w for w, _ in words[1:]]
        skip = False
        for word in args:
            if skip:
                skip = False
                continue
            if word in ("-c", "-f", "--format", "--printf", "-n", "--lines", "--bytes", "--ignore", "--exclude", "-I"):
                skip = True
                continue
            if word.startswith("-"):
                continue
            if p := literal_path(word, cwd):
                targets.add(("", p))
        if cwd and verb == "git":
            targets.add(("", cwd))
    return targets


def has_prior_evidence(calls: list[ToolCall], gated_command: str = "", current_id: str = "") -> bool:
    # Remove the current call BEFORE applying the fixed 12-call window. Only
    # tool calls count; prose/results/hook helper processes do not consume it.
    prior = calls
    if prior and ((current_id and prior[-1].call_id == current_id) or
                  (not current_id and prior[-1].name == "Bash" and prior[-1].command == gated_command)):
        prior = prior[:-1]
    prior = prior[-EVIDENCE_WINDOW:]
    targets = operation_targets(gated_command)
    observed = set()
    any_read = False
    for call in prior:
        if not call.succeeded:
            continue
        if call.name == "Bash" and bash_is_read_only(call.command):
            any_read = True
            observed |= evidence_targets(call.command)
        elif call.name in READ_ONLY_TOOLS:
            any_read = True
            if call.name in ("Read", "NotebookRead") and (p := literal_path(call.path)):
                observed.add(("", p))
    if targets:
        return all((host, path) in observed or (host, posixpath.dirname(path)) in observed for host, path in targets)
    # Preserve non-filesystem legacy gates (plugin ids, git refs). Remote calls
    # with unresolved targets cannot borrow unrelated evidence.
    for segment in operative_segments(split_command(gated_command)[1]):
        words = command_words(segment)
        if parse_remote(segment) or (words and words[0][0] in WRITE_VERBS):
            return False
    return any_read
