from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class HrPayrollContribActionChangeRates(models.TransientModel):
    _name = 'hr.payroll.contrib.action.change.rates'
    _inherit = 'abstract.hr.payroll.contrib.act'
    _description = "Payroll Contribution Action Change Rates"

    payroll_contribution_reg_ids = fields.Many2many('hr.payroll.contribution.register', relation='wizard_action_change_rates_payroll_contrib_rel',
                                                    string='Payroll Contribution Register', required=True)
    employee_contrib_rate = fields.Float(string='Employee Contribution Rate (%)', compute='_compute_employee_contrib_rate', store=True, readonly=False)
    company_contrib_rate = fields.Float(string='Company Contribution Rate (%)', compute='_compute_company_contrib_rate', store=True, readonly=False)

    @api.constrains('payroll_contribution_reg_ids')
    def _check_payroll_contribution_reg_ids(self):

        def check_rates_and_build_explaination_message(contrib_registers, rate_field):
            explaination_msg = ""
            contrib_rates = set(contrib_registers.mapped(rate_field))
            if len(contrib_rates) > 1:
                for rate in contrib_rates:
                    registers = contrib_registers.filtered(
                        lambda reg: float_compare(rate, getattr(reg, rate_field), precision_digits=2) == 0
                        )
                    explaination_msg += "* %s: %s;\n" % (
                        "%s%s" % (rate, '%'),  # append percentage sign
                        ", ".join(registers.employee_id.mapped('name'))
                        )
            return explaination_msg

        for r in self:
            if not r.payroll_contribution_reg_ids:
                continue
            # it is too dangerous to allow modifying rates for registers of different contribution types at the same time.
            # In addition to this, such operation is also not practical.
            # So, we raise error here to stop users from doing such a dangerous operation
            if len(r.payroll_contribution_reg_ids.type_id) > 1:
                raise UserError(_("You may not be able to modify registers of different types (%s) at the same time."
                                  " Please filter for a single type first.")
                                  % ", ".join(r.payroll_contribution_reg_ids.type_id.mapped('name')))

            # modifying employee rate for registers of different rates are also considered not practical and dangerous
            explaination_msg = check_rates_and_build_explaination_message(r.payroll_contribution_reg_ids, 'employee_contrib_rate')
            if explaination_msg:
                raise UserError(_("The contribution registers of `%s` you selected have different employee contribution rates."
                                  " You may want to filter for the registers of the same rate first."
                                  " Details:\n%s")
                                  % (r.payroll_contribution_reg_ids[0].type_id.name, explaination_msg))

            # modifying company rate for registers of different rates are also considered not practical and dangerous
            explaination_msg = check_rates_and_build_explaination_message(r.payroll_contribution_reg_ids, 'company_contrib_rate')
            if explaination_msg:
                raise UserError(_("The contribution registers of `%s` you selected have different company contribution rates."
                                  " You may want to filter for the registers of the same rate first."
                                  " Details:\n%s")
                                  % (r.payroll_contribution_reg_ids[0].type_id.name, explaination_msg))

    @api.depends('payroll_contribution_reg_ids.employee_contrib_rate')
    def _compute_employee_contrib_rate(self):
        for r in self:
            if r.payroll_contribution_reg_ids:
                r.employee_contrib_rate = r.payroll_contribution_reg_ids[0]._origin.employee_contrib_rate
            else:
                r.employee_contrib_rate = 0.0

    @api.depends('payroll_contribution_reg_ids.company_contrib_rate')
    def _compute_company_contrib_rate(self):
        for r in self:
            if r.payroll_contribution_reg_ids:
                r.company_contrib_rate = r.payroll_contribution_reg_ids[0]._origin.company_contrib_rate
            else:
                r.company_contrib_rate = 0.0

    def process(self):
        self.ensure_one()
        self.payroll_contribution_reg_ids.with_context(
            call_wizard=False,
            employee_contrib_rate=self.employee_contrib_rate,
            company_contrib_rate=self.company_contrib_rate,
            contribution_rates_change_date=self.date
            ).action_change_rates()
