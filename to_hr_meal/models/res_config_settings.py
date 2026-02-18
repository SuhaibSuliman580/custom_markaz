from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_id = fields.Many2one(related='company_id.currency_id')
    set_meal_employee_price = fields.Boolean(related='company_id.set_meal_employee_price',
                                     readonly=False,
                                     help="If enabled, the employee meal price set below will be used to calculate the meal price.")
    meal_emp_price = fields.Monetary(related='company_id.meal_emp_price',
                                     readonly=False,
                                     help="The employee meal price unit to be paid will be the minimum amount set on the meal type and this amount.")
