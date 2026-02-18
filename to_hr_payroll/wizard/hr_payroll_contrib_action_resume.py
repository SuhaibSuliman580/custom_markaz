from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class HrPayrollContribActionResume(models.TransientModel):
    _name = 'hr.payroll.contrib.action.resume'
    _inherit = 'abstract.hr.payroll.contrib.act'
    _description = "Payroll Contribution Action Resume"

    payroll_contribution_reg_ids = fields.Many2many('hr.payroll.contribution.register', relation='wizard_action_resume_payroll_contrib_rel',
                                                    string='Payroll Contribution Register', required=True)
    currency_id = fields.Many2one(related='payroll_contribution_reg_ids.currency_id')
    contribution_base = fields.Monetary('Computation Base',
                                     help="The base for calculation of payroll contribution")
    employee_contrib_rate = fields.Float(string='Employee Contribution Rate (%)')
    company_contrib_rate = fields.Float(string='Company Contribution Rate (%)')

    @api.constrains('payroll_contribution_reg_ids')
    def _check_payroll_contribution_reg_ids(self):
        for r in self:
            if not r.payroll_contribution_reg_ids:
                continue
            if len(r.payroll_contribution_reg_ids.currency_id) > 1:
                raise ValidationError(_("All the selected Payroll Contribution Registers must have the same currency"))
            contribution_base = None
            employee_contrib_rate = None
            company_contrib_rate = None
            for reg_id in r.payroll_contribution_reg_ids:
                if contribution_base is None:
                    contribution_base = reg_id.contribution_base
                if employee_contrib_rate is None:
                    employee_contrib_rate = reg_id.employee_contrib_rate
                if company_contrib_rate is None:
                    company_contrib_rate = reg_id.company_contrib_rate
                if contribution_base is not None and float_compare(contribution_base, reg_id.contribution_base, r.currency_id.rounding) != 0:
                    raise ValidationError(_("All the selected Payroll Contribution Registers must have the same Computation Base"))
                if employee_contrib_rate is not None and float_compare(employee_contrib_rate, reg_id.employee_contrib_rate, precision_digits=2) != 0:
                    raise ValidationError(_("The selected Payroll Contribution Registers must have the same Employee Contribution Rate"))
                if company_contrib_rate is not None and float_compare(company_contrib_rate, reg_id.company_contrib_rate, precision_digits=2) != 0:
                    raise ValidationError(_("The selected Payroll Contribution Registers must have the same Employee Contribution Rate"))

    @api.onchange('payroll_contribution_reg_ids')
    def _onchange_payroll_contribution_reg_ids(self):
        if self.payroll_contribution_reg_ids:
            self.contribution_base = self.payroll_contribution_reg_ids[0].contribution_base
            self.employee_contrib_rate = self.payroll_contribution_reg_ids[0].employee_contrib_rate
            self.company_contrib_rate = self.payroll_contribution_reg_ids[0].company_contrib_rate

    @api.constrains('payroll_contribution_reg_ids', 'date')
    def _check_date(self):
        super()._check_date()

    def process(self):
        self.ensure_one()
        self.payroll_contribution_reg_ids.write({'date_resumed': self.date})
        self.payroll_contribution_reg_ids.with_context(
            call_wizard=False,
            contribution_base=self.contribution_base,
            employee_contrib_rate=self.employee_contrib_rate,
            company_contrib_rate=self.company_contrib_rate
            ).action_resume()
