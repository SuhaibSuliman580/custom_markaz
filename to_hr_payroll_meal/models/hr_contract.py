from odoo import models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract'

    set_pay_per_meal = fields.Boolean(string='Set Meal Price',
                                      help="If enabled, the employee meal price set below "
                                      "will be used to calculate the meal price")
    pay_per_meal = fields.Monetary(string='Pay Per Meal', tracking=True,
                                   default=lambda self: self.env.company.meal_emp_price or 0.0,
                                help="The amount that the employee has to pay when place meal orders and will be"
                                " deducted from the payslips of this employee according to the number of ordered"
                                " meals accordingly.")
