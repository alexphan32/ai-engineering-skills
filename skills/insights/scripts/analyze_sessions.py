#!/usr/bin/env python3
"""
Session Transcript Analyzer for Knowledge Base Building

Parses Claude Code session transcript JSONL files to extract:
- Bug fixes (errors encountered and resolved)
- Performance optimizations (speed, memory improvements)

Also tags each finding with the stack it touched (python-pipeline, go-fiber, nextjs-prisma,
spring-boot, nestjs, fastapi, rust, angular, react, android, ios, flutter, shared-infra,
database), detected from manifest-file and import signals — the same style of detection
`architecture`/`design` use, not hardcoded to any one project.

`arch_decision`, `best_practice`, and `lesson_learned` are NOT auto-classified here — they're
rarely reliable from keyword scoring alone. This script only distinguishes bug_fix vs
perf_optimization vs general; assign the other types by reading the session (Phase 3 CLASSIFY).

Outputs structured JSON findings for downstream consolidation and memory storage.

Usage:
    python analyze_sessions.py --num-sessions 50
    python analyze_sessions.py --num-sessions 5 --dry-run
    python analyze_sessions.py --num-sessions 50 --output custom_output.json
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Configuration ---

# Default paths — auto-detect from CLAUDE_CONFIG_DIR or fall back to ~/.claude
def _default_transcript_dir() -> str:
    """Auto-detect transcript directory from environment or project structure."""
    claude_config = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    cwd = os.getcwd()
    # Derive project slug from cwd path (same algorithm claude-mem uses)
    project_slug = "D--" + cwd.replace(":", "").replace("\\", "-").replace("/", "-")
    candidate = os.path.join(claude_config, "projects", project_slug)

    # Check for new format (subdirectories with subagents/)
    if os.path.isdir(candidate):
        # Check if there are session directories (each containing subagents/)
        session_dirs = [d for d in Path(candidate).iterdir()
                        if d.is_dir() and (d / "subagents").is_dir()]
        if session_dirs:
            return candidate
        # Also accept flat JSONL files (old format)
        jsonl_files = list(Path(candidate).glob("*.jsonl"))
        if jsonl_files:
            return candidate

    # Fallback: search projects/ for the directory whose name best matches cwd
    projects_dir = os.path.join(claude_config, "projects")
    if os.path.isdir(projects_dir):
        best_match = None
        best_score = 0
        cwd_lower = cwd.lower()
        for entry in os.listdir(projects_dir):
            entry_path = os.path.join(projects_dir, entry)
            if not os.path.isdir(entry_path):
                continue

            # Check for new format (subdirectories with subagents/)
            session_dirs = [d for d in Path(entry_path).iterdir()
                            if d.is_dir() and (d / "subagents").is_dir()]
            jsonl_files = list(Path(entry_path).glob("*.jsonl"))
            has_files = bool(session_dirs or jsonl_files)
            if not has_files:
                continue

            # Score by substring match against cwd (e.g., "finx-script5" in slug)
            score = sum(1 for part in cwd_lower.replace("\\", "-").split("-") if part and part in entry.lower())
            if score > best_score:
                best_score = score
                best_match = entry_path
        if best_match:
            return best_match
    return os.path.join(claude_config, "projects")

TRANSCRIPT_DIR = _default_transcript_dir()
REPORTS_DIR = "reports"

# Bug-related keywords (Vietnamese + English), language-agnostic where possible
BUG_KEYWORDS = [
    "fix", "bug", "error", "crash", "lỗi", "sửa",
    "ValueError", "Traceback", "AttributeError", "KeyError", "TypeError",
    "IndexError", "RuntimeError", "AssertionError", "ImportError",
    "NullPointerException", "NullReferenceException", "panic:",
    "unhandled promise rejection", "undefined is not a function",
    "segmentation fault", "SIGSEGV", "deadlock", "race condition",
    "không chạy", "failed", "failure", "exception", "stack trace",
    "sai", "thiếu", "trùng", "duplicate"
]

# Performance keywords
PERF_KEYWORDS = [
    "slow", "optimize", "perf", "bottleneck", "memory", "timeout",
    "OOM", "performance", "speed", "nhanh", "chậm", "tối ưu",
    "batch", "parallel", "cache", "chunk", "lazy", "n+1", "re-render",
    "memory leak", "connection pool"
]

# Stack detection patterns — mirrors the manifest/import signals `architecture`/`design`
# use to auto-detect a project's stack. Order matters: more specific stacks (e.g. fastapi,
# nextjs-prisma) are checked with signals that wouldn't also fire for their broader sibling
# (python-pipeline, react) so ambiguous cases fall back sensibly.
STACK_PATTERNS = {
    "fastapi": [r"fastapi", r"pydantic", r"uvicorn"],
    "nextjs-prisma": [r"next\.config", r"prisma[/\\]schema\.prisma", r"schema\.prisma", r"\bnext\b.*\.tsx?"],
    "nestjs": [r"@nestjs", r"nest-cli\.json"],
    "angular": [r"angular\.json", r"@angular/"],
    "spring-boot": [r"pom\.xml", r"springframework", r"\.java$"],
    "go-fiber": [r"go\.mod", r"gofiber", r"fiber\.New", r"\.go$"],
    "rust": [r"Cargo\.toml", r"\bactix\b", r"\baxum\b", r"\.rs$"],
    "flutter": [r"pubspec\.yaml", r"\.dart$"],
    "ios": [r"\.xcodeproj", r"Podfile", r"\.swift$"],
    "android": [r"AndroidManifest\.xml", r"\.kt$"],
    "react": [r"\breact\b", r"\.jsx$", r"\.tsx$"],
    "python-pipeline": [r"\.py$", r"pyproject\.toml", r"requirements\.txt"],
    "database": [r"\.sql$", r"migrations[/\\]", r"schema\.prisma"],
    "shared-infra": [r"Dockerfile", r"docker-compose", r"\.github[/\\]workflows", r"terraform", r"kubernetes"],
}


def _is_session_dir(path: Path) -> bool:
    """Check if a path is a session directory (new format: contains subagents/)."""
    return path.is_dir() and (path / "subagents").is_dir()


def _get_session_timestamp(session_dir: Path) -> float:
    """Get the timestamp of a session directory (from mtime)."""
    return session_dir.stat().st_mtime


def _get_session_id(session_dir: Path) -> str:
    """Get the session ID from the directory name."""
    return session_dir.name


def _find_subagent_jsonl(session_dir: Path) -> List[Path]:
    """Find all subagent JSONL files in a session directory."""
    subagents_dir = session_dir / "subagents"
    if not subagents_dir.is_dir():
        return []
    return sorted(subagents_dir.glob("*.jsonl"))


# --- Core Logic ---


def find_transcript_files(
    transcript_dir: str, num_sessions: int
) -> List[Path]:
    """Find the N most recent transcript files/sessions."""
    dir_path = Path(transcript_dir)
    if not dir_path.exists():
        print(f"ERROR: Transcript directory not found: {transcript_dir}", file=sys.stderr)
        sys.exit(1)

    # Check for new format (session directories)
    session_dirs = sorted(
        [d for d in dir_path.iterdir() if _is_session_dir(d)],
        key=_get_session_timestamp,
        reverse=True,
    )

    if session_dirs:
        selected = session_dirs[:num_sessions]
        print(f"Found {len(session_dirs)} total session dirs, analyzing {len(selected)} most recent")
        return selected

    # Fallback to old format (flat JSONL files)
    jsonl_files = sorted(
        dir_path.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not jsonl_files:
        print(f"ERROR: No session directories or .jsonl files found in {transcript_dir}", file=sys.stderr)
        sys.exit(1)

    selected = jsonl_files[:num_sessions]
    print(f"Found {len(jsonl_files)} total transcripts, analyzing {len(selected)} most recent")
    return selected


def parse_transcript(file_path: Path) -> List[Dict[str, Any]]:
    """
    Parse a session transcript.
    Handles both:
    - New format: session directories with subagent JSONL files
    - Old format: flat JSONL files
    Returns list of structured events.
    """
    events = []

    if file_path.is_dir():
        # New format: combine all subagent JSONL files
        session_id = _get_session_id(file_path)
        jsonl_files = _find_subagent_jsonl(file_path)

        # First line of first file might be the main entry point
        # Process all subagent files, collect all events
        seen_uuids = set()
        for jf in jsonl_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            # Deduplicate by uuid
                            uuid = event.get("uuid", "")
                            if uuid and uuid in seen_uuids:
                                continue
                            if uuid:
                                seen_uuids.add(uuid)
                            events.append(event)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"Warning: Could not read subagent file {jf.name}: {e}", file=sys.stderr)
    else:
        # Old format: single JSONL file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Warning: Could not read {file_path.name}: {e}", file=sys.stderr)

    return events


def _get_message_text(event: Dict) -> str:
    """Extract text content from an event's message field (handles both formats)."""
    msg = event.get("message", {})
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        # tool_result blocks inside assistant messages (rare)
                        texts.append(str(block.get("output", "")))
            return "\n".join(texts)
    return str(msg)


def extract_user_messages(events: List[Dict]) -> List[str]:
    """Extract user message text from events."""
    messages = []
    for event in events:
        if event.get("type") == "user":
            text = _get_message_text(event)
            if text:
                messages.append(text)
    return messages


def extract_tool_calls(events: List[Dict]) -> List[Dict]:
    """Extract tool call information from events."""
    tool_calls = []
    for event in events:
        # In new format: assistant events have tool_use blocks in content
        if event.get("type") == "assistant":
            msg = event.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_use":
                            tool_calls.append({
                                "tool": block.get("name", "unknown"),
                                "input": block.get("input", {}),
                                "timestamp": event.get("timestamp", ""),
                            })
                        elif block.get("type") == "tool_result":
                            # tool_result embedded in assistant message
                            is_error = block.get("is_error", False)
                            tool_calls.append({
                                "tool": "tool_result",
                                "output": str(block.get("content", ""))[:500],
                                "is_error": is_error,
                                "timestamp": event.get("timestamp", ""),
                            })

        # Old format: standalone tool_result events
        if event.get("type") == "tool_result":
            tool_calls.append({
                "tool": "tool_result",
                "output": str(event.get("output", ""))[:500],
                "is_error": event.get("is_error", False),
                "timestamp": event.get("timestamp", ""),
            })

        # Old format: standalone tool_call events
        if event.get("type") == "tool_call":
            msg = event.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_calls.append({
                            "tool": block.get("name", "unknown"),
                            "input": block.get("input", {}),
                            "timestamp": event.get("timestamp", ""),
                        })

    return tool_calls


def extract_file_paths(events: List[Dict]) -> List[str]:
    """Extract file paths referenced in the session."""
    file_paths = set()
    for event in events:
        text = _get_message_text(event)
        # Find @file references and paths (handle both / and \ path separators)
        paths = re.findall(r'(?:src[\\/]|scripts[\\/]|tests[\\/]|reports[\\/]|docs[\\/])[\w\\/_.-]+\.(?:py|md|json|yaml|yml|csv|txt)', text)
        file_paths.update(p.replace("\\", "/") for p in paths)
        paths = re.findall(r'@([\w\\/_.-]+\.(?:py|md))', text)
        file_paths.update(p.replace("\\", "/") for p in paths)

        # Also extract from tool_use inputs
        if event.get("type") == "assistant":
            msg = event.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        inp = block.get("input", {})
                        file_path = inp.get("file_path", "")
                        if file_path:
                            file_paths.add(file_path.replace("\\", "/"))
                        cmd = inp.get("command", "")
                        if cmd:
                            paths2 = re.findall(r'(?:src[\\/]|scripts[\\/]|tests[\\/])[\w\\/_.-]+\.(?:py|md|json)', cmd)
                            file_paths.update(p.replace("\\", "/") for p in paths2)

    return sorted(file_paths)


def extract_error_messages(events: List[Dict]) -> List[str]:
    """Extract error messages from assistant responses and tool results."""
    errors = []
    for event in events:
        text = _get_message_text(event)

        # Check tool_result blocks for errors (new format)
        if event.get("type") == "assistant":
            msg = event.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_result" and block.get("is_error"):
                            output = str(block.get("content", ""))
                            errors.append(output[:1000])
                        elif block.get("type") == "tool_result":
                            # Check for error in output even if is_error not set
                            output = str(block.get("content", ""))
                            if "error" in output.lower() or "traceback" in output.lower() or "failed" in output.lower():
                                errors.append(output[:1000])

        # Old format: standalone tool_result with is_error
        if event.get("type") == "tool_result" and event.get("is_error"):
            output = str(event.get("output", ""))
            errors.append(output[:1000])

        # Check for Python traceback patterns in text
        if isinstance(text, str):
            traceback_match = re.search(r'(Traceback[\s\S]*?)(?=\n\n|\Z)', text)
            if traceback_match:
                errors.append(traceback_match.group(1)[:1000])

    return errors


def classify_session_type(
    user_messages: List[str],
    tool_calls: List[Dict],
    file_paths: List[str],
    error_messages: List[str],
) -> Tuple[str, float]:
    """
    Classify the session as bug_fix, perf_optimization, or general.
    `arch_decision` / `best_practice` / `lesson_learned` are assigned manually in Phase 3 —
    they aren't reliably distinguishable from a keyword scan alone.
    Returns (type, confidence).
    """
    all_text = " ".join(user_messages).lower()

    scores = {"bug_fix": 0.0, "perf_optimization": 0.0}

    # Score based on keywords in user messages
    for keyword in BUG_KEYWORDS:
        if keyword.lower() in all_text:
            scores["bug_fix"] += 1.0
    for keyword in PERF_KEYWORDS:
        if keyword.lower() in all_text:
            scores["perf_optimization"] += 1.0

    # Boost based on errors present
    if error_messages:
        scores["bug_fix"] += 2.0

    # Find the dominant type
    if max(scores.values()) == 0:
        return ("general", 0.0)

    total = sum(scores.values())
    if total == 0:
        return ("general", 0.0)

    dominant = max(scores, key=scores.get)
    confidence = scores[dominant] / total if total > 0 else 0.0

    # Normalize confidence to 0-1 range
    confidence = min(confidence, 1.0)
    if confidence < 0.3:
        return ("general", confidence)

    return (dominant, confidence)


def detect_stack(file_paths: List[str], user_messages: List[str]) -> str:
    """Detect which stack (see references/taxonomy.md) the session touched."""
    all_text = " ".join(user_messages) + " " + " ".join(file_paths)
    stack_scores = {}

    for stack, patterns in STACK_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = len(re.findall(pattern, all_text, re.IGNORECASE))
            score += matches
        if score > 0:
            stack_scores[stack] = score

    if not stack_scores:
        return "other"

    return max(stack_scores, key=lambda k: stack_scores[k])


def extract_finding(
    session_id: str,
    timestamp: str,
    events: List[Dict],
    user_messages: List[str],
    tool_calls: List[Dict],
    file_paths: List[str],
    error_messages: List[str],
) -> Optional[Dict[str, Any]]:
    """
    Extract a structured finding from a session, if it contains actionable insights.
    """
    session_type, confidence = classify_session_type(
        user_messages, tool_calls, file_paths, error_messages
    )

    if session_type == "general" or confidence < 0.3:
        return None

    stack = detect_stack(file_paths, user_messages)

    # Extract summary from first substantive user message
    summary = ""
    for msg in user_messages:
        msg = msg.strip()
        # Skip very short messages and meta commands
        if len(msg) > 20 and not msg.startswith("/"):
            summary = msg[:200]
            break

    # Extract key symptoms
    symptoms = []
    if error_messages:
        for err in error_messages[:3]:
            # Extract the last line of traceback (the actual error)
            lines = err.strip().split("\n")
            if lines:
                symptoms.append(lines[-1][:200])

    # Extract solution from Edit/Write tool calls
    solution_hints = []
    for tc in tool_calls:
        if tc["tool"] in ("Edit", "Write"):
            inp = tc.get("input", {})
            file_path = inp.get("file_path", "")
            if file_path:
                solution_hints.append(f"Modified: {file_path}")

    # Detect a generic, cross-stack pattern subtype. This is a starting hint only — the
    # actual `pattern` slug saved to a memory file (references/taxonomy.md) is free-form and
    # should be refined by reading the session, not taken verbatim from this heuristic.
    pattern_subtype = "general"
    all_text = " ".join(user_messages).lower() + " " + " ".join(str(s) for s in symptoms).lower()

    if any(kw in all_text for kw in ["duplicate", "trùng"]):
        pattern_subtype = "duplicate-logic"
    elif any(kw in all_text for kw in ["race condition", "concurrent", "deadlock"]):
        pattern_subtype = "race-condition"
    elif any(kw in all_text for kw in ["n+1", "query in a loop", "select n+1"]):
        pattern_subtype = "n-plus-one-query"
    elif any(kw in all_text for kw in ["memory leak", "oom", "out of memory"]):
        pattern_subtype = "memory-leak"
    elif any(kw in all_text for kw in ["null", "undefined", "nullpointer", "nullreference"]):
        pattern_subtype = "null-reference"
    elif any(kw in all_text for kw in ["stale cache", "cache invalidation", "stale data"]):
        pattern_subtype = "stale-cache"
    elif any(kw in all_text for kw in ["re-render", "rerender", "unnecessary render"]):
        pattern_subtype = "unbounded-rerender"
    elif any(kw in all_text for kw in ["auth", "unauthorized", "permission", "token"]):
        pattern_subtype = "auth-issue"
    elif any(kw in all_text for kw in ["config", "env var", "environment variable"]):
        pattern_subtype = "config-drift"
    elif any(kw in all_text for kw in ["dependency", "version conflict", "peer dependency"]):
        pattern_subtype = "dependency-conflict"

    return {
        "session_id": session_id,
        "timestamp": timestamp,
        "type": session_type,
        "subtype": pattern_subtype,
        "stack": stack,
        "summary": summary,
        "symptoms": symptoms[:5],
        "tool_count": len(tool_calls),
        "error_count": len(error_messages),
        "files_modified": list(set(
            tc.get("input", {}).get("file_path", "")
            for tc in tool_calls
            if tc["tool"] in ("Edit", "Write") and tc.get("input", {}).get("file_path")
        )),
        "solution_hints": solution_hints,
        "file_references": file_paths[:20],
        "confidence": round(confidence, 2),
    }


def analyze_sessions(
    transcript_dir: str,
    num_sessions: int,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Main analysis function."""
    files = find_transcript_files(transcript_dir, num_sessions)

    all_findings = []
    sessions_with_findings = 0
    earliest_ts = None
    latest_ts = None

    for i, file_path in enumerate(files):
        # Determine session ID
        if file_path.is_dir():
            session_id = _get_session_id(file_path)
        else:
            session_id = file_path.stem

        print(f"[{i+1}/{len(files)}] Analyzing {session_id[:16]}...", end=" ")

        events = parse_transcript(file_path)
        if not events:
            print("(empty)")
            continue

        # Extract session timestamp from events
        timestamp = None
        for event in events:
            ts = event.get("timestamp", "")
            if ts:
                timestamp = ts
                break

        user_messages = extract_user_messages(events)
        tool_calls = extract_tool_calls(events)
        file_paths_refs = extract_file_paths(events)
        error_messages = extract_error_messages(events)

        finding = extract_finding(
            session_id, timestamp or "", events,
            user_messages, tool_calls, file_paths_refs, error_messages,
        )

        if finding:
            all_findings.append(finding)
            sessions_with_findings += 1
            print(f"[OK] {finding['type']} ({finding['confidence']:.0%})")
            # Track date range
            if timestamp:
                if earliest_ts is None or timestamp < earliest_ts:
                    earliest_ts = timestamp
                if latest_ts is None or timestamp > latest_ts:
                    latest_ts = timestamp
        else:
            print("(no actionable findings)")

        if dry_run and i >= 4:
            break

    # Sort findings by timestamp (newest first)
    all_findings.sort(key=lambda f: f.get("timestamp", ""), reverse=True)

    # Generate metadata
    result = {
        "analysis_metadata": {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "num_sessions_scanned": len(files),
            "num_sessions_with_findings": sessions_with_findings,
            "total_findings": len(all_findings),
            "date_range": {
                "earliest": earliest_ts or "unknown",
                "latest": latest_ts or "unknown",
            },
            "type_breakdown": dict(counter(f["type"] for f in all_findings)),
            "stack_breakdown": dict(counter(f["stack"] for f in all_findings)),
            "pattern_breakdown": dict(counter(f["subtype"] for f in all_findings)),
            "confidence_distribution": {
                "high (>0.7)": sum(1 for f in all_findings if f["confidence"] > 0.7),
                "medium (0.4-0.7)": sum(1 for f in all_findings if 0.4 <= f["confidence"] <= 0.7),
                "low (0.3-0.4)": sum(1 for f in all_findings if f["confidence"] < 0.4),
            },
        },
        "findings": all_findings,
    }

    return result


def counter(items):
    """Simple counter returning dict."""
    counts = defaultdict(int)
    for item in items:
        counts[item] += 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


# --- CLI ---


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Claude Code session transcripts for knowledge base building"
    )
    parser.add_argument(
        "--transcript-dir",
        default=TRANSCRIPT_DIR,
        help=f"Path to transcript directory (default: {TRANSCRIPT_DIR})",
    )
    parser.add_argument(
        "--num-sessions",
        type=int,
        default=50,
        help="Number of most recent sessions to analyze (default: 50)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file path (default: reports/session_analysis_<timestamp>.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only analyze 5 sessions for testing",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.3,
        help="Minimum confidence threshold for findings (default: 0.3)",
    )

    args = parser.parse_args()

    # Run analysis
    result = analyze_sessions(
        transcript_dir=args.transcript_dir,
        num_sessions=5 if args.dry_run else args.num_sessions,
        dry_run=args.dry_run,
    )

    # Filter by confidence
    result["findings"] = [
        f for f in result["findings"]
        if f["confidence"] >= args.min_confidence
    ]
    result["analysis_metadata"]["total_findings"] = len(result["findings"])

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(REPORTS_DIR, exist_ok=True)
        output_path = os.path.join(REPORTS_DIR, f"session_analysis_{timestamp}.json")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Summary output
    meta = result["analysis_metadata"]
    print(f"\n{'='*60}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Sessions scanned: {meta['num_sessions_scanned']}")
    print(f"Sessions with findings: {meta['num_sessions_with_findings']}")
    print(f"Total findings: {meta['total_findings']}")
    print(f"Date range: {meta['date_range']['earliest']} -> {meta['date_range']['latest']}")
    print(f"\nType breakdown: {json.dumps(meta['type_breakdown'], indent=2)}")
    print(f"Stack breakdown: {json.dumps(meta['stack_breakdown'], indent=2)}")
    print(f"Pattern breakdown: {json.dumps(meta['pattern_breakdown'], indent=2)}")
    print(f"\nConfidence distribution: {json.dumps(meta['confidence_distribution'], indent=2)}")
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
