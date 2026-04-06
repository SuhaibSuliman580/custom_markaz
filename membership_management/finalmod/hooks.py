# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    """Populate medical.unv from existing partner university char values (if any)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Partner = env['res.partner'].with_context(active_test=False)
    Unv = env['medical.unv'].with_context(active_test=False)

    # collect distinct non-empty values
    cr.execute("""
        SELECT DISTINCT TRIM(university)
        FROM res_partner
        WHERE university IS NOT NULL AND TRIM(university) <> ''
    """)
    names = [row[0] for row in cr.fetchall() if row and row[0]]
    if not names:
        return

    existing = set(Unv.search([('name', 'in', names)]).mapped('name'))
    to_create = [{'name': n, 'active': True} for n in names if n not in existing]
    if to_create:
        Unv.create(to_create)
