# Review note — 2026-10-02

`base_import_ux` and `base_import_mobile_ux` already set `auto_install` to `False`. `portal_backend` `res.users.create()` stays global: it normalizes user access, not company data.
