# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

import logging
from datetime import timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

def days_between(start, end):
    if start and end:
        start = fields.Date.to_date(start)
        end = fields.Date.to_date(end)
        if start and end:
            return (end - start).days + 1
    return 0

def days_onleave(employee, payslip, *leavetype):
    holiday_status_ids = employee.env['hr.leave.type'].browse()
    for lt in leavetype:
        if isinstance(lt, int):
            holiday_status_ids += employee.env['hr.leave.type'].search([('id','=', lt)])
        else:
            holiday_status_ids += employee.env['hr.leave.type'].search([('name','=ilike', lt)])
    current = fields.Date.from_string(payslip.date_from)
    end = fields.Date.from_string(payslip.date_to)
    days = 0
    if current and end:
        while current <= end:
            dt = current
            if employee.env['hr.leave'].sudo().search([('employee_id','=', employee.id), 
                                                ('holiday_status_id','in', holiday_status_ids.ids), 
                                                ('state','=', 'validate'),
                                                ('date_from','<=', dt),
                                                ('date_to','>=', dt),
                                                ], count = True):
                days +=1
            current += timedelta(days=1)
    return days


class HrSalaryRule(models.Model):
    _name ='hr.salary.rule'
    _order = 'sequence, id'
    _description = 'Salary Rule'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True,
        help="The code of salary rules can be used as reference in computation of other rules. "
             "In that case, it is case sensitive.")
    sequence = fields.Integer(required=True, index=True, default=5,
        help='Use to arrange calculation sequence')
    quantity = fields.Char(default='1.0',
        help="It is used in computation for percentage and fixed amount. "
             "For e.g. A rule for Meal Voucher having fixed amount of "
             u"1€ per worked day can have its quantity defined in expression "
             "like worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    active = fields.Boolean(default=True,
        help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    appears_on_payslip = fields.Boolean(string='Appears on Payslip', default=True,
        help="Used to display the salary rule on payslip.")
    parent_rule_id = fields.Many2one('hr.salary.rule', string='Parent Salary Rule', index=True)
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression')
    ], string="Condition Based on", default='none', required=True)
    condition_range = fields.Char(string='Range Based on', default='contract.wage',
        help='This will be used to compute the % fields values; in general it is on basic, '
             'but you can also use categories code fields in lowercase as a variable names '
             '(hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text(string='Python Condition', required=True,
        default='''
                    # Available variables:
                    #----------------------
                    # payslip: object containing the payslips
                    # employee: hr.employee object
                    # contract: hr.contract object
                    # rules: object containing the rules code (previously computed)
                    # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                    # worked_days: object containing the computed worked days
                    # inputs: object containing the computed inputs

                    # Note: returned value have to be set in the variable 'result'

                    result = rules.NET > categories.NET * 0.10''',
        help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.')
    condition_range_min = fields.Float(string='Minimum Range', help="The minimum amount, applied for this rule.")
    condition_range_max = fields.Float(string='Maximum Range', help="The maximum amount, applied for this rule.")
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', index=True, required=True, default='fix', help="The computation method for the rule amount.")
    amount_fix = fields.Float(string='Fixed Amount', digits='Payroll')
    amount_percentage = fields.Float(string='Percentage (%)', digits='Payroll Rate',
        help='For example, enter 50.0 to apply a percentage of 50%')
    amount_python_compute = fields.Text(string='Python Code',
        default='''
                    # Available variables:
                    #----------------------
                    # payslip: object containing the payslips
                    # employee: hr.employee object
                    # contract: hr.contract object
                    # rules: object containing the rules code (previously computed)
                    # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                    # worked_days: object containing the computed worked days.
                    # inputs: object containing the computed inputs.

                    # Note: returned value have to be set in the variable 'result'

                    result = contract.wage * 0.10''')
    amount_percentage_base = fields.Char(string='Percentage based on', help='result will be affected to a variable')
    child_ids = fields.One2many('hr.salary.rule', 'parent_rule_id', string='Child Salary Rule', copy=True)
    register_id = fields.Many2one('hr.contribution.register', string='Contribution Register',
        help="Eventual third party involved in the salary payment of the employees.")
    input_ids = fields.One2many('hr.rule.input', 'input_id', string='Inputs', copy=True)
    note = fields.Text(string='Description')

    struct_ids = fields.Many2many('hr.payroll.structure', 'hr_structure_salary_rule_rel', 'rule_id', 'struct_id', string='Salary Structures')
    exceptional = fields.Boolean()

    @api.constrains('parent_rule_id')
    def _check_parent_rule_id(self):
        if not self._check_recursion(parent='parent_rule_id'):
            raise ValidationError(_('Error! You cannot create recursive hierarchy of Salary Rules.'))

    
    def _recursive_search_of_rules(self):
        """
        @return: returns a list of tuple (id, sequence) which are all the children of the passed rule_ids
        """
        children_rules = []
        for rule in self.filtered(lambda rule: rule.child_ids):
            children_rules += rule.child_ids._recursive_search_of_rules()
        return [(rule.id, rule.sequence) for rule in self] + children_rules
    
    def _update_localdict(self, localdict):
        def log(message, level="info"):
            with self.pool.cursor() as cr:
                cr.execute("""
                    INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func)
                    VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (self.env.uid, 'server', self._cr.dbname, __name__, level, message, "salary-rule", self.id, self.code))
        
        localdict.update({
            'days_between' : days_between,
            'days_onleave' : lambda *leavetype: days_onleave(localdict['employee'], localdict['payslip'], *leavetype),
            'time': tools.safe_eval.time,
            'datetime': tools.safe_eval.datetime,
            'dateutil': tools.safe_eval.dateutil,
            'relativedelta' : relativedelta,
            '_logger' : _logger,
            'log' : log,
            'env' : self.env
            })    

    #TODO should add some checks on the type of result (should be float)
    def _compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the environement in which to compute the rule
        :return: returns a tuple build as the base/amount computed, the quantity and the rate
        :rtype: (float, float, float)
        """
        self.ensure_one()
        self._update_localdict(localdict)
        if self.amount_select == 'fix':
            try:
                return self.amount_fix, float(safe_eval(self.quantity, localdict)), 100.0
            except Exception as e:
                _logger.exception(e)
                msg = _('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code)
                exception = getattr(e,'name', str(e) )
                employee = 'employee' in localdict and 'Employee: ' + localdict['employee'].name or ''
                msg = '%s\n\n%s\n\n%s' % (msg, employee, exception)
                raise UserError(msg)
        elif self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)),
                        self.amount_percentage)
            except Exception as e:
                _logger.exception(e)
                msg = _('Wrong percentage base or quantity defined for salary rule %s (%s).') % (self.name, self.code)
                exception = getattr(e,'name', str(e) )
                employee = 'employee' in localdict and 'Employee: ' + localdict['employee'].name or ''
                msg = '%s\n\n%s\n\n%s' % (msg, employee, exception)
                raise UserError(msg)
        else:
            try:
                localdict.pop('result_description', False)
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                if localdict.get('result_description'):
                    self.env['hr.payslip.line.description'].create({
                        'payslip_id' : localdict['payslip'].id,
                        'code' : self.code,
                        'description' : localdict['result_description']
                        })
                return float(localdict['result']), float(localdict.get('result_qty', 1.0)), float(localdict.get('result_rate',100.0))
            except Exception as e:
                _logger.exception(e)
                msg = _('Wrong python code defined for salary rule %s (%s).') % (self.name, self.code)
                exception = getattr(e,'name', str(e) )
                employee = 'employee' in localdict and 'Employee: ' + localdict['employee'].name or ''
                msg = '%s\n\n%s\n\n%s' % (msg, employee, exception)
                raise UserError(msg)

    def _satisfy_condition(self, localdict):
        """
        @param contract_id: id of hr.contract to be tested
        @return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """
        self.ensure_one()
        self._update_localdict(localdict)
        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result and result <= self.condition_range_max or False
            except Exception as e:
                _logger.exception(e)
                msg = _('Wrong range condition defined for salary rule %s (%s).') % (self.name, self.code)
                exception = getattr(e,'name', str(e) )
                employee = 'employee' in localdict and 'Employee: ' + localdict['employee'].name or ''
                msg = '%s\n\n%s\n\n%s' % (msg, employee, exception)
                raise UserError(msg)
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except Exception as e:
                _logger.exception(e)
                msg = _('Wrong python condition defined for salary rule %s (%s).') % (self.name, self.code)
                exception = getattr(e,'name', str(e) )
                employee = 'employee' in localdict and 'Employee: ' + localdict['employee'].name or ''
                msg = '%s\n\n%s\n\n%s' % (msg, employee, exception)
                raise UserError(msg)
