from odoo import models, _
from odoo.exceptions import ValidationError


class HrMealOrder(models.Model):
    _inherit = 'hr.meal.order'

    def action_refuse(self):
        for r in self:
            for line in r.order_line_ids.sudo():
                if line.hr_payslip_id:
                    raise ValidationError(_("You may not be able to refuse the order '%s' while it is referred by the payslips '%s'\n"
                                        "Please cancel the payslips first.")
                                      % (r.display_name, line.hr_payslip_id.display_name))
        super(HrMealOrder, self).action_refuse()

    def action_cancel(self):
        for r in self:
            hr_payslips = r.order_line_ids.sudo().mapped('hr_payslip_id')
            if hr_payslips:
                raise ValidationError(_("You must not cancel the order %s while it is referred by the following HR payslips: %s\n"
                                        "Please delete the payslips first.")
                                      % (r.name, ', '.join(hr_payslips.sudo().mapped('name'))))
        super(HrMealOrder, self).action_cancel()

    def action_confirm(self):
        res = super(HrMealOrder, self).action_confirm()
        for r in self:
            if r.order_line_ids:
                r.order_line_ids._check_related_payslips()
        return res

    def write(self, vals):
        res = super(HrMealOrder, self).write(vals)
        if vals.get('scheduled_date', False):
            self.order_line_ids._check_related_payslips()
        return res
