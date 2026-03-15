# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    ps_data = fields.Serialized()
    ps_start_xmlid = fields.Char(sparse='ps_data')
    ps_menu_orders = fields.Json(sparse='ps_data')
    ps_fav_menus = fields.Json(sparse='ps_data')
    ps_auto_hmenu = fields.Boolean(sparse='ps_data')

    up_bookmarks = fields.Json(readonly=True)
