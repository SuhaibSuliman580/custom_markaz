from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _inherit = ['abstract.hr.salary.rule', 'mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'
    _description = 'Salary Rule'

    def _default_python_help(self):
        return _('''
# Available variables:
#----------------------
# datetime: Python datetime library. For example, datetime.date.today() will return the current date and datetime.datetime.now() will return the current date and time
# dateutil: Python dateutil library
# fields: odoo.fields class
# relativedelta': dateutil.relativedelta.relativedelta,
# rrule: dateutil.rrule
# env': payslip environment,
# payslip: object containing the payslips
# payslips_for_13thmonth: the object containing all the payslips of the year specified by the field '13th-Month Pay Year' of the current payslip when thirteen month salary is enabled for the current payslip. Otherwise, this contains the current payslip
# worked_days: object containing the payslip work days. For example, worked_days.WORK100.number_of_hours to take the hour of 'WORK100' work entry type. Or worked_days.WORK100.records to take the list of records of 'WORK100' work entry type
# worked_days_lines: hr.payslip.worked_days records, period of work on the payslip
# worked_days_paid_lines: hr.payslip.worked_days records, period of work is used to calculate salary.
# employee: hr.employee object
# contracts: hr.contract object
# A_RULE_CODE: a code that returns the corresponding salary rule's result
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# advantages: object containing the computed contract advantages. For example, advantages.TRAVEL.amount to take the amount of travel allowance specified on the contract
# timeoff: leaves
# contributions: object containing the computed payslip contributions. For example, contributions.SOCIAL_INSURANCE.employee_contrib_rate to take the rate of the social insurance contribution by employee, contributions.SOCIAL_INSURANCE.employee_contribution to take the payslip's social insurance contribution amount by employee
# inputs: object containing the computed inputs. For example, inputs.CODE.amount where code is a custom code defined for a desired input
#
# Available Functions:
#---------------------
# hasattr: the built-in Python hasattr function
# getattr: the built-in Python getattr function

# get_advatage_amount_by_code: called through a hr.contract record, returns the contract allowance amount according to the input code
#                                e.g: contracts[0].get_advatage_amount_by_code('TRAVEL')

# get_average_amount_in_year: called through a hr.payslip record, returns the average amount for 1 year (can input the number of months you want to divide evenly, default is divided by 12)
#                                e.g: payslip.payslip.get_average_amount_in_year('TRAVEL')
#                                  or payslip.payslip.get_average_amount_in_year('TRAVEL', 6)

# Note: returned value have to be set in the variable 'result'

result = NET > categories.NET * 0.10''')

    # enable changes tracking for some important fields
    name = fields.Char(tracking=True)
    struct_id = fields.Many2one(tracking=True)
    code = fields.Char(tracking=True)
    sequence = fields.Integer(tracking=True)
    quantity = fields.Char(tracking=True)
    category_id = fields.Many2one(tracking=True)
    appears_on_payslip = fields.Boolean(tracking=True)
    register_id = fields.Many2one(tracking=True)

    # Add rule specific fields
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression')
    ], string="Condition Based on", default='none', required=True, tracking=True)
    condition_range = fields.Char(string='Range Based on', default='contract.wage', tracking=True,
        help='This will be used to compute the % fields values; in general it is on basic, '
             'but you can also use categories code fields in lowercase as a variable names '
             '(hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text(string='Python Condition', required=True, tracking=True,
        default=_default_python_help,
        help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.')
    condition_range_min = fields.Float(string='Minimum Range', tracking=True,
                                       help="The minimum amount, applied for this rule.")
    condition_range_max = fields.Float(string='Maximum Range', tracking=True,
                                       help="The maximum amount, applied for this rule.")
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', index=True, required=True, default='fix', tracking=True,
        help="The computation method for the rule amount.")
    amount_fix = fields.Float(string='Fixed Amount', digits='Payroll', tracking=True)
    amount_percentage = fields.Float(string='Percentage (%)', digits='Payroll Rate', tracking=True,
        help='For example, enter 50.0 to apply a percentage of 50%')
    amount_python_compute = fields.Text(string='Python Code', tracking=True,
        default=_default_python_help)
    amount_percentage_base = fields.Char(string='Percentage based on', help='result will be affected to a variable', tracking=True)

    payslip_line_ids = fields.One2many('hr.payslip.line', 'salary_rule_id', string='Payslip Lines',
                                       help="The payslip lines that use this salary rule.")
    input_salary = fields.Boolean(string='Input Salary?',
        help="If marked, this salary rule can be manually configured in the Other Input Salary section of the payslip.")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_payslip_line_ids(self):
        for r in self.filtered(lambda rule: rule.payslip_line_ids):
            raise UserError(_("Could not delete salary rule '%s' while it is still referred by the payslip line '%s' of the payslip '%s'."
                                  " Please open that payslip and remove the line accordingly. Or simply delete the payslip.")
                                  % (r.display_name, r.payslip_line_ids[0].display_name, r.payslip_line_ids[0].slip_id.display_name))

    def _recursive_search_of_rules(self):
        """
        @return: returns a list of tuple (id, sequence)
        """
        return [(rule.id, rule.sequence) for rule in self]

    @api.model
    def _get_fields_to_reset(self):
        return {
            'condition_select': 'none',
            'condition_python': self._default_python_help(),
            'amount_select': 'fix',
            'appears_on_payslip': True,
            'amount_python_compute': self._default_python_help(),
            }

    def _reset(self):
        """
        This method resets the rules in self to the default installation values.
        This also return custom rules in self which should not have default instance values
        :return: custom rules in self which should not have default instance values
        :rtype: hr.salary.rule
        """
        custom_rules = self.env['hr.salary.rule']
        for struct in self.struct_id:
            default_salary_rules_vals_list = struct.company_id._parepare_salary_rules_vals_list(struct)
            for rule in self.filtered(lambda r: r.struct_id == struct):
                match = False
                for vals_dict in default_salary_rules_vals_list:
                    if vals_dict.get('code') == rule.code and vals_dict.get('category_id') == rule.category_id.id and vals_dict.get('company_id') == rule.company_id.id:
                        match = vals_dict
                        break
                # no match found, add the rule to custom_rules recordset for return later
                if not match:
                    custom_rules |= rule
                    continue

                update_vals = {}
                for field, default_val in self._get_fields_to_reset().items():
                    new_val = match.get(field, default_val)
                    if isinstance(getattr(rule, field), models.BaseModel):
                        new_val = getattr(rule, field).browse(new_val)
                    if getattr(rule, field) != new_val:
                        update_vals[field] = new_val
                if bool(update_vals):
                    rule.write(update_vals)
        return custom_rules

    def action_reset(self):
        """
        This method resets the rules in self to the default installation values
        """
        self._reset()

    def _prepare_payslip_line_data(self, localdict, rules_dict=None):
        if rules_dict is None:
            rules_dict = {}
        self.ensure_one()
        self._check_register_partner()
        # compute the amount of the rule
        amount, qty, rate = self._compute_rule(localdict)
        # check if there is already a rule computed with that code
        previous_amount = self.code in localdict and localdict[self.code] or 0.0
        # set/overwrite the amount computed for this rule in the localdict
        tot_rule = amount * qty * rate / 100.0
        localdict[self.code] = tot_rule
        rules_dict[self.code] = self
        # sum the amount for its salary category
        localdict = self.category_id._sum_salary_rule(localdict, tot_rule - previous_amount)
        # create/overwrite the rule in the temporary results
        return {
            'salary_rule_id': self.id,
            'name': self.name,
            'code': self.code,
            'category_id': self.category_id.id,
            'sequence': self.sequence,
            'appears_on_payslip': self.appears_on_payslip,
            'register_id': self.register_id.id,
            'amount': amount,
            'employee_id': localdict['employee'].id,
            'quantity': qty,
            'rate': rate,
        }

    # TODO should add some checks on the type of result (should be float)
    def _compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the environement in which to compute the rule. It may look like
            {
                'datetime': <module 'datetime' from '/usr/lib/python3.6/datetime.py'>,
                'dateutil': <module 'dateutil' from '/usr/local/lib/python3.6/dist-packages/dateutil/__init__.py'>,
                'fields': <module 'odoo.fields' from '/path/to//odoo_root/odoo/fields.py'>,
                'categories': <odoo.addons.to_hr_payroll.models.browsable_object.BrowsableObject object at 0x7fdf8bee4048>,
                'rules': <odoo.addons.to_hr_payroll.models.browsable_object.BrowsableObject object at 0x7fdf8bee4240>,
                'payslip': <odoo.addons.to_hr_payroll.models.browsable_object.Payslips object at 0x7fdf8bee46a0>,
                'advantages': <odoo.addons.to_hr_payroll.models.browsable_object.Advantages object at 0x7fdf8bef8940>,
                'inputs': <odoo.addons.to_hr_payroll.models.browsable_object.InputLine object at 0x7fdf8bee4518>,
                'contributions': <odoo.addons.to_hr_payroll.models.browsable_object.PayslipContributionLine object at 0x7fdf8bef8438>,
                'employee': hr.employee(10,),
                'contracts': hr.contract(8,),
                'result': None,
                'result_qty': 1.0,
                'result_rate': 100
                }
        :return: returns a tuple build as the base/amount computed, the quantity and the rate
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix, float(safe_eval(self.quantity, localdict)), 100.0
            except Exception:
                raise UserError(_('Wrong quantity defined for salary rule %s (%s) of the structure %s.') % (self.name, self.code, self.struct_id.name))
        elif self.amount_select == 'percentage':
            try:
                if 'payslip' in localdict:
                    result = localdict['payslip'].currency_id.round(safe_eval(self.amount_percentage_base, localdict))
                else:
                    result = float(safe_eval(self.amount_percentage_base, localdict))
                return (result,
                        float(safe_eval(self.quantity, localdict)),
                        self.amount_percentage)
            except Exception:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s) of the structure %s.') % (self.name, self.code, self.struct_id.name))
        else:
            try:
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                result = localdict['payslip'].currency_id.round(localdict['result']) if 'payslip' in localdict else float(localdict['result'])
                return result, 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except Exception as e:
                msg = _('Wrong python code defined for salary rule %s (%s) of the structure %s.') % (self.name, self.code, self.struct_id.name)
                if self.env.user.has_group('base.group_no_one'):
                    msg = "%s Here is details:\n%s" % (msg, str(e))
                raise UserError(msg)

    def _prepare_payslip_lines_data(self, localdict, rules_dict=None):
        """
        @param localdict: dictionary containing the environement in which to compute the rule
            {
                'datetime': <module 'datetime' from '/usr/lib/python3.6/datetime.py'>,
                'dateutil': <module 'dateutil' from '/usr/local/lib/python3.6/dist-packages/dateutil/__init__.py'>,
                'fields': <module 'odoo.fields' from '/path/to//odoo_root/odoo/fields.py'>,
                'categories': <odoo.addons.to_hr_payroll.models.browsable_object.BrowsableObject object at 0x7fdf8bee4048>,
                'rules': <odoo.addons.to_hr_payroll.models.browsable_object.BrowsableObject object at 0x7fdf8bee4240>,
                'payslip': <odoo.addons.to_hr_payroll.models.browsable_object.Payslips object at 0x7fdf8bee46a0>,
                'advantages': <odoo.addons.to_hr_payroll.models.browsable_object.Advantages object at 0x7fdf8bef8940>,
                'inputs': <odoo.addons.to_hr_payroll.models.browsable_object.InputLine object at 0x7fdf8bee4518>,
                'contributions': <odoo.addons.to_hr_payroll.models.browsable_object.PayslipContributionLine object at 0x7fdf8bef8438>,
                'employee': hr.employee(10,),
                }
        @param rules_dict:
        @return: list of data dict to create payslip lines
        """
        if rules_dict is None:
            rules_dict = {}
        # IMPORTANT: we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        for rule in self:
            key = "%s-%s" % (rule.code, str(rule.id))
            localdict['result'] = None
            localdict['result_qty'] = 1.0
            localdict['result_rate'] = 100
            # check if the rule can be applied
            if rule._satisfy_condition(localdict):
                # create/overwrite the rule in the temporary results
                result_dict[key] = rule._prepare_payslip_line_data(localdict, rules_dict)
        return list(result_dict.values())

    def _satisfy_condition(self, localdict):
        """
        :param localdict: dictionary containing the environement in which to compute the rule. It may look like
            {
                'datetime': <module 'datetime' from '/usr/lib/python3.6/datetime.py'>,
                'dateutil': <module 'dateutil' from '/usr/local/lib/python3.6/dist-packages/dateutil/__init__.py'>,
                'fields': <module 'odoo.fields' from '/path/to//odoo_root/odoo/fields.py'>,
                'categories': <odoo.addons.to_hr_payroll.models.browsable_object.BrowsableObject object at 0x7fdf8bee4048>,
                'rules': <odoo.addons.to_hr_payroll.models.browsable_object.BrowsableObject object at 0x7fdf8bee4240>,
                'payslip': <odoo.addons.to_hr_payroll.models.browsable_object.Payslips object at 0x7fdf8bee46a0>,
                'advantages': <odoo.addons.to_hr_payroll.models.browsable_object.Advantages object at 0x7fdf8bef8940>,
                'inputs': <odoo.addons.to_hr_payroll.models.browsable_object.InputLine object at 0x7fdf8bee4518>,
                'contributions': <odoo.addons.to_hr_payroll.models.browsable_object.PayslipContributionLine object at 0x7fdf8bef8438>,
                'employee': hr.employee(10,),
                'contracts': hr.contract(8,),
                'result': None,
                'result_qty': 1.0,
                'result_rate': 100
                }
        :return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """
        self.ensure_one()
        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result and result <= self.condition_range_max or False
            except Exception:
                raise UserError(_('Wrong range condition defined for salary rule %s (%s) of the structure %s.') % (self.name, self.code, self.struct_id.name))
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except Exception:
                raise UserError(_('Wrong python condition defined for salary rule %s (%s) of the structure %s.') % (self.name, self.code, self.struct_id.name))
