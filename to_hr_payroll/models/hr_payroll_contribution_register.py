from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import format_date
from dateutil.relativedelta import relativedelta


class HRPayrollContributionRegister(models.Model):
    _name = 'hr.payroll.contribution.register'
    _description = 'Payroll Contribution Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'registered_number'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True,
                                  help='The employee to register a payroll contribution')

    currency_id = fields.Many2one(related='employee_id.company_id.currency_id', store=True, copy=False)

    company_id = fields.Many2one(related='employee_id.company_id', store=True, copy=False)

    type_id = fields.Many2one('hr.payroll.contribution.type',
                                        required=True,
                                        tracking=True,
                                        domain="[('company_id', 'in', (False, company_id))]",
                                        string='Type')
    computation_block = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ], string='Computation Block', required=True, default='month',
        compute='_compute_computation_block', store=True, readonly=False,
        help="Minimum block for contribution computation.\n")
    days_in_months = fields.Selection([('fixed', 'Fixed as 28 days'), ('flexible', 'Flexible')], string='Days in Month', required=True, default='fixed',
                                      compute='_compute_days_in_months', store=True, readonly=False,
                                      help="During payslip contributions computation,\n"
                                      "- Fixed as 28 days: every month will be considered to have 28 days in total\n"
                                      "- Flexible: the number of days depends on the actual month, which varies from 28 to 31.")
    computation_method = fields.Selection([
        ('half_up', 'Half-up Duration Rounding'),
        ('max_unpaid_days', 'Unpaid Days Limitation'),
        ], string='Computation Method', readonly=False, required=True,
        compute='_compute_computation_method', store=True,
        help="- Half-up Duration Rounding: If worked duration of employee in month is greater or equal to a half of total days in month, contribution will be calculated.\n"
             "- Unpaid Days Limitation: If employee has total unpaid days less than the following limit in a month, contribution will be calculated.")
    max_unpaid_days = fields.Float('Maximum Unpaid Days', readonly=False, compute='_compute_max_unpaid_days', store=True)

    registered_number = fields.Char(string='Registration Number',
                                    copy=False,
                                    tracking=True,
                                    help='The official registered number. E.g. Insurance Number')

    date_from = fields.Date('Date From',
                            required=True,
                            default=fields.Date.today(), copy=False,
                            tracking=True,
                            help='The date from which the employee registers for contribution to the selected payroll_contribution')
    date_suspended = fields.Date('Date Suspended',
                                 readonly=True, copy=False,
                                 tracking=True,
                                 help="The date from which the employee temporarily stops his/her contribution to the payroll_contribution")
    date_resumed = fields.Date('Date Resumed',
                               readonly=True, copy=False,
                               tracking=True,
                               help="The date from which the employee resumes his/her contribution to the payroll_contribution")
    date_to = fields.Date('Date To',
                          readonly=True, copy=False,
                          tracking=True,
                          help='The date from which the employee stop contribution to the selected payroll_contribution')

    contribution_base = fields.Monetary('Computation Base',
                                     tracking=True,
                                     help='The base for calculation of payroll contribution with the rate specified'
                                     ' in Employee Contribution Rate of the selected Type')
    employee_contrib_reg_id = fields.Many2one('hr.contribution.register',
                                              related='type_id.employee_contrib_reg_id',
                                              string='Employee Contribution Register',
                                              help='Links to a contribution register that involves Employee\'s contribution')

    employee_contrib_rate = fields.Float(string='Employee Contribution Rate',
                                         tracking=True, readonly=False,
                                         compute='_compute_employee_contrib_rate', store=True,
                                         help="The rate in percentage of either the Computation Base specified above or the"
                                         " taxable income of the employee that the employee contributes")
    company_contrib_rate = fields.Float(string='Company Contribution Rate (%)',
                                        tracking=True, readonly=False,
                                        compute='_compute_company_contrib_rate', store=True,
                                        help="The rate in percentage of either the Computation Base specified above or the"
                                        " taxable income of the employee that the company contributes")

    payslips_count = fields.Integer(compute='_compute_payslips_count', string="Payslip Line Computation Details")

    partner_id = fields.Many2one('res.partner',
                                 related='type_id.employee_contrib_reg_id.partner_id',
                                 string='Contribution Partner')

    state = fields.Selection([
        ('draft', "Draft"),
        ('confirmed', "Confirmed"),
        ('suspended', "Suspended"),
        ('resumed', "Resumed"),
        ('done', "Closed"),
        ('cancelled', "Cancelled")
        ], default='draft', required=True, copy=False, readonly=True, tracking=True, string='Status',
        help='Status of the payroll contribution register')

    payroll_contribution_history_ids = fields.One2many('hr.payroll.contribution.history', 'payroll_contribution_reg_id',
                                                     readonly=True, copy=False,
                                                     string="Payroll Contribution History")

    current_history_id = fields.Many2one('hr.payroll.contribution.history', string='Current History Line', readonly=True, copy=False,
                                         compute='_compute_current_history_id', store=True, help="Technical field to store the current history line data")

    @api.constrains('employee_id', 'type_id', 'registered_number')
    def _check_registered_number_duplicates(self):
        for r in self:
            if r.registered_number and r.type_id and r.employee_id:
                existing = self.search([
                    ('id', '!=', r.id),
                    ('registered_number', '=', r.registered_number),
                    ('employee_id', '=', r.employee_id.id),
                    ('type_id', '=', r.type_id.id)], limit=1)
                if existing:
                    raise ValidationError(_("There is another registration with the same employee and same registration number of %s."
                                            " Please use that existing one instead of creating new one, or enter another registration number.")
                                            % (r.type_id.name,))

    @api.depends('type_id', 'registered_number', 'employee_id')
    def _compute_display_name(self):
        for r in self:
            if r.type_id and r.employee_id:
                if r.registered_number:
                    r.display_name = '[' + r.registered_number + '] ' + r.type_id.name + ' - ' + r.employee_id.name
                else:
                    r.display_name = r.type_id.name + ' - ' + r.employee_id.name
            else:
                r.display_name = r.registered_number

    @api.depends('type_id')
    def _compute_computation_block(self):
        for r in self:
            if r.type_id:
                r.computation_block = r.type_id.computation_block
            else:
                r.computation_block = 'month'

    @api.depends('type_id')
    def _compute_days_in_months(self):
        for r in self:
            if r.type_id:
                r.days_in_months = r.type_id.days_in_months
            else:
                r.days_in_months = 'fixed'

    @api.depends('type_id')
    def _compute_computation_method(self):
        for r in self:
            if r.type_id:
                r.computation_method = r.type_id.computation_method
            else:
                r.computation_method = 'half_up'

    @api.depends('type_id')
    def _compute_max_unpaid_days(self):
        for r in self:
            if r.type_id:
                r.max_unpaid_days = r.type_id.max_unpaid_days
            else:
                r.max_unpaid_days = 14.0

    @api.depends('type_id')
    def _compute_employee_contrib_rate(self):
        for r in self:
            if r.type_id:
                r.employee_contrib_rate = r.type_id.employee_contrib_rate
            else:
                r.employee_contrib_rate = 0.0

    @api.depends('type_id')
    def _compute_company_contrib_rate(self):
        for r in self:
            if r.type_id:
                r.company_contrib_rate = r.type_id.company_contrib_rate
            else:
                r.company_contrib_rate = 0.0

    @api.depends('payroll_contribution_history_ids')
    def _compute_current_history_id(self):
        for r in self:
            if r.payroll_contribution_history_ids:
                r.current_history_id = r.payroll_contribution_history_ids.sorted(key=lambda r: r.date_from, reverse=True)[:1]
            else:
                r.current_history_id = False

    def action_draft(self):
        for r in self:
            if r.state != 'cancelled':
                raise ValidationError(_("You cannot set an payroll contribution register back to draft state while its state is not Cancelled!"))
        self.write({'state': 'draft'})

    def action_cancel(self):
        for r in self:
            if r.state not in ('confirmed', 'done', 'suspended', 'resumed'):
                raise ValidationError(_("You may not be able to cancel the Payroll Contribution Register '%s' while its state is neither"
                                        " Confirmed nor Suspended nor Resumed nor Done."))
            if r.payslips_count > 0:
                raise ValidationError(_("You cannot set cancel a payroll contribution register while it links to a payslip line"))

        self.mapped('payroll_contribution_history_ids').unlink()
        self.write({
            'date_suspended': False,
            'date_resumed': False,
            'date_to': False,
            'state': 'cancelled',
            })

    def _prepare_history_data(self, date_from, state, date_to=None):
        return {
            'payroll_contribution_reg_id': self.id,
            'contribution_base': self._context.get('contribution_base', self.contribution_base) or 0.0,
            'employee_contrib_rate': self._context.get('employee_contrib_rate', self.employee_contrib_rate) or 0.0,
            'company_contrib_rate': self._context.get('company_contrib_rate', self.company_contrib_rate) or 0.0,
            'date_from': date_from,
            'date_to': date_to or False,
            'state': state,
            'employee_id': self.employee_id.id,
            }

    def _create_history(self, date_from, state, date_to=None, update_existing=False):
        History = self.env['hr.payroll.contribution.history']
        data = self._prepare_history_data(date_from, state, date_to)
        existing = History.search([
            ('payroll_contribution_reg_id', '=', self.id),
            ('type_id', '=', self.type_id.id),
            ('date_from', '=', data['date_from']),
            ('state', '=', data['state'])
            ])
        if existing:
            if update_existing:
                existing.write(data)
            return existing
        return History.create(data)

    def _ensure_not_modify_past_history(self, date):
        self.ensure_one()
        if self.current_history_id and date < self.current_history_id.date_from:
            raise ValidationError(_("The date `%s` is not valid for the `%s` for %s. You may have two options as below:\n"
                                    "* Specifying a date that is later than or equal to `%s`;\n"
                                    "* Excluding the above mentioned register from modification if you want to continue with the others;")
                                    % (
                                        format_date(self.env, date),
                                        "%s [%s]" % (self.type_id.name, self.registered_number) if self.registered_number else self.type_id.name,
                                        self.employee_id.name,
                                        format_date(self.env, self.current_history_id.date_from)
                                        )
                                    )

    def _link_contracts(self):
        next1000years = fields.Date.today() + relativedelta(years=1000)
        self_sorted = self.sorted(lambda reg: (reg.date_from, reg.date_to or next1000years))
        contracts = self.employee_id._get_contracts(
            date_from=self_sorted[:1].date_from,
            date_to=self_sorted[-1:].date_to or next1000years,
            states=['open', 'close']
            )
        for employee in self.employee_id:
            for contract in contracts.filtered(lambda c: c.employee_id == employee):
                registers = self_sorted.filtered(
                    lambda reg: reg.employee_id == contract.employee_id
                    and (
                            (not reg.date_to or reg.date_to > contract.date_start)
                            or (contract.date_end and reg.date_from < contract.date_end)
                        )
                    )
                contract.write({
                    'payroll_contribution_type_ids': [(4, regtype.id) for regtype in registers.type_id]
                    })

    def action_change_base(self):
        if self._context.get('call_wizard'):
            action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.hr_payroll_contrib_action_change_base_action')
            action['context'] = {'default_payroll_contribution_reg_ids': self.ids}
            return action
        date = self._context.get('contribution_base_change_date', False)
        if not date:
            raise ValidationError(_("Please specify the date on which the Computation Base is changed"))

        new_base = None
        if 'contribution_base' in self._context:
            new_base = self._context.get('contribution_base')
        if new_base is None:
            return

        for r in self:
            r._ensure_not_modify_past_history(date)
            update_vals = {}
            # if we are modifying the current history
            if r.current_history_id and date == r.current_history_id.date_from and new_base:
                r.current_history_id.write({'contribution_base': new_base})
                update_vals['contribution_base'] = new_base
            else:
                r.current_history_id.write({'date_to': r._prepare_date_to(date)})
                history_id = r._create_history(date_from=date, state='confirmed', date_to=None, update_existing=True)
                update_vals.update({
                    'current_history_id': history_id.id,
                    'contribution_base': new_base
                    })
            r.write(update_vals)

    def action_change_rates(self):
        if self._context.get('call_wizard'):
            action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.hr_payroll_contrib_action_change_rates_action')
            action['context'] = {'default_payroll_contribution_reg_ids': self.ids}
            return action
        date = self._context.get('contribution_rates_change_date', False)
        if not date:
            raise ValidationError(_("Please specify the date on which the Payroll Contribution Rate change happened!"))

        new_employee_contrib_rate = None
        if 'employee_contrib_rate' in self._context:
            new_employee_contrib_rate = self._context.get('employee_contrib_rate')

        new_company_contrib_rate = None
        if 'company_contrib_rate' in self._context:
            new_company_contrib_rate = self._context.get('company_contrib_rate')

        if new_employee_contrib_rate is None and new_company_contrib_rate is None:
            return

        for r in self:
            r._ensure_not_modify_past_history(date)

            update_data = {}
            if new_employee_contrib_rate is not None:
                update_data['employee_contrib_rate'] = new_employee_contrib_rate
            if new_company_contrib_rate is not None:
                update_data['company_contrib_rate'] = new_company_contrib_rate

            # if we are modifying the current history
            if r.current_history_id and date == r.current_history_id.date_from:
                r.current_history_id.write(update_data)
            else:
                r.current_history_id.write({'date_to': r._prepare_date_to(date)})
                history_id = r._create_history(date_from=date, state=r.current_history_id.state, date_to=None, update_existing=True)
                update_data['current_history_id'] = history_id.id

            r.write(update_data)

    def action_confirm(self):
        for r in self:
            new_history = r._create_history(r.date_from, 'confirmed')
            r.write({
                'current_history_id': new_history.id,
                'state': 'confirmed',
                })
        self._link_contracts()

    def _prepare_date_to(self, date):
        """
        to_date is one day earlier than the given date
        @param date: (string)
        @return: date string
        """
        return date - relativedelta(days=1)

    def action_suspend(self):
        if self._context.get('call_wizard'):
            action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.hr_payroll_contrib_action_suspend_action')
            action['context'] = {'default_payroll_contribution_reg_ids': self.ids}
            return action
        for r in self:
            if r.state not in ('confirmed', 'resumed', 'done'):
                raise ValidationError(_("You cannot suspend the contribution register '%s' while its state is neither Confirmed nor Resumed nor Done.") % (r.display_name,))
            r._ensure_not_modify_past_history(r.date_suspended)
            if r.date_suspended < r.date_from:
                raise ValidationError(_("The Date Suspended (%s) must NOT be earlier than the Date From (%s)")
                                      % (format_date(r.env, r.date_suspended), format_date(r.env, r.date_from)))
            r.current_history_id.write({
                'date_to': r._prepare_date_to(r.date_suspended)
                })
            new_history = r._create_history(r.date_suspended, 'suspended')
            r.write({
                'current_history_id': new_history.id,
                'state': 'suspended',
                })

    def action_resume(self):
        if self._context.get('call_wizard'):
            action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.hr_payroll_contrib_action_resume_action')
            action['context'] = {'default_payroll_contribution_reg_ids': self.ids}
            return action
        for r in self:
            r._ensure_not_modify_past_history(r.date_resumed)
            if r.state not in ('suspended', 'done'):
                raise ValidationError(_("You cannot resume the contribution register '%s' while its state is neither Suspended nor Done.")
                                      % (r.display_name,))

            if r.date_resumed and r.date_suspended and r.date_resumed < r.date_suspended:
                raise ValidationError(_("The Date Resumed (%s) must NOT be earlier than the Date Suspended (%s)")
                                      % (format_date(r.env, r.date_resumed), format_date(r.env, r.date_suspended)))
            if not r.date_resumed:
                raise ValidationError(_("Date Resumed is required!"))

            r.current_history_id.write({'date_to': r._prepare_date_to(r.date_resumed)})
            new_history = r._create_history(r.date_resumed, 'resumed')
            data = {
                'current_history_id': new_history.id,
                'state': 'resumed',
                }

            if 'contribution_base' in self._context:
                data['contribution_base'] = self._context.get('contribution_base')

            if 'employee_contrib_rate' in self._context:
                data['employee_contrib_rate'] = self._context.get('employee_contrib_rate')

            if 'company_contrib_rate' in self._context:
                data['company_contrib_rate'] = self._context.get('company_contrib_rate')

            r.write(data)

    def action_done(self):
        if self._context.get('call_wizard'):
            action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.hr_payroll_contrib_action_done_action')
            action['context'] = {'default_payroll_contribution_reg_ids': self.ids}
            return action
        ctx_date_to = self._context.get('date_to', False)
        for r in self:
            if r.state not in ('suspended', 'confirmed', 'resumed'):
                raise ValidationError(_("You cannot mark the contribution register '%s' as Closed while its state is neither Suspended"
                                        " nor Confirmed nor Resumed.")
                                        % (r.display_name,))

            date_to = ctx_date_to or r.date_to or fields.Date.today()
            r._ensure_not_modify_past_history(date_to)

            if date_to < r.date_from:
                raise ValidationError(_("The Closed Date (%s) must NOT be earlier than the Date From (%s)")
                                      % (format_date(r.env, date_to), format_date(r.env, r.date_from)))

            if r.date_suspended and date_to < r.date_suspended:
                raise ValidationError(_("The Closed Date (%s) must NOT be earlier than the Date Suspended (%s)")
                                      % (format_date(r.env, date_to), format_date(r.env, r.date_suspended)))

            if r.date_resumed and date_to < r.date_resumed:
                raise ValidationError(_("The Closed Date (%s) must NOT be earlier than the Date Resumed (%s)")
                                      % (format_date(r.env, date_to), format_date(r.env, r.date_resumed)))

            r.current_history_id.write({'date_to': r._prepare_date_to(date_to)})
            new_history = r._create_history(date_to, 'done')
            r.write({
                'date_to': date_to,
                'current_history_id': new_history.id,
                'state': 'done',
                })

    def valid_for_sal_rule(self, payslip_date_from, payslip_date_to, delta=15):
        for history in self.payroll_contribution_history_ids:
            if history.valid_for_sal_rule(payslip_date_from, payslip_date_to, delta):
                return True
        return False

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
        name search that supports searching by tag code
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', ('registered_number', '=ilike', name + '%'), '|', ('employee_id.name', operator, name), ('type_id.name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        recs = self.search(domain + args, limit=limit)
        return [(record.id, record.display_name) for record in recs.sudo()]

    def get_employee_payslip_lines(self):
        domain = [('employee_id', '=', self.employee_id.id), ('register_id', '=', self.employee_contrib_reg_id.id)]
        return self.env['hr.payslip.line'].search(domain)

    def _compute_payslips_count(self):
        History = self.env['hr.payroll.contribution.history']
        for r in self:
            payslip_ids = History.search([('payroll_contribution_reg_id', '=', r.id)]).mapped('hr_payslip_contribution_line_ids.payslip_id')
            r.payslips_count = len(payslip_ids)

    @api.constrains('employee_id', 'type_id', 'date_from')
    def constrains_registration(self):
        for r in self:
            if r.employee_id and r.type_id:
                existing_regs = self.search([
                    ('id', '!=', r.id),
                    ('employee_id', '=', r.employee_id.id),
                    ('type_id', '=', r.type_id.id),
                    ('state', '!=', 'done'),
                    ])
                for reg in existing_regs:
                    if reg.date_from and reg.date_to:
                        if r.date_from >= reg.date_from and r.date_from <= reg.date_to:
                            raise ValidationError(_("The employee '%s' currently has a registration with the same payroll contribution type that overlapping"
                                                  " the duration of this registration. Please re-input Date From of this registration")
                                                    % (r.employee_id.name,))
                        if r.date_to and r.date_to >= reg.date_from and r.date_to <= reg.date_to:
                            raise ValidationError(_("The employee '%s' currently has a registration with the same payroll contribution type that overlapping"
                                                  " the duration of this registration. Please re-input Date To of this registration")
                                                    % (r.employee_id.name,))
                    else:
                        if r.date_from >= reg.date_from:
                            raise ValidationError(_("The employee '%s' currently has a registration with the same payroll contribution type that overlapping"
                                                  " the duration of this registration. Please close/delete that registration before creating a new one.")
                                                    % (r.employee_id.name,))

    def action_view_payslips(self):
        payslip_ids = self.payroll_contribution_history_ids.hr_payslip_contribution_line_ids.payslip_id
        action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.action_view_hr_payslip_form')

        # choose the view_mode accordingly
        if len(payslip_ids) != 1:
            action['domain'] = "[('id', 'in', " + str(payslip_ids.ids) + ")]"
        elif len(payslip_ids) == 1:
            res = self.env.ref('to_hr_payroll.view_hr_payslip_form', False)
            action['views'] = [(res and res.id or False, 'form')]
            action['res_id'] = payslip_ids.id
        return action

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_state(self):
        for r in self:
            if r.state != 'draft':
                raise UserError(_("You may not be able to delete the payroll contribution register '%s' while its state is not Draft.")
                                % (r.display_name,))

    def unlink(self):
        self.mapped('payroll_contribution_history_ids').unlink()
        return super(HRPayrollContributionRegister, self).unlink()
