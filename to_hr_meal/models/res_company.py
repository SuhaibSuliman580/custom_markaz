from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    set_meal_employee_price = fields.Boolean(string='Set Employee Price')
    meal_emp_price = fields.Monetary(string='Employee Price')
