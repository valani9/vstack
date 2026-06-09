# Tutorial 05 — Exposing vstack via MCP

The vstack MCP server exposes all 34 patterns plus the cross-pattern
`vstack_diagnose` runner as tools to any MCP-compatible client
(Claude Desktop, Cursor, Cline, Continue, etc.). Once registered,
your LLM client can call any pattern directly without you writing
glue code.

## Install

```bash
pip install valanistack[anthropic]
```

The MCP server is part of the base wheel. Verify the install:

```bash
vstack-mcp --version
# vstack-mcp 0.2.0 (vstack 0.18.1)
```

## Register with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "vstack": {
      "command": "vstack-mcp",
      "args": [],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

Restart Claude Desktop. The vstack tools appear in the tool picker:

- `vstack_diagnose` — cross-pattern runner (v0.17.0+)
- `vstack_lewin`, `vstack_lencioni`, ..., `vstack_aar` — 34 per-pattern
  tools
- Resources: `vstack://patterns/index`, per-pattern citations /
  playbooks / composition
- Prompts: `vstack_pick_pattern` (routing), `vstack_<name>_invoke`
  (one per pattern, 35 total with the picker)

## Register with Cursor

Cursor reads the MCP config from the project's `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "vstack": {
      "command": "vstack-mcp"
    }
  }
}
```

## Register with Cline (VS Code extension)

Cline's settings UI has an "MCP Servers" panel. Add:

```json
{
  "command": "vstack-mcp",
  "env": {"ANTHROPIC_API_KEY": "sk-ant-..."}
}
```

## Calling `vstack_diagnose` from Claude Desktop

In a Claude Desktop conversation:

> Use the `vstack_diagnose` tool to diagnose this agent trace
> (paste trace JSON). Use the `stuck_in_loop` recipe.

Claude will call `vstack_diagnose` with `trace={...}` and
`recipe="stuck_in_loop"`. The tool returns the same JSON the
`vstack.diagnose.diagnose()` Python API returns: shape + ranked
findings + per-pattern summary + cost.

## Calling a single pattern

> Use `vstack_lewin` on this trace.

Claude passes the trace as the tool's input schema (the pattern's
Pydantic input model, which is auto-converted to JSON Schema). The
tool returns the structured detection.

## Resources

The MCP server exposes static catalog resources at predictable URIs:

- `vstack://patterns/index` — catalogue JSON (all 34 patterns)
- `vstack://patterns/<name>/citations` — per-pattern literature
- `vstack://patterns/<name>/playbooks` — per-pattern playbooks
- `vstack://patterns/<name>/composition` — composition manifest

In Claude Desktop, type `@vstack` and the resource picker shows
these.

## Prompts

The server exposes one routing prompt + one invocation prompt per
pattern (35 prompts total):

- `vstack_pick_pattern` — given a free-text failure description,
  picks the right pattern.
- `vstack_lewin_invoke`, `vstack_lencioni_invoke`, ... — one per
  pattern, ready-to-fill template arguments.

In Claude Desktop, `/vstack_pick_pattern` opens the routing prompt.

## Programmatic MCP client

If you want to call the vstack MCP server from a custom MCP client:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command="vstack-mcp")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print(f"{len(tools.tools)} tools available")

            # Call vstack_diagnose
            result = await session.call_tool(
                name="vstack_diagnose",
                arguments={
                    "trace": {"goal": "...", "steps": [], "outcome": "...", "success": False},
                    "recipe": "stuck_in_loop",
                },
            )
            print(result.content[0].text)


asyncio.run(main())
```

## Environment variables

- `ANTHROPIC_API_KEY` — required for any pattern that calls Anthropic.
- `OPENAI_API_KEY` — required for any pattern that calls OpenAI.
- `VSTACK_MCP_LOG_LEVEL` — defaults to `WARNING`. Set to `DEBUG` for
  tool-call logging on stderr.

## Troubleshooting

**"Tool call failed: LLMResolutionError: No LLM client could be resolved."**

Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in the MCP config's
`env` block.

**"Tool call failed: ValidationError"**

The tool input didn't match the pattern's Pydantic input schema.
Check the tool's `inputSchema` (visible in Claude Desktop's tool
picker) for the required fields.

**"Tool call timed out"**

Forensic-mode patterns can take 30-60s. Quick mode is faster but
less detailed. Switch by adding `"mode": "quick"` to the tool
arguments.

## See also

- v0.17.0 changelog for the `vstack_diagnose` tool details
- Tutorial 06 for the HTTP `/v1/diagnose` endpoint variant
- `_mcp/lib/_server.py` source for the tool registration logic
