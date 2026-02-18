import logging

from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .browsable_object import Advantages

_logger = logging.getLogger(__name__)

TAX_POLICY = [
    ('escalation', 'Progressive Tax Table'),
    ('flat_rate', 'Flat Rate')
    ]


class HrContract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """
    _inherit = 'hr.contract'

    # Override the field `wage` for new label and help string
    # by default in the module `hr_contract`, this field is considered as gross wage.
    # However, our module `to_hr_payroll` considers this as basic wage without any allowance and advantages
    wage = fields.Monetary('Basic Wage', tracking=True,
                           compute='_compute_wage', store=True, readonly=False,
                           help="Employee's monthly basic wage (without any allowance and advantages).")
    # New fields:
    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure',
                                domain="[('type_id', '=', structure_type_id)]",
                                compute='_compute_structure', store=True,
                                tracking=True, readonly=False)
    thirteen_month_struct_id = fields.Many2one('hr.payroll.structure', string='13th-Month Salary Structure',
                                               compute='_compute_structure', store=True, tracking=True, readonly=False,
                                               domain="[('company_id','=',company_id)]", ondelete='restrict',
                                               help="If specified, thirteen-month payslips of this contract will use this"
                                               " structure instead of the default Salary Structure above specified.")
    advantage_ids = fields.One2many('hr.contract.advantage', 'contract_id', string='Monthly Advantages', auto_join=True)
    gross_salary = fields.Monetary(string='Gross Salary', compute='_compute_gross_sal', store=True, tracking=True)
    payroll_contribution_type_ids = fields.Many2many('hr.payroll.contribution.type', string='Payroll Contribution Types',
                                                     domain="[('company_id', 'in', (False, company_id))]",
                                                     help="The types of payroll contribution to be applied to the contract."
                                                     " For example, you could create contribution types such as Employee Social Insurance,"
                                                     " Employee Unemployment Insurance, etc.")
    payroll_contribution_register_ids = fields.Many2many('hr.payroll.contribution.register',
                                                         'hr_contract_payroll_contribution_register_rel', 'contract_id', 'register_id',
                                                         compute='_compute_payroll_contribution_registers', store=True,
                                                         string='Payroll Contribution Registers')
    personal_tax_policy = fields.Selection(TAX_POLICY,
       string='Personal Tax Policy', tracking=True,
       required=True, default='escalation',
       compute="_compute_from_contract_type_id", store=True, readonly=False,
       help="The taxation policy applied to the net income of the payslips of this contract.\n"
       " which is defined in Configuration > Personal Tax Rules;\n"
       "- Flat Rate: No matter how much the income is, a flat rate defined in Configuration"
       " > Personal Tax Rules will always  be applied.")
    personal_tax_rule_id = fields.Many2one('personal.tax.rule', string='Tax Rule',
                                           domain="[('personal_tax_policy', '=', personal_tax_policy)]",
                                           compute='_compute_tax_rule', store=True,
                                           readonly=False, tracking=True,
                                           help="The personal income tax rule applied to payslips of this contract")
    payslip_ids = fields.Many2many('hr.payslip', 'hr_payslip_hr_contract_rel', 'contract_id', 'payslip_id',
                                   help="Payslips related to this contract")
    payslips_count = fields.Integer(string='Payslips Count', compute='_compute_payslips_count')
    salary_computation_mode = fields.Selection([
        ('hour_basis', 'Hour Basis'),
        ('day_basis', 'Day Basis')
        ], string='Salary Computation Mode', required=True, tracking=True, default='hour_basis',
        compute="_compute_from_contract_type_id", store=True, readonly=False,
        help="How the employee salary would be computed in salary rules, based on either working days or working hours:\n"
        "* Hour Basis: salary would be computed based on working hours;\n"
        "* Day Basis: salary would be computed based on working days;\n")
    payslips_auto_generation = fields.Boolean(string='Payslips Auto-Generation',
                                              compute='_compute_payslips_auto_generation', store=True,
                                              readonly=False, tracking=True,
                                              help="If enabled, and allowed by the company's settings, payslips will be "
                                              "generated for this contract accordingly.")

    @api.depends('company_id')
    def _compute_payslips_auto_generation(self):
        for r in self:
            r.payslips_auto_generation = r.company_id.payslips_auto_generation

    @api.depends('wage', 'advantage_ids', 'advantage_ids.amount', 'advantage_ids.amount_type')
    def _compute_gross_sal(self):
        for r in self:
            advantages = r.advantage_ids.filtered(lambda t: t.amount_type == 'monthly_base')
            r.gross_salary = r.wage + sum(advantages.mapped('amount'))

    @api.depends('personal_tax_policy', 'company_id', 'contract_type_id')
    def _compute_tax_rule(self):
        tax_rules = self.env['personal.tax.rule'].search([
            ('country_id', 'in', self.company_id.country_id.ids),
            ('personal_tax_policy', 'in', self.mapped('personal_tax_policy'))
            ])
        for r in self:
            if r.personal_tax_policy == r.contract_type_id.personal_tax_policy and r.company_id.country_id == r.contract_type_id.country_id:
                r.personal_tax_rule_id = r.contract_type_id.personal_tax_rule_id
            else:
                r.personal_tax_rule_id = tax_rules.filtered(
                    lambda rule:
                    rule.country_id == r.company_id.country_id
                    and rule.personal_tax_policy == r.personal_tax_policy
                    )[:1]

    def generate_payroll_contribution_registers(self):
        self._compute_payroll_contribution_registers()
        for r in self.filtered('payroll_contribution_type_ids'):
            if not r.employee_id:
                raise UserError(_("Please select an employee first!"))
            existing_types = r.mapped('payroll_contribution_register_ids.type_id')
            vals_list = []
            for contribution_type in r.payroll_contribution_type_ids.filtered(lambda t: t.id not in existing_types.ids):
                vals_list.append(contribution_type._prepare_payroll_contribution_register_data(r))
            if vals_list:
                payroll_contribution_register_ids = self.env['hr.payroll.contribution.register'].create(vals_list)
                r.write({
                    'payroll_contribution_register_ids': [(4, reg.id) for reg in payroll_contribution_register_ids]
                    })

    def _get_contribution_advantages(self):
        return self.advantage_ids.filtered(lambda adv: adv.included_in_payroll_contribution_register)

    def _get_payroll_contribution_base(self):
        self.ensure_one()
        return self.wage + sum(self._get_contribution_advantages().mapped('amount'))

    @api.depends('employee_id', 'payroll_contribution_type_ids')
    def _compute_payroll_contribution_registers(self):
        all_registers = self.env['hr.payroll.contribution.register'].search(self._get_payroll_contribution_register_domain())
        for r in self:
            registers = all_registers.filtered(lambda reg: reg.employee_id == r.employee_id and reg.type_id.id in r.payroll_contribution_type_ids.ids)
            r.payroll_contribution_register_ids = [(6, 0, registers.ids)]

    def _compute_payslips_count(self):
        for r in self:
            r.payslips_count = len(r.payslip_ids)

    def _get_payroll_contribution_register_domain(self):
        return [
            ('employee_id', 'in', self.employee_id.ids),
            ('type_id', 'in', self.payroll_contribution_type_ids.ids)
            ]

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by hierarchy (parent=False first,
                 then first level children and so on) and without duplication
        """
        if not self._context.get('thirteen_month_pay', False):
            structures = self.mapped('struct_id')
        else:
            structures = self.thirteen_month_struct_id or self.structure_type_id.with_company(self.company_id).property_thirteen_month_struct_id or self.struct_id
        if not structures:
            return self.env['hr.payroll.structure']
        structure_ids = list(set(structures._get_parent_structure().ids))
        return self.env['hr.payroll.structure'].browse(structure_ids)

    def _prepare_contrib_history_date_breaks(self, date_from=None, date_to=None):
        """
        Breaks the contribution period by months, and according with the periods of contracts.
        """
        period_iter = self.env['to.base'].period_iter
        date_breaks = []
        last_break = None
        for r in self.sorted('date_start'):
            if date_to < r.date_start or r.date_end and date_from > r.date_end:
                continue
            dt_from, dt_to = r._qualify_interval(date_from, date_to)
            contract_date_breaks = period_iter(period_name='monthly', dt_start=dt_from, dt_end=dt_to)
            # If last break point is the connect date between old an new contracts, and it is not
            # the start of month, we should remove that break point because in real, the contribution
            # is still running without any gaps.
            if last_break and last_break == contract_date_breaks[0]:
                contract_date_breaks.pop(0)
                if last_break.day != 1:
                    date_breaks.pop()
            date_breaks += contract_date_breaks
            last_break = date_breaks[-1] + relativedelta(days=1)
        date_breaks = list(set(date_breaks))
        date_breaks.sort()
        return date_breaks

    def _prepare_hr_payslip_contribution_lines_vals_list(self, date_from=None, date_to=None):
        self.employee_id.ensure_one()
        vals_list = []

        # calculate only with real value, this will help to recalculate compute when save button is pressed
        # virtual value: hr.contract(<NewId origin=2>,) => return []
        if not all([isinstance(contract.id, int) for contract in self]):
            return vals_list

        # real value: hr.contract(2)
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('payroll_contribution_reg_id', 'in', self.payroll_contribution_register_ids.ids),
            ('date_from', '<=', date_to),
            '|', ('date_to', '=', False), ('date_to', '>', date_from)]

        for line in self.env['hr.payroll.contribution.history'].search(domain):
            last_dt = None
            contrib_from = max(line.date_from, date_from)
            contrib_to = min(line.date_to, date_to) if line.date_to else date_to
            for dt in self._prepare_contrib_history_date_breaks(contrib_from, contrib_to):
                if not last_dt:
                    last_dt = dt
                    continue
                dt_from = max(line.date_from, last_dt)
                dt_to = min(line.date_to, dt) if line.date_to else dt
                vals = line._prepare_hr_payslip_contribution_line_data(dt_from, dt_to)
                vals_list.append(vals)
                last_dt = dt + relativedelta(days=1)

        return vals_list

    def _prepare_payslip_working_month_calendar_line_vals_list(self, date_from, date_to):
        vals_list = []
        self = self.sorted('date_start')
        last_contract = self[-1:]
        for contract in self:
            # prepare pre-contract calendar line data
            if date_from < contract.date_start:
                vals = contract.resource_calendar_id._prepare_payslip_working_month_calendar_line_data(date_from, contract.date_start - relativedelta(days=1))
                vals_list.append(vals)
                date_from = contract.date_start
            # prepare contract calendar line data for the contract period
            vals = contract._prepare_payslip_working_month_calendar_line_data(date_from, date_to)
            vals_list.append(vals)
            # set date_from for the next contract
            if contract.date_end:
                date_from = contract.date_end + relativedelta(days=1)
                # prepare post-contract calendar line data for the the last contract
                if contract == last_contract and date_to > contract.date_end:
                    vals = contract.resource_calendar_id._prepare_payslip_working_month_calendar_line_data(date_from, date_to)
                    vals_list.append(vals)
        return vals_list

    def _prepare_payslip_data(self, date_from, date_to):
        payslip_run_id = self._context.get('payslip_run_id', False)
        credit_note = self._context.get('credit_note', False)
        thirteen_month_pay = self._context.get('thirteen_month_pay', False)
        thirteen_month_pay_year = self._context.get('thirteen_month_pay_year', False)
        thirteen_month_pay_include_trial = self._context.get('thirteen_month_pay_include_trial', False)
        salary_cycle_id = self._context.get('salary_cycle_id', False) or self.company.salary_cycle_id
        date_from, date_to = self._qualify_interval(date_from, date_to)
        res = {
            'name': self.env['hr.payslip'].with_context(
                thirteen_month_pay=thirteen_month_pay,
                thirteen_month_pay_year=thirteen_month_pay_year
                )._get_salary_slip_name(self.employee_id, date_to),
            'struct_id': self.struct_id.id,
            'company_id': self.employee_id.company_id.id,
            'salary_cycle_id': salary_cycle_id.id,
            'employee_id': self.employee_id.id,
            'payslip_run_id': payslip_run_id,
            'date_from': date_from,
            'date_to': date_to,
            'credit_note': credit_note,
            'thirteen_month_pay': thirteen_month_pay,
            'thirteen_month_pay_year': thirteen_month_pay_year,
            'thirteen_month_pay_include_trial': thirteen_month_pay_include_trial
        }
        return res

    def action_view_payslips(self):
        action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.act_hr_employee_payslip_list')

        # override the context to get rid of the default filtering
        action['context'] = {
            'default_employee_id': self.employee_id.id,
            'default_contract_id': self.id,
            'default_company_id': self.company_id.id
            }

        # choose the view_mode accordingly
        if self.payslips_count != 1:
            action['domain'] = "[('id', 'in', %s)]" % str(self.payslip_ids.ids)
        elif self.payslips_count == 1:
            res = self.env.ref('to_hr_payroll.view_hr_payslip_form', False)
            action['views'] = [(res and res.id or False, 'form')]
            action['res_id'] = self.payslip_ids.id
        return action

    @api.depends('job_id')
    def _compute_wage(self):
        for r in self:
            r.wage = r.job_id.wage

    @api.depends('contract_type_id')
    def _compute_from_contract_type_id(self):
        for r in self:
            r.salary_computation_mode = r.contract_type_id.salary_computation_mode or r.salary_computation_mode
            r.personal_tax_policy = r.contract_type_id.personal_tax_policy or r.personal_tax_policy

    @api.depends('structure_type_id')
    def _compute_structure(self):
        for r in self:
            r.struct_id = r.structure_type_id.with_company(r.company_id).property_regular_struct_id
            r.thirteen_month_struct_id = r.structure_type_id.with_company(r.company_id).property_thirteen_month_struct_id

    def get_advatages_obj(self):
        """
        Get an Advantages object for usage in salary rule python code
        @return: Advantages object
        @rtype: Advantages
        """
        advatages_dict = {}
        for code in self.advantage_ids.mapped('code'):
            advatages_dict[code] = self.advantage_ids.filtered(lambda r: r.code == code)
        return Advantages(self.employee_id.id, advatages_dict, self.env)

    def get_contract_advatage_by_code(self, code):
        self.ensure_one()
        return self.advantage_ids.filtered(lambda r: r.code == code)

    def get_advatage_amount_by_code(self, code):
        return self.get_contract_advatage_by_code(code).amount

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contract_with_payslip(self):
        for r in self:
            if r.payslip_ids:
                raise UserError(_("You cannot delete the contract %s while it is still referred by the payslip %s."
                                  " It is required to delete all the related payslip first. Or, you could close/"
                                  "cancel the contract.")
                                % (r.name, r.payslip_ids[0].name))

    def _get_trial_period(self):
        """
        Get the trial period of the contract, if applicable

        :return: (trial_date_start, trial_date_end) in tuple of datetime.datetime or (None, None)
        :rtype: tuple
        """
        self.ensure_one()
        if self.trial_date_end and self.trial_date_end >= self.date_start:
            trial_date_start = datetime.combine(self.date_start, time.min)
            trial_date_end = datetime.combine(self.trial_date_end, time.max)
            return trial_date_start, trial_date_end
        else:
            return None, None

    def _get_discrepancy_fields(self):
        """get list of fields having different values between contracts in self"""
        group_fields = self._get_group_fields_for_payslip_consolidation()
        # apply sudo to avoid access error when get value of protected fields such as
        # analytic_account_id, analytic_tags_ids
        first_contract = self[:1].sudo()
        field_list = []
        for r in self[1:].sudo():
            _list = [f for f in group_fields if getattr(r, f) != getattr(first_contract, f)]
            field_list += _list
        return field_list

    @api.model
    def _get_group_fields_for_payslip_consolidation(self):
        return ['company_id', 'department_id', 'struct_id', 'job_id', 'work_entry_source', 'resource_calendar_id']

    def _get_group_hashcode_for_payslip_consolidation(self):
        self.ensure_one()
        d = {}
        # apply sudo to avoid access error when get value of protected fields such as
        # analytic_account_id, analytic_tags_ids
        self_sudo = self.sudo()
        for field in self._get_group_fields_for_payslip_consolidation():
            d[field] = getattr(self_sudo, field) or 'False'

        hashcode = []
        for k, v in d.items():
            hashcode.append('%s:%s' % (k, v))
        hashcode = '-'.join(hashcode)
        return hashcode

    def _get_leave_domain(self, start_dt, end_dt):
        # Override, make sure all leave types can generate Work Entry automatically, Kind of Time Off includes Working Time a& Absence
        # some cases: business trip, work from home
        return [
            # ('time_type', '=', 'leave'),
            '|', ('calendar_id', 'in', [False] + self.resource_calendar_id.ids),
                 ('holiday_id.employee_id', 'in', self.employee_id.ids),
            ('resource_id', 'in', [False] + self.employee_id.resource_id.ids),
            ('date_from', '<=', end_dt),
            ('date_to', '>=', start_dt),
            ('company_id', 'in', [False, self.company_id.id]),
        ]

    def _prepare_worked_day_data(self, date_from, date_to, salary_cycle):
        """
        @param date_from, date_to: date, desired time period
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        convert_local_to_utc = self.env['to.base'].convert_local_to_utc
        datetime_list = salary_cycle._get_month_start_dates(date_from, date_to)
        for cycle_date in datetime_list:
            # start and end date of the salary cycle
            start_cycle = salary_cycle._get_month_start_date(cycle_date).date()
            end_cycle = salary_cycle._get_month_end_date(cycle_date).date()
            # valid time between payslip and salary cycle
            start_ = max(start_cycle, date_from)
            end_ = min(end_cycle, date_to)

            for contract in self:
                # TODO: fix _qualify_interval mehod. This method is not correct when the transmission time is invalid
                # get the valid time between contract and payslip period to calculate the work and leave time
                # date_start, date_end = contract._qualify_interval(start_, end_)

                # valid time between payslip and salary cycle and contract
                if contract.date_start > end_:
                    continue
                elif contract.date_end and contract.date_end < start_:
                    continue
                date_start = max(start_, contract.date_start)
                date_end = min(end_, contract.date_end) if contract.date_end else end_

                day_from = datetime.combine(date_start, time.min)
                day_to = datetime.combine(date_end, time.max)
                day_from = convert_local_to_utc(day_from, contract.resource_calendar_id.tz, naive=True)
                day_to = convert_local_to_utc(day_to, contract.resource_calendar_id.tz, naive=True)
                # eg: 2023-04-30 17:00:00 -> 2023-05-01 00:00:00 (UTC +7)
                domain = [
                    ('employee_id', '=', contract.employee_id.id),
                    ('contract_id', '=', contract.id),
                    ('date_start', '>=', day_from),
                    ('date_stop', '<=', day_to),
                    ('state', '=', 'validated')
                ]
                all_work_entries = self.env['hr.work.entry'].search(domain)
                for entry_type in all_work_entries.work_entry_type_id:
                    work_entries = all_work_entries.filtered(lambda r: r.work_entry_type_id == entry_type)
                    work_days_data = {
                        'entry_type_id': entry_type.id,
                        'contract_id': contract.id,
                        'date_from': start_cycle,
                        'date_to': end_cycle,
                        'number_of_hours': sum(work_entries.mapped('duration')),
                        'number_of_days': sum(work_entries.mapped('duration_days')),
                        'work_entry_ids': [(6, 0, work_entries.ids)]
                    }
                    res.append(work_days_data)
        return res

    def action_view_registers(self):
        action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.to_hr_payroll_contribution_register_action')

        # override the context to get rid of the default filtering
        action['context'] = {
            'default_employee_id': self.employee_id.id,
            'default_company_id': self.company_id.id
            }

        # choose the view_mode accordingly
        action['domain'] = "[('id', 'in', %s)]" % str(self.payroll_contribution_register_ids.ids)
        return action
