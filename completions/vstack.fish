# Fish completion for the vstack CLI family.
# Install: cp completions/vstack.fish ~/.config/fish/completions/

# vstack-mcp
complete -c vstack-mcp -f -n "__fish_use_subcommand" -a "serve list-tools list-resources config-snippet"
complete -c vstack-mcp -f -n "__fish_seen_subcommand_from config-snippet" \
    -a "claude-desktop cursor cline continue generic"

# vstack-api
complete -c vstack-api -f -n "__fish_use_subcommand" -a "serve routes openapi"

# vstack-config
complete -c vstack-config -f -n "__fish_use_subcommand" \
    -a "get set list unset path keys install-skills gen-platform"
complete -c vstack-config -f -n "__fish_seen_subcommand_from path" \
    -a "home baselines sessions analytics config"
complete -c vstack-config -f -n "__fish_seen_subcommand_from gen-platform" \
    -a "claude-desktop cursor cline continue roo-code windsurf zed aider goose kiro openclaw codex-cli opencode docker-compose"
complete -c vstack-config -f -n "__fish_seen_subcommand_from get set unset" \
    -a "default_mode default_model telemetry log_level preferred_llm api_host api_port skills_install_path"

# vstack-learn
complete -c vstack-learn -f -n "__fish_use_subcommand" \
    -a "record recall outcome outcomes path clear"

# vstack-analytics
complete -c vstack-analytics -f -n "__fish_use_subcommand" \
    -a "summary top-costs cost path raw"

# vstack-browser
complete -c vstack-browser -f -n "__fish_use_subcommand" -a "scrape screenshot tools"

# vstack-gbrain
complete -c vstack-gbrain -f -n "__fish_use_subcommand" -a "status sync search corpus"

# vstack-bench
complete -c vstack-bench -f -n "__fish_use_subcommand" -a "list run compare"

# vstack-doctor
complete -c vstack-doctor -l json -d "Emit JSON instead of pretty text"
complete -c vstack-doctor -l skip-network -d "Skip the PyPI upgrade check"
complete -c vstack-doctor -l only-errors -d "Print only ERROR-level findings"

# vstack-hello
complete -c vstack-hello -l offline -d "Skip LLM resolution; always show canned sample"
complete -c vstack-hello -l json -d "Emit a JSON envelope instead of pretty text"
complete -c vstack-hello -l no-banner -d "Skip the ASCII banner and footer"

# vstack (top-level AAR CLI)
complete -c vstack -f -n "__fish_use_subcommand" -a "aar bench version"

# ---------------------------------------------------------------------------
# Pattern CLIs (33) — all share the same subcommand set.
# analyze batch replay validate schema playbooks compose
# Registered via a single loop to keep this file compact.
# ---------------------------------------------------------------------------
for cli in vstack-lewin vstack-goleman vstack-johari vstack-danva vstack-reappraisal \
        vstack-yerkes vstack-hexaco vstack-grant vstack-motivation vstack-sdt \
        vstack-mcgregor vstack-vroom vstack-grpi vstack-process vstack-loafing \
        vstack-superflocks vstack-lencioni vstack-trust-triangle vstack-mcallister \
        vstack-psych-safety vstack-glaser vstack-feedback-triggers vstack-plus-delta \
        vstack-smart-goal vstack-group-decision vstack-debate-pathology vstack-bias-stack \
        vstack-devils-advocate vstack-thomas-kilmann vstack-schein-culture \
        vstack-robbins-culture vstack-org-structure vstack-span-of-control
    complete -c $cli -f -n "__fish_use_subcommand" \
        -a "analyze batch replay validate schema playbooks compose"
end

# ---------------------------------------------------------------------------
# Workflow CLIs (8)
# ---------------------------------------------------------------------------

# vstack-diagnose (flag-driven)
complete -c vstack-diagnose -l trace -d "Path to a trace file to diagnose"
complete -c vstack-diagnose -l recipe -d "Recipe id to run"
complete -c vstack-diagnose -l client -d "Client identifier"
complete -c vstack-diagnose -l shape -d "Trace/recipe shape filter"
complete -c vstack-diagnose -l mode -d "Diagnosis mode"
complete -c vstack-diagnose -l patterns -d "Restrict to a comma-separated pattern set"
complete -c vstack-diagnose -l list-recipes -d "List available recipes"
complete -c vstack-diagnose -l list -d "List available diagnoses"
complete -c vstack-diagnose -l json -d "Emit JSON instead of pretty text"
complete -c vstack-diagnose -l top -d "Limit to the top N results"
complete -c vstack-diagnose -l match -d "Filter by a match query"
complete -c vstack-diagnose -l help -d "Show help"

# vstack-recipes (flag-driven)
complete -c vstack-recipes -l cluster -d "Filter recipes by cluster"
complete -c vstack-recipes -l shape -d "Filter recipes by shape"
complete -c vstack-recipes -l match -d "Filter by a match query"
complete -c vstack-recipes -l q -d "Free-text query"
complete -c vstack-recipes -l show -d "Show a specific recipe"
complete -c vstack-recipes -l json -d "Emit JSON instead of pretty text"
complete -c vstack-recipes -l md -d "Emit Markdown"
complete -c vstack-recipes -l compact -d "Compact output"
complete -c vstack-recipes -l help -d "Show help"

# vstack-scorecard (subcommands)
complete -c vstack-scorecard -f -n "__fish_use_subcommand" -a "compute render compare"

# vstack-dashboard (subcommands)
complete -c vstack-dashboard -f -n "__fish_use_subcommand" -a "render serve"

# vstack-trace-zoo (subcommands)
complete -c vstack-trace-zoo -f -n "__fish_use_subcommand" -a "list show get categories shapes"

# vstack-redaction (flag-driven)
complete -c vstack-redaction -l trace -d "Path to a trace file to redact"
complete -c vstack-redaction -l text -d "Inline text to redact"
complete -c vstack-redaction -l list-patterns -d "List available redaction patterns"
complete -c vstack-redaction -l out -d "Output file path"
complete -c vstack-redaction -l json -d "Emit JSON instead of pretty text"
complete -c vstack-redaction -l help -d "Show help"

# vstack-export (flag-driven)
complete -c vstack-export -l report -d "Report to export"
complete -c vstack-export -l format -d "Output format"
complete -c vstack-export -l out -d "Output file path"
complete -c vstack-export -l help -d "Show help"

# vstack-aggregate (flag-driven)
complete -c vstack-aggregate -l reports -d "Reports to aggregate"
complete -c vstack-aggregate -l top -d "Limit to the top N results"
complete -c vstack-aggregate -l json -d "Emit JSON instead of pretty text"
complete -c vstack-aggregate -l out -d "Output file path"
complete -c vstack-aggregate -l help -d "Show help"
