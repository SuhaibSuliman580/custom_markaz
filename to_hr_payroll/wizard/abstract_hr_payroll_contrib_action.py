from odoo import models, fields, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import format_date


class AbstractHrPayrollContribAction(models.AbstractModel):
    _name = 'abstract.hr.payroll.contrib.act'
    _description = "Share business logics between hr.payroll.contrib.action models"

    date = fields.Date(string='Date', required=True, default=fields.Date.today())

    def process(self):
        raise ValidationError(_("The method `process` has not been implemented for the model `%s`") % (self._name,))

    def _check_date(self):
        if 'payroll_contribution_reg_ids' in self:
            for r in self:
                for payroll_contribution_register in r.payroll_contribution_reg_ids:
                    if payroll_contribution_register.current_history_id \
                        and payroll_contribution_register.current_history_id.date_from >= r.date:
                        raise UserError(_("You should input a date that is later than %s, which is the Start Date of the current contribution history '%s'.")
                                        % (
                                            format_date(r.env, payroll_contribution_register.current_history_id.date_from),
                                            payroll_contribution_register.current_history_id.display_name,
                                            )
                                        )
