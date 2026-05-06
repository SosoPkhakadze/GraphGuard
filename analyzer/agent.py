import json
from .agent_tools import (find_callers, find_callees, get_call_chain,
                           read_function, read_header, search_code)

TOOL_SCHEMAS = [
    {
        "name": "find_callers",
        "description": (
            "Find all functions that directly call the given function. "
            "Use this first for every changed function to trace upstream impact."
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
            "Use this to understand what a function depends on."
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
            "Returns a nested tree showing the full upstream impact chain."
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
            "Use this to inspect #ifdef guards, ownership semantics, or subtle logic."
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
            "Call this when you have enough information. This ends the analysis."
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

SYSTEM_PROMPT = """\
You are a senior C software engineer performing code impact analysis.
You have tools to explore a C project's call graph and source code.

Your process:
1. For each changed function, call find_callers to trace upstream impact.
2. Call get_call_chain to see the full transitive caller tree.
3. Call read_header if you suspect a contract violation (ownership, thread safety, etc.).
4. Call search_code if you suspect function pointers, macros, or #ifdef guards.
5. Call read_function to inspect implementation details when needed.
6. When you have a complete picture, call submit_impact_report.

Be thorough but efficient — only call tools when you need information you don't yet have.
Your final action must always be submit_impact_report."""


def run_agent(diff_text: str, changed_fns: set, cg, project_files: list,
              client, model: str) -> dict:
    """
    Run the agent loop against the Anthropic API.
    Returns the arguments passed to submit_impact_report as the final result.
    """
    initial_message = (
        f"Git diff:\n{diff_text}\n\n"
        f"Functions directly modified: {sorted(changed_fns) if changed_fns else '(parse from diff)'}\n\n"
        f"Trace the full impact using the available tools, then call submit_impact_report."
    )

    messages = [{"role": "user", "content": initial_message}]
    tool_log: list[str] = []

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        # Agent gave a plain text answer with no tool call — shouldn't happen normally
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

            print(f"    [agent] {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})")

            if name == "submit_impact_report":
                args["_tool_log"] = tool_log
                final_report = args
                result = "Report submitted."

            elif name == "find_callers":
                result = find_callers(args["function_name"], cg)
            elif name == "find_callees":
                result = find_callees(args["function_name"], cg)
            elif name == "get_call_chain":
                result = get_call_chain(args["function_name"], args.get("depth", 3), cg)
            elif name == "read_function":
                result = read_function(args["function_name"], cg)
            elif name == "read_header":
                result = read_header(args["function_name"], project_files)
            elif name == "search_code":
                result = search_code(args["pattern"], project_files)
            else:
                result = f"Unknown tool: {name}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result) if not isinstance(result, str) else result,
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
