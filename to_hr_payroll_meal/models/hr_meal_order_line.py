from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrMealOrderLine(models.Model):
    _inherit = 'hr.meal.order.line'

    hr_payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', readonly=True)

    def _get_employee_price(self):
        res = super(HrMealOrderLine, self)._get_employee_price()
        contracts = self.employee_id.sudo()._get_contracts(self.meal_date.date(), self.meal_date.date(), states=['open', 'close'])
        if contracts[:1].set_pay_per_meal:
            return min(res, contracts[:1].pay_per_meal)
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_hr_payslip_id(self):
        for r in self:
            if r.hr_payslip_id:
                raise ValidationError(_("You must not delete a meal order line while it refers to a HR Payslip."
                                        " Please cancel the payslip %s first.") % r.hr_payslip_id.display_name)

    def _check_related_payslips(self):
        """
        Function to check if there is a confirmed employee payslip during
        the meal order period that will not allow the meal order
        """
        hr_meal_lines = self.filtered(lambda l: l.employee_id and l.meal_order_id and not l.hr_payslip_id)

        for employee in hr_meal_lines.employee_id:
            meal_lines = hr_meal_lines.filtered(lambda l: l.employee_id == employee)
            earliest_date = min(meal_lines.mapped('meal_date')).date()
            latest_date = max(meal_lines.mapped('meal_date')).date()
            payslips = employee.sudo()._get_payslips(earliest_date, latest_date)
            if payslips:
                raise UserError(_("You cannot book employee meals '%s' for the period %s - %s while the status of"
                                  " the corresponding payslip '%s' is neither Draft nor Cancelled."
                                  " Please ask your Payroll Manager to set up a Draft or Canceled payslip first.")
                                  % (employee.name,
                                    payslips[:1].date_from.strftime('%d/%m/%Y'),
                                    payslips[:1].date_to.strftime('%d/%m/%Y'),
                                    payslips[:1].display_name
                                ))

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        rec = super(HrMealOrderLine, self).create(vals_list)
        rec._check_related_payslips()
        return rec
