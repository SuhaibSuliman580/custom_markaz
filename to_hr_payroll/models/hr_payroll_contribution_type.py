from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HRPayrollContributionType(models.Model):
    _name = 'hr.payroll.contribution.type'
    _description = 'Payroll Contribution Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True, translate=True)

    code = fields.Char(string='Code', required=True,
                       help='The unique code of the payroll_contribution type which can be used within salary rules computation.')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    employee_contrib_reg_id = fields.Many2one('hr.contribution.register', required=True, string='Employee Contribution',
                                              domain="[('company_id', 'in', (False, company_id))]",
                                              help="Links to a contribution register that involves Employee\'s contribution")
    employee_contrib_rate = fields.Float(string='Employee Contribution Rate',
                                         required=True,
                                         help="The rate in percentage of the taxable income of the employee that the employees contributes")

    company_contrib_reg_id = fields.Many2one('hr.contribution.register', string='Company Contribution',
                                             domain="[('company_id', 'in', (False, company_id))]",
                                             help="Link to a contribution register that involves Company's contribution")
    company_contrib_rate = fields.Float(string='Company Contribution Rate (%)',
                                                 help="The rate in percentage of the taxable income of the employee that the company contributes")

    partner_id = fields.Many2one('res.partner',
                                 related='employee_contrib_reg_id.partner_id',
                                 string='Payroll Contribution Partner',
                                 help='The partner into whom the contribution goes.')

    total_payroll_contribution_reg_ids = fields.One2many('hr.payroll.contribution.register', 'type_id',
                                              string='Total Payroll Contribution Registers',
                                              readonly=True)
    current_payroll_contribution_reg_ids = fields.One2many('hr.payroll.contribution.register', 'type_id',
                                                domain=[('state', 'in', ['confirmed', 'resumed'])],
                                                string='Current Payroll Contribution Registers',
                                                readonly=True)

    total_payroll_contribution_reg_count = fields.Integer(compute='_compute_total_payroll_contribution_reg_count',
                                               string='Total Payroll Contribution Reg.',
                                               groups="to_hr_payroll.group_hr_payroll_user")
    current_payroll_contribution_reg_count = fields.Integer(compute='_compute_current_payroll_contribution_active_reg_count',
                                                 string='Current Payroll Contribution Reg.',
                                                 groups="to_hr_payroll.group_hr_payroll_user")

    employee_payslip_line_count = fields.Integer(compute='_compute_employee_payslip_line_count',
                                                 string='Employee Payslip Lines',
                                                 groups="to_hr_payroll.group_hr_payroll_user")
    company_payslip_line_count = fields.Integer(compute='_compute_company_payslip_line_count',
                                                 string='Company Payslip Lines',
                                                 groups="to_hr_payroll.group_hr_payroll_user")
    computation_block = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ], string='Computation Block', required=True, default='month',
        help="Minimum block for contribution computation.\n")
    days_in_months = fields.Selection([('fixed', 'Fixed as 28 days'), ('flexible', 'Flexible')], string='Days in Month', required=True, default='fixed',
                                      help="During payslip contributions computation,\n"
                                      "- Fixed as 28 days: every month will be considered to have 28 days in total\n"
                                      "- Flexible: the number of days depends on the actual month, which varies from 28 to 31.")
    computation_method = fields.Selection([
        ('half_up', 'Half-up Duration Rounding'),
        ('max_unpaid_days', 'Unpaid Days Limitation'),
        ], string='Computation Method', required=True, default='half_up',
        help="- Half-up Duration Rounding: If worked duration of employee in month is greater or equal to a half of total days in month, contribution will be calculated.\n"
             "- Unpaid Days Limitation: If employee has total unpaid days less than the following limit in a month, contribution will be calculated.")
    max_unpaid_days = fields.Float('Maximum Unpaid Days', default=14.0)

    _sql_constraints = [
        ('code_unique_per_company',
         'UNIQUE(code,company_id)',
         "The Payroll Contribution Type's code must be unique per company!"),
    ]

    @api.onchange('company_contrib_reg_id')
    def _onchange_company_contrib_reg_id(self):
        if not self.employee_contrib_reg_id and self.company_contrib_reg_id:
            raise ValidationError(_("You must select Employee Contribution first"))

    def _get_employee_payslip_lines(self):
        domain = [('register_id', '=', self.employee_contrib_reg_id.id)]
        return self.env['hr.payslip.line'].search(domain)

    def _compute_employee_payslip_line_count(self):
        for r in self:
            r.employee_payslip_line_count = len(r._get_employee_payslip_lines())

    def _get_company_payslip_lines(self):
        return self.company_contrib_reg_id and self.env['hr.payslip.line'].search([('register_id', '=', self.company_contrib_reg_id.id)]) or self.env['hr.payslip.line']

    def _compute_company_payslip_line_count(self):
        for r in self:
            r.company_payslip_line_count = len(r._get_company_payslip_lines())

    def _compute_total_payroll_contribution_reg_count(self):
        register_data = self.env['hr.payroll.contribution.register']._read_group([
            ('type_id', 'in', self.ids),
            ('state', '!=', 'draft')],
            ['type_id'], ['__count'])
        mapped_data = {contribute_type.id: count for contribute_type, count in register_data}
        for r in self:
            r.total_payroll_contribution_reg_count = mapped_data.get(r.id, 0)

    def _compute_current_payroll_contribution_active_reg_count(self):
        register_data = self.env['hr.payroll.contribution.register']._read_group([
            ('type_id', 'in', self.ids),
            ('state', 'in', ['confirmed', 'resumed'])
            ], ['type_id'], ['__count'])
        mapped_data = {contribute_type.id: count for contribute_type, count in register_data}
        for r in self:
            r.current_payroll_contribution_reg_count = mapped_data.get(r.id, 0)

    def _prepare_payroll_contribution_register_data(self, contract):
        return {
            'employee_id': contract.employee_id.id,
            'type_id': self.id,
            'company_id': contract.company_id.id,
            'date_from': contract.date_start,
            'contribution_base': contract._get_payroll_contribution_base(),
            'employee_contrib_reg_id': self.employee_contrib_reg_id.id,
            'employee_contrib_rate': self.employee_contrib_rate,
            'company_contrib_rate': self.company_contrib_rate,
            'computation_block': self.computation_block,
            'days_in_months': self.days_in_months,
            'computation_method': self.computation_method,
            'max_unpaid_days': self.max_unpaid_days,
            'state': 'draft',
            }

    def action_view_current_registers(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.act_hr_payroll_contribution_reg_current')
        action['context'] = {
            'search_default_type_id': [self.id],
            'default_type_id': self.id,
            'search_default_confirmed_resumed': 1
            }
        return action

    def action_view_all_registers(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.act_hr_payroll_contribution_reg_all')
        action['context'] = {
            'search_default_type_id': [self.id],
            'default_type_id': self.id,
            'search_default_confirmed_resumed': 1,
            'search_default_done': 1,
            'search_default_suspended': 1
            }
        return action

    def action_mass_change_rates(self):
        """
        This call wizard to change contribution rates for all the existing and current contribution registers
        of this type whose state is either Confirmed or Resumed only.
        """
        action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.hr_payroll_contrib_action_change_rates_action')
        action['context'] = {'default_payroll_contribution_reg_ids': self.current_payroll_contribution_reg_ids.ids}
        return action
