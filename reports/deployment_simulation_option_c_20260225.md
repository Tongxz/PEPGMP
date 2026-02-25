# Option C Report: Simulated Deployment Testing

Date: 2026-02-25
Mode: Simulated deployment only (no real registry push, no real remote connection)

## Scope

Reviewed deployment-related shell scripts in:
- `scripts/*.sh`
- `scripts/lib/*.sh`
- `deploy-packages/PEPGMP-20251205/scripts/*.sh`
- `deploy-packages/PEPGMP-20251212/scripts/*.sh`

Primary execution-path focus:
- `scripts/deploy_via_registry.sh`
- `scripts/deploy_mixed_registry.sh`
- `scripts/build_prod_only.sh`
- `scripts/build_prod_images.sh`
- `scripts/update_image_version.sh`

## Validation Approach

1. Static syntax validation using `bash -n` for all deployment scripts.
2. Logic review for network/registry/SSH/offline branches and interactive behavior.
3. Mocked runtime simulation using fake `docker`, `curl`, `ssh`, `scp`, `rsync`, `ping` binaries via `PATH` override.
4. No real image pushes and no real remote connections performed.

Simulation logs captured under:
- `/tmp/pepgmp_sim2/local_registry.log`
- `/tmp/pepgmp_sim2/network_isolation.log`
- `/tmp/pepgmp_sim2/offline_package.log`
- `/tmp/pepgmp_sim2/build_cmd.log`

## Scenario Results

### 1) Local registry mock
Script: `scripts/deploy_via_registry.sh`
Result: PASS (simulated path completed)
Observed behavior:
- Registry check path succeeded
- Build/push/deploy steps progressed with mocked commands
- Script flow is logically coherent for happy path

### 2) Network isolation simulation
Script: `scripts/deploy_mixed_registry.sh`
Result: PASS (simulated path completed)
Observed behavior:
- Registry unreachable branch correctly skipped push
- Tar export + transfer + remote deploy path proceeded
- Health-check loop executed and passed under mock

### 3) Offline package handling
Script: `scripts/deploy_mixed_registry.sh`
Result: PASS (expected fail-fast)
Observed behavior:
- Script exits early when PyTorch source unavailable
- Error message is explicit and actionable
- Exit code: 1 (expected)

## Findings (Ordered by Severity)

### Critical

1. `scripts/setup_dev.sh` contains unrecoverable syntax error
- Evidence: `bash -n scripts/setup_dev.sh` fails at line 361.
- Location: `scripts/setup_dev.sh:361`
- Impact: script cannot execute at all.
- Root cause: duplicate trailing malformed function block (`() { ... }`) appended after `main "$@"`.
- Action:
  - Remove duplicated malformed block.
  - Re-run `bash -n scripts/setup_dev.sh` in CI.

2. `scripts/build_prod_only.sh` command assembly is broken on ARM path
- Evidence: simulated run exits with code 127; log shows `line 149: buildx: command not found` despite mock `docker buildx` existing.
- Locations:
  - `scripts/build_prod_only.sh:149`
  - `scripts/build_prod_only.sh:152`
  - `scripts/build_prod_only.sh:156`
- Impact: backend build command is malformed on ARM because `BUILD_CMD` is assigned with escaped quotes (`\"...\"`) then `eval` executes invalid tokenization.
- Action:
  - Replace `BUILD_CMD=\"...\"` with plain quoted assignment:
    - `BUILD_CMD="docker buildx build ..."`
  - Prefer direct command invocation over `eval` to avoid quoting bugs and injection risk.

### High

3. Non-interactive automation can block on prompts
- Locations:
  - `scripts/deploy_via_registry.sh:109`
  - `scripts/deploy_mixed_registry.sh:151`
  - `scripts/deploy_mixed_registry.sh:181`
  - `scripts/deploy_mixed_registry.sh:385`
  - `scripts/build_prod_images.sh:118`
  - `scripts/build_prod_images.sh:266`
  - `scripts/build_prod_images.sh:334`
  - `scripts/build_prod_only.sh:89`
- Impact: CI/CD or unattended runs can hang indefinitely.
- Action:
  - Add `--yes` / `--non-interactive` flag and auto-default behavior.
  - Guard prompts with `if [ -t 0 ]; then ... else ... fi`.

4. Several deployment commands use unquoted variables in SSH/SCP/Docker calls
- Example locations:
  - `scripts/deploy_via_registry.sh:94,103,119,128,129,131,248,266,376`
  - `scripts/deploy_mixed_registry.sh:205,342,357,358,417,472-476,500,604`
- Impact: whitespace/special chars in values (paths/users/tags) can break commands or lead to unintended expansion.
- Action:
  - Quote variable expansions consistently: `"$VAR"`.
  - For remote heredoc blocks, pass vars as env or positional args instead of direct interpolation when possible.

### Medium

5. Error handling depends on `set -e` with redundant `$?` checks
- Locations:
  - `scripts/deploy_via_registry.sh:219-226,236-243`
  - `scripts/deploy_mixed_registry.sh:325-333,587-592`
- Impact: readability and maintainability issue; false sense of explicit branch handling.
- Action:
  - Remove redundant `if [ $? -eq 0 ]` blocks after commands already protected by `set -e`.
  - Use explicit `if command; then ... else ... fi` where branch logic is needed.

6. Health checks rely on hardcoded container naming
- Locations:
  - `scripts/deploy_mixed_registry.sh:605` (`pepgmp-api-prod`)
- Impact: false negative health checks if compose project/container naming differs.
- Action:
  - Resolve container by compose service (`docker compose ps -q api`) or health endpoint via compose network.

7. Registry protocol assumption is fixed to HTTP in several checks
- Locations:
  - `scripts/deploy_via_registry.sh:83,103`
  - `scripts/deploy_mixed_registry.sh:340`
  - `scripts/build_prod_images.sh:109`
- Impact: HTTPS-only registries fail even if reachable.
- Action:
  - Support `REGISTRY_SCHEME` (`http|https`) or detect based on `IMAGE_REGISTRY` value.

## Summary

- Syntax status: 1 script hard-failing (`scripts/setup_dev.sh`), others pass `bash -n`.
- Simulation status:
  - Local registry mock: pass
  - Network isolation: pass
  - Offline package handling: expected fail-fast
- Highest-priority fixes before production confidence:
  1. Fix `scripts/setup_dev.sh` syntax corruption
  2. Fix `scripts/build_prod_only.sh` ARM build command quoting/eval path
  3. Add non-interactive mode to deployment scripts
