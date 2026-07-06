# Database Schema & Migrations

This directory holds the PostgreSQL schema for the Qentry platform (Supabase).

## Source of truth

The **authoritative** schema is the base consolidated file plus the ordered
migrations applied on top of it:

1. `schema_final.sql` — base SaaS core (tenants, memberships, roles, plans,
   subscriptions, usage, audit, settings, feature flags) + helper functions.
2. The `migration_v3` … `migration_v16` files, applied **in the order listed
   below**.

Apply them with `scripts/migrations/setup_cloud_db.py` (which encodes this exact
order), or via the Supabase CLI.

> The other root files — `schema.sql`, `schema_simple.sql`, and
> `schema_complete.sql` — are **historical bootstrap snapshots** and are NOT
> kept current (they only cover up to ~v4). Do not use them to provision a new
> environment. They are retained for reference only.

## Migration order

| # | File | Adds |
|---|------|------|
| base | `schema_final.sql` | Core SaaS schema, RBAC, plans, usage, audit |
| v3 | `migration_v3_invitations_platform.sql` | events, templates, guests, invitations, checkins, `validate_checkin` |
| v4 | `migration_v4_generation_batches.sql` | generation_batches, batch_items |
| v4 | `migration_v4_event_improvements.sql` | event field additions |
| v5 | `migration_v5_production_hardening.sql` | constraints / hardening |
| v5 | `migration_v5_fix_missing_columns.sql` | column fixups |
| v6 | `migration_v6_constraints_and_governance.sql` | constraints + governance |
| v6 | `migration_v6_platform_limits.sql` | platform limits |
| v7 | `migration_v7_platform_consistency.sql` | platform consistency |
| v8 | `migration_v8_optional_guest_whatsapp.sql` | optional guest whatsapp |
| v8 | `migration_v8_slot_index.sql` | slot index |
| v9 | `migration_v9_event_address.sql` | event address fields |
| v9 | `migration_v9_guest_count_scans.sql` | guest_count-aware `validate_checkin` |
| v10 | `migration_v10_gate_teams_and_users.sql` | gate ↔ teams/users |
| v10 | `migration_v10_registration_forms.sql` | registration_forms |
| v11 | `migration_v11_professional_plans.sql` | professional plan tiers |
| v12 | `migration_v12_custom_plans.sql` | custom plans |
| v13 | `migration_v13_limits_and_features.sql` | limits & features |
| v14 | `migration_v14_addons_pricing.sql` | addon pricing |
| v15 | `migration_v15_standard_plan_limits.sql` | standard plan limits |
| v16 | `migration_v16_paypal_pending_subscriptions.sql` | PayPal pending subs |
| v16 | `migration_v16_ui_permissions.sql` | ui.* permission keys |

When two files share a version number, apply them in the order shown above.

## After provisioning

Run `python seed_plans.py` (from repo root) to seed the 5 plan tiers and their
limits. It requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` env vars —
**never hardcode keys**.
