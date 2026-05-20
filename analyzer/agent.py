import json
import time
import anthropic
from .agent_tools import (find_callers, find_callees, get_call_chain,
                           read_function, read_header, search_code)

MAX_TOOL_CALLS = 4

# ── Tool schemas (Anthropic format) ──────────────────────────────────────────
TOOL_SCHEMAS = [
    {
        "name": "find_callers",
        "description": (
            "Find all functions that directly call the given function. "
            "Only use this if the pre-provided call graph is missing a function you need."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "function_name": {"type": "string", "description": "Function to find callers of"}
            },
            "required": ["function_name"],
        },
    },
    {
        "name": "find_callees",
        "description": (
            "Find all functions that the given function calls. "
            "Only use this if the pre-provided call graph is missing a function you need."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "function_name": {"type": "string", "description": "Function to find callees of"}
            },
            "required": ["function_name"],
        },
    },
    {
        "name": "get_call_chain",
        "description": (
            "Trace all callers recursively up to `depth` levels. "
            "Only use this if the pre-provided call graph is insufficient."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "function_name": {"type": "string", "description": "Starting function"},
                "depth": {"type": "integer", "description": "Levels to trace upward (default 3, max 5)"},
            },
            "required": ["function_name"],
        },
    },
    {
        "name": "read_function",
        "description": (
            "Read the full source code of a function. "
            "Always call this on the changed function(s) to inspect the actual implementation. "
            "Also call it on high-risk callers to verify real impact beyond what the call graph shows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "function_name": {"type": "string", "description": "Function whose body to read"}
            },
            "required": ["function_name"],
        },
    },
    {
        "name": "read_header",
        "description": (
            "Read the .h header file where a function is declared. "
            "Use this to check documented contracts (e.g. caller-must-free, thread safety)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "function_name": {"type": "string", "description": "Function whose header to read"}
            },
            "required": ["function_name"],
        },
    },
    {
        "name": "search_code",
        "description": (
            "Search all .c and .h files in the project for a regex pattern. "
            "Use this to find function pointer assignments, macro usages, or "
            "any pattern not visible in the call graph."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"}
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "submit_impact_report",
        "description": (
            "Submit your final impact analysis. "
            "Call this as soon as you have enough information — aim for 1-2 tool calls before this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "changed_functions": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Functions whose body was directly modified",
                },
                "affected_functions": {
                    "type": "array", "items": {"type": "string"},
                    "description": "All functions transitively impacted by the change",
                },
                "bugs_introduced": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Concrete bugs or risks, one string per issue",
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "concerns": {
                    "type": "string",
                    "description": "2-3 sentences: what changed, what breaks, and why",
                },
            },
            "required": ["changed_functions", "affected_functions", "severity", "concerns"],
        },
    },
]

# ── OpenAI format (auto-converted from Anthropic schemas) ─────────────────────
TOOL_SCHEMAS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in TOOL_SCHEMAS
]

SYSTEM_PROMPT = """\
You are a senior C software engineer performing code impact analysis.
The diff and the FULL call graph are already provided in the user message.

Your process:
1. Read the diff and call graph to identify changed functions and all transitively affected callers.
2. Call read_function on the changed function(s) to inspect the actual implementation — look for
   memory ownership issues, off-by-one errors, null pointer risks, contract violations, or any
   subtle logic that the diff alone does not make obvious.
3. If an affected caller looks risky (e.g. it frees memory, has error handling, or is called
   frequently), call read_function on that caller too to verify the real impact.
4. Call search_code if you see function pointers, macros, or #ifdef in the diff or source.
5. Once you have read the key implementations and understand the full impact, call submit_impact_report.

You have up to 4 tool calls. Use read_function on 1-2 functions, then submit.
Your final action must always be submit_impact_report."""


# ── Tool executor (shared by both providers) ──────────────────────────────────

def _execute_tool(name: str, args: dict, cg, project_files: list):
    if name == "find_callers":
        return find_callers(args["function_name"], cg)
    elif name == "find_callees":
        return find_callees(args["function_name"], cg)
    elif name == "get_call_chain":
        return get_call_chain(args["function_name"], args.get("depth", 3), cg)
    elif name == "read_function":
        return read_function(args["function_name"], cg)
    elif name == "read_header":
        return read_header(args["function_name"], project_files)
    elif name == "search_code":
        return search_code(args["pattern"], project_files)
    return f"Unknown tool: {name}"


def _tool_result_str(result) -> str:
    return json.dumps(result) if not isinstance(result, str) else result


# ── Anthropic API call with retry ─────────────────────────────────────────────

def _call_anthropic(client, model: str, messages: list, call_num: int,
                    max_retries: int = 4):
    print(f"    [agent] API call #{call_num} ...", flush=True)
    wait = 15
    for attempt in range(max_retries + 1):
        try:
            return client.messages.create(
                model=model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
        except anthropic.AuthenticationError:
            raise RuntimeError(
                "Invalid Anthropic API key. "
                "Update it with: python graphguard.py config --anthropic-key <your-key>"
            ) from None
        except anthropic.BadRequestError as e:
            if "credit balance" in str(e) or "billing" in str(e).lower():
                raise RuntimeError(
                    "Anthropic API credits exhausted. "
                    "Add credits at console.anthropic.com/settings/billing"
                ) from None
            raise
        except anthropic.RateLimitError as e:
            if attempt == max_retries:
                raise
            retry_after = None
            try:
                retry_after = int(e.response.headers.get("retry-after", 0))
            except Exception:
                pass
            delay = retry_after if retry_after and retry_after > 0 else wait
            print(f"    [agent] Rate limit - waiting {delay}s "
                  f"(retry {attempt + 1}/{max_retries})...", flush=True)
            time.sleep(delay)
            wait = min(wait * 2, 60)


# ── OpenAI API call ───────────────────────────────────────────────────────────

def _call_openai(client, model: str, messages: list, call_num: int):
    print(f"    [agent] API call #{call_num} ...", flush=True)
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOL_SCHEMAS_OPENAI,
        tool_choice="auto",
        temperature=0,
    )


# ── Main agent loop ───────────────────────────────────────────────────────────

def run_agent(diff_text: str, changed_fns: set, cg, project_files: list,
              client, model: str, provider: str = "anthropic",
              cg_content: str = "") -> dict:
    """
    Run the agent loop for either Anthropic or OpenAI.
    cg_content: pre-built call graph context string (from build_diff_with_graph).
                When provided, the agent starts with full graph knowledge and
                skips find_callers / get_call_chain tool calls entirely.
    Returns the arguments passed to submit_impact_report as the final result.
    """
    if cg_content:
        initial_content = (
            f"{cg_content}\n\n"
            f"Functions directly modified: {sorted(changed_fns) if changed_fns else '(parse from diff)'}\n\n"
            f"Use the call graph to identify affected functions, then call read_function on the "
            f"changed function(s) to inspect the actual implementation for bugs or risks. "
            f"Read key callers if they look risky. Then submit your report."
        )
    else:
        initial_content = (
            f"Git diff:\n{diff_text}\n\n"
            f"Functions directly modified: {sorted(changed_fns) if changed_fns else '(parse from diff)'}\n\n"
            f"Trace the full impact using the available tools, then call submit_impact_report."
        )

    tool_log: list[str] = []
    api_call_count = 0
    total_tool_calls = 0

    # ── OpenAI loop ───────────────────────────────────────────────────────────
    if provider == "openai":
        messages: list = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": initial_content},
        ]

        while True:
            api_call_count += 1
            response = _call_openai(client, model, messages, api_call_count)
            choice = response.choices[0]
            msg    = choice.message

            # Append assistant turn (must include tool_calls if present)
            asst: dict = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                asst["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(asst)

            # No tool calls — agent finished without submit_impact_report
            if not msg.tool_calls or choice.finish_reason == "stop":
                return {
                    "changed_functions": sorted(changed_fns),
                    "affected_functions": [],
                    "bugs_introduced": [],
                    "severity": "unknown",
                    "concerns": msg.content or "Agent ended without submitting a report.",
                    "_tool_log": tool_log,
                }

            final_report = None

            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                tool_log.append(name)
                total_tool_calls += 1

                print(f"    [agent] {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})",
                      flush=True)

                if total_tool_calls >= MAX_TOOL_CALLS and name != "submit_impact_report":
                    print(f"    [agent] Tool call limit ({MAX_TOOL_CALLS}) reached - forcing report",
                          flush=True)
                    content = "Tool call limit reached. Call submit_impact_report now."
                elif name == "submit_impact_report":
                    args["_tool_log"] = tool_log
                    final_report = args
                    content = "Report submitted."
                else:
                    content = _tool_result_str(_execute_tool(name, args, cg, project_files))

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                })

            if final_report:
                return final_report

    # ── Anthropic loop ────────────────────────────────────────────────────────
    else:
        messages = [{"role": "user", "content": initial_content}]

        while True:
            api_call_count += 1
            response = _call_anthropic(client, model, messages, api_call_count)
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                text = " ".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
                return {
                    "changed_functions": sorted(changed_fns),
                    "affected_functions": [],
                    "bugs_introduced": [],
                    "severity": "unknown",
                    "concerns": text or "Agent ended without submitting a report.",
                    "_tool_log": tool_log,
                }

            tool_results = []
            final_report = None

            for block in response.content:
                if block.type != "tool_use":
                    continue

                name = block.name
                args = block.input
                tool_log.append(name)
                total_tool_calls += 1

                print(f"    [agent] {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})",
                      flush=True)

                if total_tool_calls >= MAX_TOOL_CALLS and name != "submit_impact_report":
                    print(f"    [agent] Tool call limit ({MAX_TOOL_CALLS}) reached - forcing report",
                          flush=True)
                    content = "Tool call limit reached. Call submit_impact_report now."
                elif name == "submit_impact_report":
                    args["_tool_log"] = tool_log
                    final_report = args
                    content = "Report submitted."
                else:
                    content = _tool_result_str(_execute_tool(name, args, cg, project_files))

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                })

            if final_report:
                return final_report

            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return {
            "changed_functions": sorted(changed_fns),
            "affected_functions": [],
            "bugs_introduced": [],
            "severity": "unknown",
            "concerns": "Agent loop ended unexpectedly.",
            "_tool_log": tool_log,
        }
