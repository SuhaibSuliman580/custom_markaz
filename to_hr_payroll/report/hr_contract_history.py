from odoo import fields, models


class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    gross_salary = fields.Monetary(string='Gross Salary', readonly=True)
