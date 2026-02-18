from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HRPayrollContributionHistory(models.Model):
    _name = 'hr.payroll.contribution.history'
    _inherit = 'mail.thread'
    _rec_name = 'payroll_contribution_reg_id'
    _description = 'Payroll Contribution History'

    employee_id = fields.Many2one('hr.employee',
                                  related='payroll_contribution_reg_id.employee_id',
                                  readonly=True,
                                  store=True,
                                  string='Employee', tracking=True)
    date_from = fields.Date(string='Date Start', required=True, readonly=True, tracking=True)
    date_to = fields.Date(string='Date End', readonly=True, tracking=True)

    state = fields.Selection([
        ('confirmed', "Confirmed"),
        ('suspended', "Suspended"),
        ('resumed', "Resumed"),
        ('done', "Closed")], required=True, readonly=True, string='Status', tracking=True)

    payroll_contribution_reg_id = fields.Many2one('hr.payroll.contribution.register',
                                       readonly=True,
                                       required=True,
                                       string='Payroll Contribution Register', tracking=True)
    currency_id = fields.Many2one(related='payroll_contribution_reg_id.currency_id', store=True, readonly=True)
    company_id = fields.Many2one(related='payroll_contribution_reg_id.company_id', store=True, readonly=True)
    type_id = fields.Many2one(related='payroll_contribution_reg_id.type_id', store=True)

    contribution_base = fields.Monetary('Computation Base', tracking=True, readonly=True)
    employee_contrib_rate = fields.Float(string='Employee Contribution Rate (%)', tracking=True, readonly=True, help="Contribution rate in percentage")
    company_contrib_rate = fields.Float(string='Company Contribution Rate (%)', tracking=True, readonly=True, help="Contribution rate in percentage")

    employee_contrib_reg_id = fields.Many2one('hr.contribution.register',
                                              related='payroll_contribution_reg_id.employee_contrib_reg_id')

    hr_payslip_contribution_line_ids = fields.One2many('hr.payslip.contribution.line', 'payroll_contrib_history_id',
                                                          string='Payslip Payroll Contribution Lines', readonly=True)

    @api.constrains('date_from', 'date_to')
    def check_date(self):
        for r in self:
            if r.date_from and r.date_to and r.date_from > r.date_to:
                raise UserError(_("The Date End of the contribution history '%s' must be greater than or equal to its Date Start.")
                                % r.display_name
                                )

            domain = [
                ('id', '!=', r.id),
                ('payroll_contribution_reg_id', '=', r.payroll_contribution_reg_id.id)
            ]
            if r.date_to:
                domain += [
                    ('date_from', '<', r.date_to),
                    '|', ('date_to', '>', r.date_from), ('date_to', '=', False)]
            else:
                domain += [('date_to', '>', r.date_from)]

            overlapped = self.env['hr.payroll.contribution.history'].search(domain, limit=1)
            if overlapped:
                raise ValidationError(_("The contribution history %s you were creating/modifying was overlapped with"
                                        " an existing one which is %s. Please change the dates to avoid that.")
                                        % (r.display_name, overlapped.display_name))

    @api.depends('payroll_contribution_reg_id', 'employee_id', 'date_to')
    def _compute_display_name(self):
        for r in self:
            if r.date_to:
                r.display_name = '[%s] [%s] [%s - %s]' % (r.payroll_contribution_reg_id.type_id.name, r.employee_id.name, r.date_from, r.date_to)
            else:
                r.display_name = '[%s] [%s] [%s - %s]' % (r.payroll_contribution_reg_id.type_id.name, r.employee_id.name, r.date_from, _('Now'))

    def valid_for_sal_rule(self, payslip_date_from, payslip_date_to, delta=15):
        if self.state != 'confirmed' and self.state != 'resumed':
            return False

        delta = delta or 0

        payslip_date_from = fields.Date.to_date(payslip_date_from)
        payslip_date_to = fields.Date.to_date(payslip_date_to)

        payslip_date_from_delta = payslip_date_from + timedelta(days=delta)
        payslip_date_to_delta = payslip_date_to - timedelta(days=delta)

        date_from = self.date_from or False
        date_to = self.date_to or False

        if date_to:
            if payslip_date_to_delta <= date_from or payslip_date_from > date_to:
                return False
            elif payslip_date_to_delta > date_from and payslip_date_to_delta <= date_to:
                if payslip_date_from_delta > date_from:
                    return True
                else:
                    return False
            else:
                return False
        else:
            if payslip_date_from_delta > date_from:
                return True
            else:
                return False

    def _prepare_hr_payslip_contribution_line_data(self, date_from, date_to):
        """
        Prepare data to create contribution history line on payslip
        """
        if not date_from or date_from < self.date_from:
            date_from = self.date_from

        if self.date_to:
            if date_to >= self.date_to:
                date_to = self.date_to
        return {
            'payroll_contrib_history_id': self.id,
            'date_from': date_from,
            'date_to': date_to,
            }

    def action_edit_date_end(self):
        self.ensure_one()
        if self._context.get('call_wizard', False):
            action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.hr_payroll_contrib_action_edit_date_end_action')
            return action

    def action_edit_date_start(self):
        self.ensure_one()
        if self._context.get('call_wizard', False):
            action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.hr_payroll_contrib_action_edit_date_start_action')
            return action

    @api.ondelete(at_uninstall=False)
    def _unlink_except_payslip(self):
        for r in self:
            for payslip in r.hr_payslip_contribution_line_ids.payslip_id:
                raise UserError(_("You cannot delete the payroll contribution history '%s' while the payslip '%s' still refers to it."
                                  " You may need either to remove the payslip or to remove the relation between them.")
                                % (r.display_name, payslip.name))
