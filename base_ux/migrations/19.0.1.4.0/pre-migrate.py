import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

# BTL: ``odoo.upgrade`` exposes ``util`` only when Odoo runs with ``--upgrade-path``
# (it lives in the separate odoo/upgrade-util repo, not in odoo core). A plain
# ``odoo-bin -u`` branch build has no such path, so the import raises ImportError and
# aborts the whole registry load. Reimplemented in raw SQL, which is what a pre-migrate
# stage allows anyway. ``ir_ui_view.inherit_id`` is ``ondelete='restrict'``, so the
# inheritance tree has to be deleted bottom-up, deepest level first.
# TODO: Upgrade 19.0 - revert if upgrade-util is ever vendored.

OBSOLETE_VIEWS = [
    ("base_ux", "view_partner_form_mobile"),
    ("base_ux", "view_partner_tree_mobile"),
]


def migrate(cr, version):
    for module, name in OBSOLETE_VIEWS:
        cr.execute(
            "SELECT res_id FROM ir_model_data WHERE module = %s AND name = %s AND model = 'ir.ui.view'",
            (module, name),
        )
        row = cr.fetchone()
        if not row:
            _logger.info("View %s.%s not present, nothing to remove", module, name)
            continue

        cr.execute(
            """
            WITH RECURSIVE tree AS (
                SELECT id, 0 AS depth FROM ir_ui_view WHERE id = %s
                UNION ALL
                SELECT child.id, tree.depth + 1
                  FROM ir_ui_view child
                  JOIN tree ON child.inherit_id = tree.id
            )
            SELECT depth, array_agg(id) FROM tree GROUP BY depth ORDER BY depth DESC
            """,
            (row[0],),
        )
        for depth, view_ids in cr.fetchall():
            view_ids = tuple(view_ids)
            openupgrade.logged_query(
                cr,
                "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN %s",
                (view_ids,),
            )
            openupgrade.logged_query(cr, "DELETE FROM ir_ui_view WHERE id IN %s", (view_ids,))
            _logger.info("Removed %s inherited view(s) at depth %s of %s.%s", len(view_ids), depth, module, name)
