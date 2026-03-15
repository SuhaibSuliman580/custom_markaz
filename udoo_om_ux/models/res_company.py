# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    ps_brand = fields.Serialized()
    menus_preset = fields.Many2many('ir.ui.menu', domain=[('parent_id', '=', False)])

    def get_menus_preset(self):
        return [o['id'] for o in self.menus_preset.read(['id'])]
