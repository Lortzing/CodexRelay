# Architecture

## Profile model

Each profile is a self-contained snapshot:

```text
profiles/<name>/
├── profile.json
├── auth.json
└── config.toml
```

`profile.json` contains only non-secret metadata. `auth.json` and `config.toml` are the exact files activated into `CODEX_HOME`.

## First-run bootstrap

When no valid managed profile exists, the CLI checks for active `CODEX_HOME/auth.json` and `config.toml`. Installation and the first business command import those files under the process lock and register the imported profile as active. The check is idempotent and is skipped during shell completion and the explicit `import-current` command.

## Authentication modes

### ChatGPT profile

- Imports an existing Codex `auth.json`.
- Requires `tokens.access_token` and an account id.
- Uses the built-in `openai` provider in `config.toml`.
- Health and usage are checked through the ChatGPT usage endpoint.

### API profile

- Creates `auth.json` with `auth_mode = apikey` and `OPENAI_API_KEY`.
- Creates a custom `[model_providers.<id>]` table.
- Uses the Responses wire API and the configured base URL/model.
- Supports Responses, models-list, or custom health checks.

## Switching transaction

1. Acquire the process lock.
2. Back up active Codex files.
3. Atomically replace `auth.json`.
4. Atomically replace `config.toml`.
5. Parse and validate both active files.
6. Persist active-profile state.
7. Roll back the old files if any step fails.

## Automatic selection

Profiles are evaluated in priority order without modifying active Codex files. The state file tracks consecutive successes and failures.

- Current-profile failure uses `fail_threshold`.
- Higher-priority recovery uses `recover_threshold`.
- Recovery switching observes the cooldown.
- Emergency failover does not wait for the cooldown.
- No switch occurs when every candidate is unhealthy.

## Existing Codex processes

Codex clients can cache authentication and configuration. Automatic file switching primarily affects newly started processes. `coder-relay launch` selects a healthy profile and then starts a fresh Codex process so it reads the selected files.
