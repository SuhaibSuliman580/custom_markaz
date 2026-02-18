from odoo import fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    personal_tax_rule_escalation_ids = fields.One2many('personal.tax.rule', 'country_id', string='Personal Tax Rules')
