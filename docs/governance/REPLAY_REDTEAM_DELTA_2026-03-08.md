# Replay Red-Team Delta Report (2026-03-08)

## Target

- Repository: `faxp-org/faxp`
- Tested SHA: `6a89f1d12850e183ccbd140dfbb45875e787cb66`

## Result Summary

- Findings P0: none
- Findings P1: none
- Findings P2: none
- Findings P3: none

## Validated Controls

1. `redis_shared` volatile backend detection fails closed by default.
2. Volatile Redis override governance:
   - valid override accepted
   - malformed/expired/>24h overrides rejected
3. Startup audit evidence:
   - `replay_redis_durability_verified`
   - `replay_redis_volatile_override_active`
4. Duplicate replay path under volatile restart without override is rejected at policy guard.

## Evidence Source

- Red-team command/output transcript posted in security thread on 2026-03-08.
