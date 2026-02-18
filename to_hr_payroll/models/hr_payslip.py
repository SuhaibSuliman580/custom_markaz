import pytz
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import format_date
from odoo.tools.safe_eval import wrap_module
from odoo.exceptions import UserError, ValidationError

from .browsable_object import BrowsableObject
from .hr_contract import TAX_POLICY


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to DESC, id DESC'
    _description = 'Pay Slip'
    _mail_post_access = 'read'

    def _default_salary_cycle_id(self):
        return self.env.company.salary_cycle_id or self.env.ref('to_hr_payroll.hr_salary_cycle_default')

    def _default_thirteen_month_pay_year(self):
        return fields.Date.today().year - 1

    # Payslip 13th
    thirteen_month_pay = fields.Boolean(string='13th-Month Pay', tracking=True,
                                        help="If checked, this payslip will be considered as 13th-Month Payslip")
    thirteen_month_pay_year = fields.Integer('13th-Month Pay Year',
                                             default=_default_thirteen_month_pay_year,
                                             help="The year for thirteen month pay calculation")
    thirteen_month_pay_include_trial = fields.Boolean(string='13th-Month Pay Incl. Trial',
                                                      help="If enabled, 13th-Month Pay will include trial contracts (which has trial end"
                                                      " date specified) during salary computation.")

    # Payslip common info
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batches', copy=True,
                                     index=True, tracking=True)
    salary_cycle_id = fields.Many2one('hr.salary.cycle', string='Salary Cycle', tracking=True,
                                      required=True, default=_default_salary_cycle_id,
                                      compute='_compute_salary_cycle', store=True, readonly=False,
                                      precompute=True,
                                      help="Select an appropriate salary cycle to apply if it differs from"
                                      " the one specified in your company's settings.")
    name = fields.Char(string='Payslip Name', readonly=False,
                       compute='_compute_name', store=True, tracking=True)
    number = fields.Char(string='Reference', copy=False, tracking=True)
    is_payslip_trial = fields.Boolean(compute='_compute_is_payslip_trial',
                                      help="Technical field, Mark payslip as trial payslip if its Contract is trial contract.")
    date_from = fields.Date(string='Date From', required=True, tracking=True, copy=True,
                            compute='_compute_date_from', store=True, readonly=False,
                            precompute=True,
                            help="By default, the payslip  period is from the previous cycle.")
    date_to = fields.Date(string='Date To', readonly=False, required=True,
                          precompute=True,
                          compute='_compute_date_to', store=True, copy=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected')],
        string='Status', index=True, readonly=False, copy=False, default='draft', tracking=True,
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    company_id = fields.Many2one('res.company', string='Company', copy=True, required=True,
                                 default=lambda self: self.env.company,
                                 compute='_compute_company', store=True, readonly=False,
                                 precompute=True)
    currency_id = fields.Many2one('res.currency', string="Currency", compute="_compute_currency_id", store=True, copy=True)
    paid = fields.Boolean(string='Made Payment Order ? ', copy=False)
    note = fields.Text(string='Internal Note')

    # Employee info
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_ids = fields.Many2many('hr.contract', 'hr_payslip_hr_contract_rel', 'payslip_id', 'contract_id',
                                    groups="to_hr_payroll.group_hr_payroll_user",
                                    string='Contracts', compute='_compute_contracts', store=True, copy=False, required=True,
                                    help="Technical fields to store all the contracts that are applicable to the payslip period.")
    contracts_count = fields.Integer(string='Contracts Count', compute='_compute_contracts_count', compute_sudo=True)
    department_id = fields.Many2one('hr.department', string='Department', compute='_compute_department_job', store=True)
    job_id = fields.Many2one('hr.job', string='Job', compute='_compute_department_job', store=True)
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure', domain="[('company_id','=',company_id)]",
        tracking=True, compute='_compute_struct', store=True, readonly=False,
        groups="to_hr_payroll.group_hr_payroll_user",
        help='Defines the rules that have to be applied to this payslip, accordingly '
             'to the contract chosen. If you let empty the field contract, this field isn\'t '
             'mandatory anymore and thus the rules applied will be all the rules set on the '
             'structure of all contracts of the employee valid for the chosen period')

    # Payslip Input
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', string='Payslip Inputs',
        compute='_compute_input_line_ids', store=True, readonly=False)

    # Payslip lines
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Payslip Lines', readonly=True)
    payslip_lines_count = fields.Integer(compute='_compute_payslip_lines_count', string="Payslip Computation Details")
    details_by_salary_rule_category = fields.One2many('hr.payslip.line',
                                                      string='Details by Salary Rule Category',
                                                      compute='_compute_details_by_salary_rule_category')
    cost_line_ids = fields.One2many('hr.payslip.line', string='Cost Lines',
                                    compute='_compute_cost_lines',
                                    help="The lines whose amount is at company cost")

    # Salary
    basic_wage = fields.Monetary(string='Basic Wage', compute='_compute_basic', store=True, tracking=True)
    gross_salary = fields.Monetary(string='Gross Salary', compute='_compute_gross_salary', store=True, tracking=True)
    company_cost = fields.Monetary(string='Company Cost', compute='_compute_company_cost', store=True, tracking=True,
                                   groups='to_hr_payroll.group_hr_payroll_user')
    net_salary = fields.Monetary(string='Net Salary', compute='_compute_net', store=True, tracking=True)
    date_confirmed = fields.Date(string='Date Confirmed', copy=False, tracking=True)

    # Refund Payslip
    credit_note = fields.Boolean(string='Credit Note',
                                 help="Indicates this payslip has a refund of another")
    refund_for_payslip_id = fields.Many2one('hr.payslip', string='Refund for', copy=False,
                                            help="The original payslip for which this payslip refunds")
    refund_ids = fields.One2many('hr.payslip', 'refund_for_payslip_id', string='Refunds', copy=False,
                                 help="The payslips that are the refunds for this payslip")
    refunds_count = fields.Integer(string='Refunds Count', compute='_compute_refunds_count')

    # Contribution
    hr_payslip_contribution_line_ids = fields.One2many('hr.payslip.contribution.line', 'payslip_id',
                                                       string='Contribution History Lines',
                                                       compute='_compute_hr_payslip_contribution_line_ids', store=True)

    # Full Hours/Days in 1 cycle
    calendar_working_hours = fields.Float(string='Calendar Working Hours',
                                          compute='_compute_calendar_working_days_hours', store=True,
                                          help="Total Working Hours (excl. global leaves) for the FULL months crossing the paylip according"
                                          " to the corresponding working schedule.")
    calendar_working_days = fields.Float(string='Calendar Working Days',
                                         compute='_compute_calendar_working_days_hours', store=True,
                                         help="Total Working Days (excl. global leaves) for the FULL months crossing the paylip according"
                                         " to the corresponding working schedule.")

    # Duty Hours/Days in actual duration
    duty_working_hours = fields.Float(string='Duty Working Hours', compute='_compute_duty_working_days_hours', store=True,
                                      help="Total Working Hours on duty according to the payslip period and the employee working schedule.")
    duty_working_days = fields.Float(string='Duty Working Days', compute='_compute_duty_working_days_hours', store=True,
                                     help="Total Working Days on duty according to the payslip period and the employee working schedule.")

    # Leaves
    leave_days = fields.Float(string='Total Leave Days',
                              compute='_compute_leave_days_hours', compute_sudo=True,
                              help="Total leave days excluding global leaves")
    leave_hours = fields.Float(string='Total Leave Hours',
                               compute='_compute_leave_days_hours', compute_sudo=True,
                               help="Total leave hours excluding global leaves")
    unpaid_leave_days = fields.Float(string='Unpaid Leave Days',
                                     compute='_compute_unpaid_leave_days_hours', compute_sudo=True)
    unpaid_leave_hours = fields.Float(string='Unpaid Leave Hours',
                                      compute='_compute_unpaid_leave_days_hours', compute_sudo=True)

    # Actual working days/hours
    worked_days = fields.Float(string='Worked Days', compute='_compute_worked_days_hours', compute_sudo=True)
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_days_hours', compute_sudo=True)

    # Work days
    worked_days_line_ids = fields.One2many('hr.payslip.worked_days', 'payslip_id',
                                           string='Workdays Type',
                                           compute='_compute_worked_days_line_ids', store=True)
    work_entry_ids = fields.Many2many('hr.work.entry', 'hr_payslip_work_entry_rel', 'payslip_id', 'work_entry_id',
                                      string='Work Entries',
                                      compute='_compute_work_entry_ids', store=True)
    work_entry_count = fields.Integer(string='Work Entries Count', compute='_compute_work_entry_count')
    # Work Entry Warning
    # TODO in master+: Added filter for pay slips/payrolls that need Work Entry processing
    warning_we_conflict = fields.Boolean(string="Work Entry is Conflicted", compute='_compute_we_warning', compute_sudo=True)
    warning_we_no_validate = fields.Boolean(string="Work Entry Not Validated", compute='_compute_we_warning', compute_sudo=True)
    warning_we_no_exists = fields.Boolean(string="Work Entry Does Not Exist", compute='_compute_we_warning', compute_sudo=True)

    # Tax fields
    personal_tax_base = fields.Monetary(string='Personal Income Tax Base', compute='_compute_personal_tax_base', store=True, tracking=True)
    personal_tax_policy = fields.Selection(TAX_POLICY, string='Personal Income Tax Policy', compute='_compute_personal_tax_policy', store=True, tracking=True)
    personal_tax_rule_id = fields.Many2one('personal.tax.rule', string='Tax Rule', compute='_compute_personal_tax_policy', store=True, tracking=True)
    personal_tax_base_deduction = fields.Monetary(string='Personal Deduction', compute='_compute_get_dependent_deduction', store=True, tracking=True)
    dependent_deduction = fields.Monetary(string='Dependent Deduction', compute='_compute_get_dependent_deduction', store=True, tracking=True)
    payslip_personal_income_tax_ids = fields.One2many('payslip.personal.income.tax', 'slip_id', string='Personal Income Tax Details')
    is_different_tax_rule = fields.Boolean(string='Is Different Tax Rules', compute="_compute_is_different_tax_rule", compute_sudo=True)

    # For email template
    employee_partner_id = fields.Many2one('res.partner', string='Employee Contact', compute='_compute_employee_partner_id')
    employee_lang = fields.Char(string='Employee Language', compute='_compute_employee_lang')

    @api.constrains('contract_ids', 'thirteen_month_pay')
    def _check_multi_contracts(self):
        for r in self:
            if r.thirteen_month_pay:
                continue
            conflict_fields = r.contract_ids._get_discrepancy_fields()
            if conflict_fields:
                field_names = []
                for f in conflict_fields:
                    field_names.append(r.contract_ids._fields[f]._description_string(r.env))
                field_list_msg = "\n".join(field_names)
                raise ValidationError(_("Inconsistent contracts! Please separate the payslip '%s' into multiple ones "
                                        "to ensure that each payslip contains contracts with the same value in the following fields:\n"
                                        "%s")
                                        % (r.name, field_list_msg)
                                        )

    @api.depends('employee_id')
    def _compute_company(self):
        for r in self:
            r.company_id = r.employee_id.company_id

    @api.depends('contract_ids', 'employee_id')
    def _compute_department_job(self):
        for r in self:
            r.department_id = r.contract_ids[:1].department_id or r.employee_id.department_id
            r.job_id = r.contract_ids[:1].job_id or r.employee_id.job_id

    @api.depends('contract_ids')
    def _compute_personal_tax_policy(self):
        for r in self:
            r.personal_tax_policy = r.contract_ids[-1:].personal_tax_policy
            r.personal_tax_rule_id = r.contract_ids[-1:].personal_tax_rule_id

    def _compute_is_different_tax_rule(self):
        for r in self:
            if not r.thirteen_month_pay and len(r.contract_ids.personal_tax_rule_id) > 1:
                r.is_different_tax_rule = True
            else:
                r.is_different_tax_rule = False

    @api.depends('contract_ids')
    def _compute_currency_id(self):
        for r in self:
            r.currency_id = r.contract_ids[:1].currency_id

    @api.depends('personal_tax_rule_id', 'employee_id')
    def _compute_get_dependent_deduction(self):
        for r in self:
            if r.personal_tax_rule_id.apply_tax_base_deduction:
                r.dependent_deduction = r.personal_tax_rule_id.dependent_tax_base_ded * r.employee_id.total_dependant
                r.personal_tax_base_deduction = r.personal_tax_rule_id.personal_tax_base_ded
            else:
                r.dependent_deduction = 0.0
                r.personal_tax_base_deduction = 0.0

    @api.depends('date_from', 'date_to', 'contract_ids')
    def _compute_calendar_working_days_hours(self):
        for r in self:
            if not r.contract_ids or not r.date_from or not r.date_to or not r.salary_cycle_id:
                continue
            calendar = r.contract_ids.resource_calendar_id
            tz = pytz.timezone(calendar.tz)
            cycle = r.salary_cycle_id

            # get start date and end date of salary cycles
            datetime_list = cycle._get_month_start_dates(r.date_from, r.date_to)
            date_from = cycle._get_month_start_date(datetime_list[0])
            date_to = cycle._get_month_end_date(datetime_list[-1])

            # set timezone
            date_from = date_from.astimezone(tz)
            date_to = date_to.astimezone(tz)

            # get work duration data
            data = calendar.get_total_work_duration_data(date_from, date_to)
            # data type: {'days': 43.0, 'hours': 344.0}
            r.calendar_working_hours = data['hours']
            r.calendar_working_days = data['days']

    @api.depends('date_from', 'date_to', 'contract_ids')
    def _compute_duty_working_days_hours(self):
        for r in self:
            if not r.contract_ids or not r.date_from or not r.date_to:
                continue
            calendar = r.contract_ids.resource_calendar_id
            tz = pytz.timezone(calendar.tz)
            duty_working_hours = 0.0
            duty_working_days = 0.0
            # Loop valid periods between contracts and the payslip
            for contract in r.contract_ids:
                date_from, date_to = contract._qualify_interval(r.date_from, r.date_to)
                date_from = datetime.combine(date_from, time.min, tz)
                date_to = datetime.combine(date_to, time.max, tz)
                # set `compute_leaves=True` because need remove global holidays from duty actual days
                data = calendar.get_total_work_duration_data(date_from, date_to)
                # data type: {'days': 43.0, 'hours': 344.0}
                duty_working_days += data['days']
                duty_working_hours += data['hours']
            r.duty_working_hours = duty_working_hours
            r.duty_working_days = duty_working_days

    def _compute_leave_days_hours(self):
        self.flush_model()
        for r in self:
            # Work Entries - Timeoff
            work_entries = self.work_entry_ids.filtered(
                lambda r: r.leave_id and r.leave_id.holiday_status_id.time_type == 'leave')
            # Work Entries - Public Holiday (paid leave)
            work_entries |= self.work_entry_ids.filtered(
                lambda r: not r.leave_id and r.work_entry_type_id.is_leave
                and not r.work_entry_type_id.is_unpaid)
            r.leave_days = sum(work_entries.mapped('duration_days'))
            r.leave_hours = sum(work_entries.mapped('duration'))

    def _compute_unpaid_leave_days_hours(self):
        self.flush_model()
        for r in self:
            we_unpaid_leave = r.work_entry_ids.filtered(lambda r: r.leave_id
                                                        and r.work_entry_type_id.is_unpaid)
            r.unpaid_leave_days = sum(we_unpaid_leave.mapped('duration_days'))
            r.unpaid_leave_hours = sum(we_unpaid_leave.mapped('duration'))

    def _get_worked_work_entries(self):
        leave_work_entries = self.work_entry_ids.filtered(
            lambda r: r.work_entry_type_id.is_leave
            and (not r.leave_id or r.leave_id.holiday_status_id.time_type == 'leave'))
        return self.work_entry_ids - leave_work_entries

    def _compute_worked_days_hours(self):
        for r in self:
            work_entries = r._get_worked_work_entries()
            r.worked_days = sum(work_entries.mapped('duration_days'))
            r.worked_hours = sum(work_entries.mapped('duration'))

    @api.depends('company_id')
    def _compute_salary_cycle(self):
        default_cycle = self.env.ref('to_hr_payroll.hr_salary_cycle_default', raise_if_not_found=False)
        for r in self:
            r.salary_cycle_id = r.company_id.salary_cycle_id or default_cycle

    @api.depends('thirteen_month_pay', 'thirteen_month_pay_year', 'salary_cycle_id')
    def _compute_date_from(self):
        """
        By default, the payslip period is from the previous cycle.
        For example: The payslip cycle is from 10/3 to 09/04.
            1. Today is 06/04 -> not enough for the current cycle so it will calculate the previous cycle:
                => The default payslip cycle will be the previous cycle: 10/2 -> 9/3
            2. Today is 11/04
                => The default payslip cycle will be the previous cycle: 10/3 -> 9/4
        """
        validate_year = self.env['to.base'].validate_year
        today = fields.Date.today()
        for r in self:
            cycle = r._get_salary_cycle()
            date_from = r.date_from or cycle._get_month_start_date(today + relativedelta(months=-1))
            if r.thirteen_month_pay and r.thirteen_month_pay_year:
                thirteen_month_pay_year = validate_year(r.thirteen_month_pay_year)
                r._check_thirteen_month_pay_year_valid(thirteen_month_pay_year)
                date_from = cycle._get_year_start_date(today.replace(year=thirteen_month_pay_year))
            r.date_from = date_from

    @api.depends('thirteen_month_pay', 'thirteen_month_pay_year', 'date_from')
    def _compute_date_to(self):
        for r in self:
            if not r.date_from:
                continue
            if r.thirteen_month_pay and r.thirteen_month_pay_year:
                date_to = r.date_from + relativedelta(years=1, days=-1)
            else:
                date_to = r.date_from + relativedelta(months=1, days=-1)
            r.date_to = date_to

    @api.depends('employee_id', 'date_from', 'date_to', 'thirteen_month_pay_include_trial')
    def _compute_contracts(self):
        for r in self:
            if not r.employee_id or not r.date_from or not r.date_to:
                r.contract_ids = False
            else:
                contracts = r._get_contracts()
                r.contract_ids = contracts if contracts else False

    def _compute_is_payslip_trial(self):
        for r in self:
            r.is_payslip_trial = bool(r.contract_ids.filtered('trial_date_end'))

    @api.depends('employee_id', 'contract_ids', 'date_from', 'date_to')
    def _compute_worked_days_line_ids(self):
        for r in self:
            command = [(5, 0, 0)]
            if r.employee_id and r.contract_ids and r.date_from and r.date_to and r.salary_cycle_id:
                worked_days_line_vals = r.contract_ids.sudo()._prepare_worked_day_data(r.date_from, r.date_to, r.salary_cycle_id)
                for line in worked_days_line_vals:
                    command.append((0, 0, line))
            r.worked_days_line_ids = command

    @api.depends('contract_ids')
    def _compute_contracts_count(self):
        self.flush_model()
        mapped_data = {}
        if self.ids:
            # read group, by pass ORM for performance
            self.env.cr.execute("""
            SELECT r.id as payslip_id, COUNT(DISTINCT(pshc.contract_id)) as contracts_count
            FROM hr_payslip AS r
            LEFT JOIN hr_payslip_hr_contract_rel AS pshc ON pshc.payslip_id = r.id
            WHERE r.id in %s
            GROUP BY r.id
            """, (tuple(self.ids),))
            contracts_data = self.env.cr.dictfetchall()
            mapped_data = dict([(dict_data['payslip_id'], dict_data['contracts_count']) for dict_data in contracts_data])
        for r in self:
            r.contracts_count = mapped_data.get(r.id, 0)

    # @api.model
    def _include_trial_contracts(self, thirteen_month_pay=False, thirteen_month_pay_include_trial=False):
        if thirteen_month_pay and not thirteen_month_pay_include_trial:
            include_trial_contracts = False
        else:
            include_trial_contracts = True
        return include_trial_contracts

    def _get_contracts(self):
        self.ensure_one()
        contracts = self.employee_id.with_context(
            include_trial_contracts=self._include_trial_contracts(self.thirteen_month_pay, self.thirteen_month_pay_include_trial)
            )._get_contracts(self.date_from, self.date_to, states=['open', 'close'])
        if contracts:
            contracts = contracts.sorted('date_start')
        return contracts

    @api.depends('refund_ids')
    def _compute_refunds_count(self):
        for r in self:
            r.refunds_count = len(r.refund_ids)

    @api.depends('line_ids.total', 'company_id')
    def _compute_basic(self):
        for r in self:
            basic_code = r.company_id.basic_wage_rule_categ_id and r.company_id.basic_wage_rule_categ_id.code or 'BASIC'
            r.basic_wage = r._get_salary_line_total(basic_code)

    @api.depends('line_ids.total', 'company_id')
    def _compute_personal_tax_base(self):
        for r in self:
            personal_tax_base_code = r.company_id.tax_base_rule_categ_id and r.company_id.tax_base_rule_categ_id.code or 'TAXBASE'
            r.personal_tax_base = r._get_salary_line_total(personal_tax_base_code)

    @api.depends('line_ids.total', 'company_id')
    def _compute_gross_salary(self):
        for r in self:
            gross_code = r.company_id.gross_salary_rule_categ_id and r.company_id.gross_salary_rule_categ_id.code or 'GROSS'
            r.gross_salary = r._get_salary_line_total(gross_code)

    def _get_cost_lines(self):
        self.ensure_one()
        return self.mapped('line_ids').filtered(lambda line: line.salary_rule_id.category_id.paid_by_company)

    @api.depends('line_ids.salary_rule_id.category_id.paid_by_company', 'line_ids.total')
    def _compute_company_cost(self):
        for r in self:
            r.company_cost = sum(r._get_cost_lines().mapped('total'))

    @api.depends('line_ids.total', 'company_id')
    def _compute_net(self):
        for r in self:
            net_code = r.company_id.net_income_salary_rule_categ_id and r.company_id.net_income_salary_rule_categ_id.code or 'NET'
            r.net_salary = r._get_salary_line_total(net_code)

    def _get_salary_line_total(self, code):
        lines = self.line_ids.filtered(lambda line: line.code == code)
        return sum(lines.mapped('total'))

    def _compute_details_by_salary_rule_category(self):
        for payslip in self:
            payslip.details_by_salary_rule_category = payslip.mapped('line_ids').filtered(lambda line: line.category_id)

    def _compute_cost_lines(self):
        for r in self:
            r.cost_line_ids = r._get_cost_lines()

    def _compute_payslip_lines_count(self):
        for payslip in self:
            payslip.payslip_lines_count = len(payslip.line_ids)

    @api.depends('worked_days_line_ids')
    def _compute_work_entry_ids(self):
        for r in self:
            r.work_entry_ids = r.worked_days_line_ids.work_entry_ids

    def _compute_work_entry_count(self):
        for r in self:
            r.work_entry_count = len(r.work_entry_ids)

    def _compute_we_warning(self):
        domain = [
            ('employee_id', 'in', self.employee_id.ids),
            ('contract_id', 'in', self.contract_ids.ids),
            ('date_start', '>=', min(self.mapped('date_from'))),
            ('date_stop', '<=', max(self.mapped('date_to'))),
        ]
        all_work_entries = self.env['hr.work.entry'].search(domain)
        convert_local_to_utc = self.env['to.base'].convert_local_to_utc
        for r in self:
            day_from = datetime.combine(r.date_from, time.min)
            day_from = convert_local_to_utc(day_from, r.employee_id.resource_calendar_id.tz, naive=True)
            day_to = datetime.combine(r.date_to, time.max)
            day_to = convert_local_to_utc(day_to, r.employee_id.resource_calendar_id.tz, naive=True)

            we_of_employee = all_work_entries.filtered(lambda we: we.employee_id == r.employee_id
                                                       and we.date_start >= day_from
                                                       and we.date_stop <= day_to)
            we_conflict = we_of_employee.filtered(lambda we: we.state == 'conflict')
            we_draft = we_of_employee.filtered(lambda we: we.state == 'draft')

            r.warning_we_conflict = True if we_conflict else False
            r.warning_we_no_validate = True if we_draft else False
            r.warning_we_no_exists = True if not we_of_employee else False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for r in self:
            if r.date_from and r.date_to and r.date_from > r.date_to:
                raise ValidationError(_("The 'Date From' of the payslip '%s' must be earlier than its 'Date To'.") % r.name)

    @api.constrains('employee_id', 'payslip_run_id')
    def _check_employee_batch(self):
        for r in self.filtered(lambda slip: slip.employee_id and slip.payslip_run_id):
            if r.payslip_run_id.thirteen_month_pay:
                overlap_slips = r.payslip_run_id.slip_ids.filtered(
                    lambda slip:
                        slip != r
                        and slip.employee_id == r.employee_id
                        )
            else:
                overlap_slips = r.payslip_run_id.slip_ids.filtered(
                    lambda slip:
                        slip != r
                        and slip.employee_id == r.employee_id
                        and slip.date_from < r.date_to
                        and slip.date_to > r.date_from
                        )
            if overlap_slips:
                raise UserError(_("There are more than 1 payslip for the employee '%s' in the payslip batch '%s'"
                                  " that overlaps the current one, which is not allowed.")
                                % (r.employee_id.display_name, r.payslip_run_id.display_name))

    @api.constrains('thirteen_month_pay', 'thirteen_month_pay_year')
    def _check_thirteen_month_pay_year(self):
        for r in self.filtered('thirteen_month_pay'):
            thirteen_month_pay_year = self.env['to.base'].validate_year(r.thirteen_month_pay_year)
            r._check_thirteen_month_pay_year_valid(thirteen_month_pay_year)

    def _check_thirteen_month_pay_year_valid(self, thirteen_month_pay_year):
        if thirteen_month_pay_year < 1970 or thirteen_month_pay_year >= 9999:
            raise UserError(_("The year must be between 1970 and 9998"))

    def _set_timeoff_payslip_status(self):
        """
        Mark all the related time off records as Reported in payslips
        """
        timeoff_records = self.work_entry_ids.leave_id.filtered(lambda h: not h.payslip_status)
        if timeoff_records:
            timeoff_records.write({
                'payslip_status': True
                })

    def _unset_timeoff_payslip_status(self):
        """
        Mark all the related time off records that are Reported in payslips as Not Reported in payslips
        """
        timeoff_records = self.work_entry_ids.leave_id.filtered('payslip_status')
        if timeoff_records:
            timeoff_records.write({
                'payslip_status': False
                })

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        rec = super(HrPayslip, self).copy(default)
        for input_line in self.input_line_ids:
            input_line.copy({'payslip_id': rec.id})
        for line in self.line_ids:
            line.copy({'slip_id': rec.id})
        return rec

    def action_payslip_verify(self):
        if not self.env.context.get('without_compute_sheet'):
            self.compute_sheet()
        for r in self:
            if r.state != 'draft':
                raise UserError(_("You may not be able to confirm the payslip '%s' while its status is not Draft.") % (r.name,))
        self._set_timeoff_payslip_status()
        return self.write({
            'state': 'verify',
            'date_confirmed': fields.Date.today(),
            })

    def action_payslip_done(self):
        for r in self:
            if r.state != 'verify':
                raise UserError(_("You cannot mark the payslip '%s' as done while it is not in Waiting state") % r.name)
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        self._unset_timeoff_payslip_status()
        return self.write({'state': 'cancel'})

    def action_payslip_draft(self):
        for r in self:
            if r.state != 'cancel':
                raise UserError(_("You must cancel the payslip '%s' before you can set it to Draft.") % (r.name,))
        return self.write({'state': 'draft'})

    def refund_sheet(self):
        for payslip in self:
            copied_payslip = payslip.copy({
                'credit_note': not payslip.credit_note,
                'name': _('Refund: ') + payslip.name,
                'refund_for_payslip_id': payslip.id,
                'payslip_run_id': False
                })
            number = copied_payslip.number or self.env['ir.sequence'].with_company(copied_payslip.company_id).next_by_code('salary.slip')
            copied_payslip.write({'number': number})
            copied_payslip.with_context(without_compute_sheet=True).action_payslip_verify()
        formview_ref = self.env.ref('to_hr_payroll.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('to_hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': _("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [
                (treeview_ref and treeview_ref.id or False, 'tree'),
                (formview_ref and formview_ref.id or False, 'form')
                ],
            'context': {}
        }

    def check_done(self):
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_verify_done_state(self):
        if any(self.filtered(lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))

    def _recompute_fields(self):
        self._compute_contracts()
        self._compute_worked_days_line_ids()
        self._compute_hr_payslip_contribution_line_ids()
        self._compute_input_line_ids()
        self._compute_get_dependent_deduction()

    def compute_sheet(self):
        self.flush_model()
        if not self.ids:
            return
        if not self._context.get('do_not_recompute_fields', False):
            self._recompute_fields()

        for r in self:
            if r.state != 'draft':
                raise UserError(_("You must not compute payslip %s while its state is not Draft.") % r.display_name)

        # delete old payslip lines and old personal income taxes
        ids = tuple(self.ids)
        query = """
            DELETE FROM hr_payslip_line WHERE slip_id IN %s;
            DELETE FROM payslip_personal_income_tax WHERE slip_id IN %s;
            """
        self.env.cr.execute(query, (ids, ids,))
        self.invalidate_model(['line_ids', 'payslip_personal_income_tax_ids'])

        lines_vals_list = []
        query = ""
        self.read(['id', 'state', 'display_name', 'company_id', 'number', 'personal_tax_rule_id'])

        for payslip in self:
            if not payslip.number:
                number = self.env['ir.sequence'].with_company(payslip.company_id).next_by_code('salary.slip')
                query += """UPDATE hr_payslip SET number='%s' WHERE id=%s;""" % (number, payslip.id)

            for line in payslip._prepare_payslip_line_vals_list():
                line.update({'slip_id': payslip.id})
                lines_vals_list.append(line)
        if query:
            self.env.cr.execute(query)
            self.invalidate_model(['number'])
        self.env['hr.payslip.line'].create(lines_vals_list)
        self.invalidate_model(['line_ids'])

        # compute personal tax breaks table
        # IMPORTANT: since the the tax breaks table relies on salary rules computation,
        # the code below must be executed after salary rules computation
        taxes_vals_list = []
        for r in self.filtered('personal_tax_rule_id'):
            for vals in r.personal_tax_rule_id._prepare_payslip_personal_income_tax_data(r):
                vals.update({'slip_id': r.id})
                taxes_vals_list.append(vals)
        if taxes_vals_list:
            self.env['payslip.personal.income.tax'].create(taxes_vals_list)
            self.invalidate_model(['payslip_personal_income_tax_ids'])

        return True

    def _get_salary_cycle(self):
        self.ensure_one()
        return self.salary_cycle_id or self.company_id.salary_cycle_id or self.env.ref('to_hr_payroll.hr_salary_cycle_default')

    def _get_payslips_for_13thmonth(self):
        self.ensure_one()
        if self.employee_id and self.thirteen_month_pay and self.thirteen_month_pay_year > 1970:
            # payslips in 13th payslip duration, excluding the 13th payslip for that period
            payslips = self.employee_id._get_payslips_in_duration(self.date_from, self.date_to)
        else:
            payslips = self

        if not self.thirteen_month_pay_include_trial:
            payslips = payslips.filtered(lambda ps: not ps.is_payslip_trial)
        return payslips

    def _prepare_baselocaldict(self, rules_dict):
        self.ensure_one()
        employee = self.employee_id
        # to be available in salary rule python code
        # pylint: disable=reimported
        import datetime
        import dateutil
        return {
            'datetime': wrap_module(datetime, ['date', 'datetime', 'time', 'timedelta', 'timezone', 'tzinfo', 'MAXYEAR', 'MINYEAR']),
            'dateutil': wrap_module(dateutil, {
                mod: getattr(dateutil, mod).__all__
                for mod in ['parser', 'relativedelta', 'rrule', 'tz']}),
            'fields': wrap_module(fields, []),
            'env': self.env,
            'categories': BrowsableObject(employee.id, {}, self.env),
            'rules': BrowsableObject(employee.id, rules_dict, self.env),
            'payslip': self,
            'payslips_for_13thmonth': self._get_payslips_for_13thmonth(),
            'worked_days': self.worked_days_line_ids.get_workedday_obj(),
            'worked_days_lines': self.worked_days_line_ids,
            'worked_days_paid_lines': self.worked_days_line_ids.filtered('paid_rate'),
            'advantages': self.contract_ids.get_advatages_obj(),
            'timeoff': self.work_entry_ids.leave_id,
            'contributions': self.hr_payslip_contribution_line_ids.get_contributionline_obj(),
            'inputs': self.input_line_ids.get_inputline_obj(),
            'hasattr': hasattr,
            'getattr': getattr,
            }

    def _prepare_localdict(self, rules_dict):
        return dict(self._prepare_baselocaldict(rules_dict), employee=self.employee_id, contracts=self.contract_ids)

    def _prepare_payslip_line_vals_list(self):
        self.ensure_one()
        # get the ids of the structures on the contracts and their parent id as well
        if self.struct_id:
            structures = self.struct_id._get_parent_structure()
        else:
            if self.thirteen_month_pay:
                structures = self.contract_ids[:1].with_context(thirteen_month_pay=True).get_all_structures()
            else:
                structures = self.contract_ids[:1].get_all_structures()
        rules = structures.rule_ids.sorted(key='sequence', reverse=False)

        # IMPORTANT: we keep a dict with the result because a value can be overwritten by another rule with the same code
        rules_dict = {}
        localdict = self._prepare_localdict(rules_dict)
        return rules._prepare_payslip_lines_data(localdict, rules_dict)

    @api.depends('thirteen_month_pay', 'thirteen_month_pay_year', 'date_from')
    def _compute_name(self):
        for r in self:
            r.name = r._get_salary_slip_name()

    def _get_salary_slip_name(self, employee=None, date_to=None):
        employee = employee or self.employee_id
        employee_name = employee and employee.name or _("Unknown")
        thirteen_month_pay = self._context.get('thirteen_month_pay', False) or self.thirteen_month_pay
        thirteen_month_pay_year = self._context.get('thirteen_month_pay_year', False) or self.thirteen_month_pay_year
        if thirteen_month_pay and thirteen_month_pay_year:
            return _("13th-Month Salary of %s for the year %s") % (employee_name, str(thirteen_month_pay_year))
        else:
            date_to = date_to or self.date_to
            return _('Salary Slip of %s for %s') % (employee_name, format_date(self.env, date_to, date_format='MMMM-y'))

    def sorted_by_dates(self, reverse=False):
        """
        This method sorts payslips in self by their date_from and date_to
        """
        return self.sorted(lambda r: (
            datetime.timestamp(datetime.combine(r.date_from, time.min)),
            datetime.timestamp(datetime.combine(r.date_to, time.max))
            ), reverse=reverse)

    def _get_dates(self, reverse=False):
        dates = []
        for payslip in self:
            if payslip.date_from not in dates:
                dates.append(payslip.date_from)
            if payslip.date_to not in dates:
                dates.append(payslip.date_to)
        dates.sort(reverse=reverse)
        return dates

    @api.depends('contract_ids', 'thirteen_month_pay')
    def _compute_struct(self):
        for r in self:
            struct = r.contract_ids.struct_id[:1]
            if r.thirteen_month_pay and r.contract_ids and r.contract_ids[-1].thirteen_month_struct_id:
                struct = r.contract_ids.thirteen_month_struct_id
            r.struct_id = struct

    @api.depends('struct_id')
    def _compute_input_line_ids(self):
        for r in self:
            if r.struct_id:
                command = []
                existing_input_lines = r._origin.input_line_ids if r._origin else r.input_line_ids
                input_rules = r.struct_id._get_rule_inputs()
                input_line_to_keep = existing_input_lines.filtered(lambda l: l.salary_rule_id in input_rules)
                input_line_to_remove = existing_input_lines - input_line_to_keep

                for rule in (input_rules - input_line_to_keep.salary_rule_id):
                    command.append((0, 0, {'salary_rule_id': rule.id}))

                # add to-keep lines to the command
                if input_line_to_keep:
                    command = [(4, line.id) for line in input_line_to_keep] + command
                # remove to remove lines
                if input_line_to_remove:
                    command = [(3, line.id) for line in input_line_to_remove] + command
                r.input_line_ids = command
            else:
                r.input_line_ids = False

    @api.depends('employee_id', 'contract_ids', 'date_from', 'date_to')
    def _compute_hr_payslip_contribution_line_ids(self):
        for r in self:
            command = [(5, 0, 0)]
            if r.contract_ids and r.date_from and r.date_to:
                contribution_lines = r.contract_ids.sudo()._prepare_hr_payslip_contribution_lines_vals_list(r.date_from, r.date_to)

                for vals in contribution_lines:
                    command.append((0, 0, vals))
            r.hr_payslip_contribution_line_ids = command

    def _compute_employee_partner_id(self):
        for r in self:
            r.employee_partner_id = r.employee_id.user_id.partner_id or r.employee_id.sudo().work_contact_id

    def _compute_employee_lang(self):
        for r in self:
            r.employee_lang = r.employee_partner_id.lang or self.env.lang

    def action_view_refunds(self):
        '''
        This function returns an action that display existing refund payslips of the given payslips.
        When only one found, show the refund immediately.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.action_view_hr_payslip_form')

        refund_ids = self.mapped('refund_ids')

        # choose the view_mode accordingly
        if len(refund_ids) != 1:
            action['domain'] = "[('refund_for_payslip_id', 'in', %s)]" % str(self.ids)
        elif len(refund_ids) == 1:
            res = self.env.ref('to_hr_payroll.view_hr_payslip_form', False)
            action['views'] = [(res and res.id or False, 'form')]
            action['res_id'] = refund_ids.id
        return action

    def action_view_work_entries(self):
        action = self.env['ir.actions.act_window']._for_xml_id('viin_hr_work_entry.viin_hr_work_entry_action')
        action['context'] = {}
        action['domain'] = "[('id','in',%s)]" % str(self.worked_days_line_ids.work_entry_ids.ids)
        tree_view = self.env.ref('hr_work_entry.hr_work_entry_view_tree')
        form_view = self.env.ref('hr_work_entry.hr_work_entry_view_form')
        action['views'] = [(tree_view.id, 'tree'), (form_view.id, 'form')]
        return action

    def action_payslip_send(self):
        template = self.env.ref('to_hr_payroll.email_template_payslip', raise_if_not_found=False)
        if template:
            for r in self:
                r.with_context(force_send=True).sudo().message_post_with_source(
                    template,
                    message_type='comment',
                    )

    def action_payslip_send_wizard(self):
        '''
        This function opens a window to compose an email, with the payslip batch template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        template = self.env.ref('to_hr_payroll.email_template_payslip', raise_if_not_found=False)
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'hr.payslip',
            'default_res_ids': self.ids,
            'default_use_template': template and template.id or False,
            'default_template_id': template and template.id or False,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def action_view_contracts(self):
        contracts = self.contract_ids
        action = self.env['ir.actions.act_window']._for_xml_id('hr_contract.action_hr_contract')
        action['context'] = {'search_default_group_by_state': 1}
        action['domain'] = "[('id', 'in', %s)]" % str(contracts.ids)
        return action

    def get_average_amount_in_year(self, code, months=12):
        """
        Get the average amount for 1 year according to salary rule code.
            It is useful when setting up the salary formula for the 13th salary month.
            You can customize the number of months by passing in the months argument, by default it is 12 months.
        @param code: string, salary rule code
        @param months: integer, Number of months you want to average, default is 12
        @return: float, average amount
        """
        self.ensure_one()
        months = 12 if months < 1 else months
        payslips_13th = self._get_payslips_for_13thmonth()
        total = sum(payslips_13th.line_ids.filtered(lambda r: r.code == code).mapped('total'))
        return total / months
