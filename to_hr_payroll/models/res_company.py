from odoo import fields, models, api, _
from odoo.tools import relativedelta
from odoo.addons.base.models.res_partner import _lang_get

RULES_CATEG_MAP = {
    'basic_wage_rule_categ_id': 'BASIC',
    'gross_salary_rule_categ_id': 'GROSS',
    'tax_base_rule_categ_id': 'TAXBASE',
    'net_income_salary_rule_categ_id': 'NET'
    }


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _default_salary_cycle(self):
        return self.env.ref('to_hr_payroll.hr_salary_cycle_default', raise_if_not_found=False)

    basic_wage_rule_categ_id = fields.Many2one('hr.salary.rule.category', string='Basic Wage Rule Category', ondelete='set null',
                                         help="The salary rule category that represents employee's basic wage")
    gross_salary_rule_categ_id = fields.Many2one('hr.salary.rule.category', string='Gross Salary Rule Category', ondelete='set null',
                                         help="The salary rule category that represents employee's gross salary")
    tax_base_rule_categ_id = fields.Many2one('hr.salary.rule.category', string='Personal Tax Base Rule Category', ondelete='set null',
                                         help="The salary rule category that represents the personal tax base for personal tax computation")
    net_income_salary_rule_categ_id = fields.Many2one('hr.salary.rule.category', string='Net Salary Rule Category', ondelete='set null',
                                                help="The salary rule category that computes employee net income (after tax and deduction)")
    payslips_auto_generation = fields.Boolean(string='Payslips Auto-Generation',
                                             help="If enabled, payslips will be generated automatically base on their corresponding contracts settings.")

    payslips_auto_generation_mode = fields.Selection([
        ('batch_period', 'Payslip Batch Period'),
        ('contract_period', 'Contract Validity')], string='Payslip Generation Mode', required=True, default='contract_period',
        help="* Payslip Batch Period: all the generated payslips will have the same period as the batch's;\n"
        "* Contract Validity: generated paysplips will have their period constrained by their corresponding contracts")

    payslips_auto_generation_day = fields.Integer(string='Generation Day', default=1, required=True,
                                                  help="The day of the period specified in the Payslips Auto-Generation Period,"
                                                  " on which the payslips will be generated.")
    payslips_auto_generation_lang = fields.Selection(_lang_get, string='Language', default=lambda self: self.env.lang,
                            help="During payslip generation, the language selected here will be used."
                            " If none is specified, the language of the execution user will be used (usually the Bot user).")

    salary_cycle_id = fields.Many2one('hr.salary.cycle', string='Salary Cycle', default=_default_salary_cycle)

    _sql_constraints = [
        ('check_payslips_auto_generation_day',
         "CHECK(payslips_auto_generation_day >= 1)",
         "Generation Day must be greater than or equal to 1"),
    ]

    def _get_job_positions(self):
        """
        Get all existing job positions of the current companies, incl. inactive job position.
        Job positions without a company specified will not be considered here
        """
        return self.env['hr.job'].sudo().with_context(active_test=False).search([('company_id', 'in', self.ids)])

    def _prepare_contribution_register_data(self):
        wage_categ = self.env.ref('to_hr_payroll.hr_contribution_register_wage_allowance')
        insurance_categ = self.env.ref('to_hr_payroll.hr_contribution_category_insurance')
        labor_union_categ = self.env.ref('to_hr_payroll.hr_contribution_category_labor_union')
        return [
            # Wage & Allowances
            {'name': _('Employees'), 'partner_id': False, 'category_id': wage_categ.id, 'company_id': self.id},
            {'name': _('Travel Allowance'), 'partner_id': False, 'category_id': wage_categ.id, 'company_id': self.id},
            {'name': _('Phone Allowance'), 'partner_id': False, 'category_id': wage_categ.id, 'company_id': self.id},
            {'name': _('Meal Allowance'), 'partner_id': False, 'category_id': wage_categ.id, 'company_id': self.id},
            {'name': _('Harmful Subsidies'), 'partner_id': False, 'category_id': wage_categ.id, 'company_id': self.id},
            {'name': _('Responsibility Allowance'), 'partner_id': False, 'category_id': wage_categ.id, 'company_id': self.id},
            {'name': _('Hard Working Award'), 'partner_id': False, 'category_id': wage_categ.id, 'company_id': self.id},
            {'name': _('Performance Award'), 'partner_id': False, 'category_id': wage_categ.id, 'company_id': self.id},
            # Insurances
            {'name': _('Social Insurance'), 'partner_id': False, 'category_id': insurance_categ.id, 'company_id': self.id},
            {'name': _('Health Insurance'), 'partner_id': False, 'category_id': insurance_categ.id, 'company_id': self.id},
            {'name': _('Unemployment Insurance'), 'partner_id': False, 'category_id': insurance_categ.id, 'company_id': self.id},
            # Labor Union
            {'name': _('Labor Union'), 'partner_id': False, 'category_id': labor_union_categ.id, 'company_id': self.id},
            ]

    def _generate_contribution_register(self):
        register_obj = self.env['hr.contribution.register'].sudo()
        existing_registers = register_obj.search([])
        vals_list = []
        for r in self:
            data_list = r._prepare_contribution_register_data()
            # generate if not exists
            for vals in data_list:
                if not existing_registers.filtered(lambda reg: reg.company_id == r and reg.name == vals['name']):
                    vals_list.append(vals)
        # use sudo to pass the multi-company rule during new company creation
        # when the user has not been assigned with new company access right yet
        register_obj.sudo().create(vals_list)

    def _get_contribution_register(self, name):
        self.ensure_one()
        # use sudo to pass the multi-company rule during new company creation
        # when the user has not been assigned with new company access right yet
        return self.env['hr.contribution.register'].sudo().search([
            ('name', '=', name), ('company_id', '=', self.id)], limit=1)

    def _prepare_payrol_contribution_types_data(self):
        return [
            {
                'name': _("Social Insurance"),
                'code': 'SOCIAL_INSURANCE',
                'employee_contrib_reg_id': self._get_contribution_register(_("Social Insurance")).id,
                'employee_contrib_rate': 0.0,
                'company_contrib_reg_id': self._get_contribution_register(_("Social Insurance")).id,
                'company_contrib_rate': 0.0,
                'company_id': self.id,
                },
            {
                'name': _("Health Insurance"),
                'code': 'HEALTH_INSURANCE',
                'employee_contrib_reg_id': self._get_contribution_register(_("Health Insurance")).id,
                'employee_contrib_rate': 0.0,
                'company_contrib_reg_id': self._get_contribution_register(_("Health Insurance")).id,
                'company_contrib_rate': 0.0,
                'company_id': self.id,
                },
            {
                'name': _("Unemployment Insurance"),
                'code': 'UNEMPLOYMENT_UNSURANCE',
                'employee_contrib_reg_id': self._get_contribution_register(_("Unemployment Insurance")).id,
                'employee_contrib_rate': 0.0,
                'company_contrib_reg_id': self._get_contribution_register(_("Unemployment Insurance")).id,
                'company_contrib_rate': 0.0,
                'company_id': self.id,
                },
            {
                'name': _("Labor Union"),
                'code': 'LABOR_UNION',
                'employee_contrib_reg_id': self._get_contribution_register(_("Labor Union")).id,
                'employee_contrib_rate': 0.0,
                'company_contrib_reg_id': self._get_contribution_register(_("Labor Union")).id,
                'company_contrib_rate': 0.0,
                'company_id': self.id,
                },
            ]

    def _generate_payrol_contribution_types(self):
        # use sudo to pass the multi-company rule during new company creation
        # when the user has not been assigned with new company access right yet
        contribution_type_obj = self.env['hr.payroll.contribution.type'].sudo()
        existing_types = contribution_type_obj.search([])
        vals_list = []
        for r in self:
            data_list = r._prepare_payrol_contribution_types_data()
            # generate if not exists
            for vals in data_list:
                if not existing_types.filtered(lambda reg: reg.company_id == r and reg.code == vals['code']):
                    vals_list.append(vals)
        if vals_list:
            # use sudo to pass the multi-company rule during new company creation
            # when the user has not been assigned with new company access right yet
            contribution_type_obj.create(vals_list)

    def _prepare_hr_advantage_templates(self):
        return [
            {'name': _('Travel Allowance'), 'code': 'TRAVEL', 'amount': 0.0, 'lower_bound': 0.0, 'upper_bound': 0.0, 'company_id': self.id},
            {'name': _('Phone Allowance'), 'code': 'PHONE', 'amount': 0.0, 'lower_bound': 0.0, 'upper_bound': 0.0, 'company_id': self.id},
            {'name': _('Meal Allowance'), 'code': 'MEAL', 'amount': 0.0, 'lower_bound': 0.0, 'upper_bound': 0.0, 'company_id': self.id},
            {'name': _('Responsibility Allowance'), 'code': 'RESPONSIBILITY', 'amount': 0.0, 'lower_bound': 0.0, 'upper_bound': 0.0, 'company_id': self.id},
            {'name': _('Hard Working Award'), 'code': 'HARDWORK', 'amount': 0.0, 'lower_bound': 0.0, 'upper_bound': 0.0, 'company_id': self.id},
            {'name': _('Performance Award'), 'code': 'PERFORMANCE', 'amount': 0.0, 'lower_bound': 0.0, 'upper_bound': 0.0, 'company_id': self.id},
            {'name': _('Harmful Subsidies'), 'code': 'HARMFUL', 'amount': 0.0, 'lower_bound': 0.0, 'upper_bound': 0.0, 'company_id': self.id},
            ]

    def _generate_hr_advantage_templates(self):
        # use sudo to pass the multi-company rule during new company creation
        # when the user has not been assigned with new company access right yet
        adv_template_obj = self.env['hr.advantage.template'].sudo()
        existing_templates = adv_template_obj.search([])
        for r in self:
            vals_list = []
            data_list = r._prepare_hr_advantage_templates()
            # generate if not exists
            for vals in data_list:
                if not existing_templates.filtered(lambda reg: reg.company_id == r and reg.code == vals['code']):
                    vals_list.append(vals)

            advatage_templates = adv_template_obj.create(vals_list)
            advatage_templates._generate_job_position_advantages()

    def _prepare_salary_rule_categories_data(self):
        return [
            {'name': _('Basic'), 'code': 'BASIC', 'company_id': self.id, 'paid_by_company': True},
            {'name': _('Allowance'), 'code': 'ALW', 'company_id': self.id, 'paid_by_company': True, 'children_ids': [
                (0, 0, {'name': _('Travel Allowance'), 'code': 'TRAVEL', 'company_id': self.id, 'paid_by_company': True}),
                (0, 0, {'name': _('Phone Allowance'), 'code': 'PHONE', 'company_id': self.id, 'paid_by_company': True}),
                (0, 0, {'name': _('Meal Allowance'), 'code': 'MEAL', 'company_id': self.id, 'paid_by_company': True}),
                (0, 0, {'name': _('Responsibility Allowance'), 'code': 'RESPONSIBILITY', 'company_id': self.id, 'paid_by_company': True}),
                (0, 0, {'name': _('Hard Working Award'), 'code': 'HARDWORK', 'company_id': self.id, 'paid_by_company': True}),
                (0, 0, {'name': _('Performance Award'), 'code': 'PERFORMANCE', 'company_id': self.id, 'paid_by_company': True}),
                ]},
            {'name': _('Gross'), 'code': 'GROSS', 'company_id': self.id},
            {'name': _('Deduction (before taxes)'), 'code': 'DED_BEFORE_TAX', 'company_id': self.id, 'children_ids': [
                (0, 0, {'name': _('Employee Insurance (by employee)'), 'code': 'E_INSURANCE', 'company_id': self.id}),
                ]},
            {'name': _('Personal Income Tax Base'), 'code': 'TAXBASE', 'company_id': self.id},
            {'name': _('Personal Income Tax'), 'code': 'PTAX', 'company_id': self.id},
            {'name': _('Deduction (after taxes)'), 'code': 'DED_AFTER_TAX', 'company_id': self.id, 'children_ids': [
                (0, 0, {'name': _('Labor Union (by employee)'), 'code': 'E_LU', 'company_id': self.id}),
                ]},
            {'name': _('Net'), 'code': 'NET', 'company_id': self.id},
            {'name': _('Company Contribution'), 'code': 'COMP', 'company_id': self.id, 'paid_by_company': True, 'children_ids': [
                (0, 0, {'name': _('Employee Insurance (by company)'), 'code': 'C_INSURANCE', 'company_id': self.id, 'paid_by_company': True}),
                (0, 0, {'name': _('Labor Union (by company)'), 'code': 'C_LU', 'company_id': self.id, 'paid_by_company': True}),
                ]},
            {'name': _('Allowance (tax exemption)'), 'code': 'ALWNOTAX', 'company_id': self.id, 'paid_by_company': True, 'children_ids': [
                (0, 0, {'name': _('Harmful Subsidies'), 'code': 'HARMFUL', 'company_id': self.id, 'paid_by_company': True}),
                ]},
            {'name': _('Miscellaneous (e.g. based for other calculations)'), 'code': 'MISC', 'company_id': self.id},
            ]

    def _generate_salary_rule_categories(self):
        """
        This method generates salary rules categories if not exist
        """
        # use sudo to pass the multi-company rule during new company creation
        # when the user has not been assigned with new company access right yet
        categ_obj = self.env['hr.salary.rule.category'].sudo()
        existing_categs = categ_obj.search([])
        for r in self:
            vals_list = []
            for vals in r._prepare_salary_rule_categories_data():
                exist = existing_categs.filtered(lambda categ: categ.company_id == r and categ.code == vals['code'])
                # generate salary rules category if not exists
                if not exist:
                    vals_list.append(vals)
                else:
                    for child in vals.get('children_ids', []):
                        child_vals = child[2]
                        child_exist = existing_categs.filtered(lambda categ: categ.company_id == r and categ.code == child_vals['code'])
                        if not child_exist:
                            child_vals['parent_id'] = exist.id
                            vals_list.append(child_vals)
            categ_obj.create(vals_list)
        self._update_salary_rule_categ_settings()

    def _update_salary_rule_categ_settings(self):
        categ_obj = self.env['hr.salary.rule.category'].sudo()
        for r in self:
            udpate_vals = {}
            for field, code in RULES_CATEG_MAP.items():
                udpate_vals[field] = categ_obj.search([
                    ('company_id', '=', r.id),
                    ('code', '=', code)], limit=1).id
            r.write(udpate_vals)

    def _get_salary_rule_categ(self, code):
        self.ensure_one()
        # use sudo to pass the multi-company rule during new company creation
        # when the user has not been assigned with new company access right yet
        return self.env['hr.salary.rule.category'].sudo().search([
            ('code', '=', code), ('company_id', '=', self.id)], limit=1)

    def _parepare_salary_rules_vals_list(self, struct):
        self.ensure_one()
        vals_list = [
            {
                'name': _('Basic Salary'),
                'struct_id': struct.id,
                'sequence': 1,
                'code': 'BASIC',
                'category_id': self._get_salary_rule_categ('BASIC').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """
wage = 0.0
if payslip.thirteen_month_pay:
    wage = payslip.get_average_amount_in_year('BASIC')
else:
    # Loop over the payslip's Working Days that link to contract for wage calculation
    for line in worked_days_paid_lines:
        wage += line.contract_id.wage * line.paid_rate
result = wage
""",
                'company_id': self.id
                },
            {
                'name': _('Travel Allowance'),
                'struct_id': struct.id,
                'sequence': 530,
                'code': 'TRAVEL',
                'category_id': self._get_salary_rule_categ('TRAVEL').id,
                'condition_select': 'python',
                'condition_python': "result = advantages.TRAVEL and advantages.TRAVEL.amount > 0",
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': """
alw = 0.0
if payslip.thirteen_month_pay:
    alw = payslip.get_average_amount_in_year('TRAVEL')
else:
    # Loop over the payslip's Worked Days that link to contract for allowance
    for line in worked_days_paid_lines:
        alw += line.contract_id.get_advatage_amount_by_code('TRAVEL') * line.paid_rate
result = alw
""",
                'company_id': self.id
                },
            {
                'name': _('Phone Allowance'),
                'struct_id': struct.id,
                'sequence': 540,
                'code': 'PHONE',
                'category_id': self._get_salary_rule_categ('PHONE').id,
                'condition_select': 'python',
                'condition_python': "result = advantages.PHONE and advantages.PHONE.amount > 0",
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': """
alw = 0.0
if payslip.thirteen_month_pay:
    alw = payslip.get_average_amount_in_year('PHONE')
else:
    # Loop over the payslip's Worked Days that link to contract for allowance
    for line in worked_days_paid_lines:
        alw += line.contract_id.get_advatage_amount_by_code('PHONE') * line.paid_rate
result = alw
""",
                'company_id': self.id
                },
            {
                'name': _('Meal Allowance'),
                'struct_id': struct.id,
                'sequence': 550,
                'code': 'MEAL',
                'category_id': self._get_salary_rule_categ('MEAL').id,
                'condition_select': 'python',
                'condition_python': "result = advantages.MEAL and advantages.MEAL.amount > 0",
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': """
alw = 0.0
if payslip.thirteen_month_pay:
    alw = payslip.get_average_amount_in_year('MEAL')
else:
    # Loop over the payslip's Worked Days that link to contract for allowance
    for line in worked_days_paid_lines:
        alw += line.contract_id.get_advatage_amount_by_code('MEAL') * line.paid_rate
result = alw
""",
                'company_id': self.id
                },
            {
                'name': _('Responsibility Allowance'),
                'struct_id': struct.id,
                'sequence': 560,
                'code': 'RESPONSIBILITY',
                'category_id': self._get_salary_rule_categ('RESPONSIBILITY').id,
                'condition_select': 'python',
                'condition_python': "result = advantages.RESPONSIBILITY and advantages.RESPONSIBILITY.amount > 0",
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': """
alw = 0.0
if payslip.thirteen_month_pay:
    alw = payslip.get_average_amount_in_year('RESPONSIBILITY')
else:
    # Loop over the payslip's Worked Days that link to contract for allowance
    for line in worked_days_paid_lines:
        alw += line.contract_id.get_advatage_amount_by_code('RESPONSIBILITY') * line.paid_rate
result = alw
""",
                'company_id': self.id
                },
            {
                'name': _('Hard Working Award'),
                'struct_id': struct.id,
                'sequence': 570,
                'code': 'HARDWORK',
                'category_id': self._get_salary_rule_categ('HARDWORK').id,
                'condition_select': 'python',
                'condition_python': "result = advantages.HARDWORK and advantages.HARDWORK.amount > 0",
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': """
alw = 0.0
if payslip.thirteen_month_pay:
    alw = payslip.get_average_amount_in_year('HARDWORK')
else:
    # Loop over the payslip's Worked Days that link to contract for allowance
    for line in worked_days_paid_lines:
        alw += line.contract_id.get_advatage_amount_by_code('HARDWORK') * line.paid_rate
result = alw
""",
                'company_id': self.id
                },
            {
                'name': _('Performance Award'),
                'struct_id': struct.id,
                'sequence': 580,
                'code': 'PERFORMANCE',
                'category_id': self._get_salary_rule_categ('PERFORMANCE').id,
                'condition_select': 'python',
                'condition_python': "result = advantages.PERFORMANCE and advantages.PERFORMANCE.amount > 0",
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': """
alw = 0.0
if payslip.thirteen_month_pay:
    alw = payslip.get_average_amount_in_year('PERFORMANCE')
else:
    # Loop over the payslip's Worked Days that link to contract for allowance
    for line in worked_days_paid_lines:
        alw += line.contract_id.get_advatage_amount_by_code('PERFORMANCE') * line.paid_rate
result = alw
""",
                'company_id': self.id
                },

            # GROSS
            {
                'name': _('Gross'),
                'struct_id': struct.id,
                'sequence': 1000,
                'code': 'GROSS',
                'category_id': self._get_salary_rule_categ('GROSS').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': 'result = categories.BASIC + categories.ALW',
                'company_id': self.id
                },

            # Social insurance
            {
                'name': _('Social Insurance by Employee'),
                'struct_id': struct.id,
                'sequence': 1230,
                'code': 'ESINS',
                'category_id': self._get_salary_rule_categ('E_INSURANCE').id,
                'condition_select': 'python',
                'condition_python': 'result = contributions.SOCIAL_INSURANCE and contributions.SOCIAL_INSURANCE.employee_contribution > 0 and not payslip.thirteen_month_pay',
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': 'result = -1 * contributions.SOCIAL_INSURANCE.employee_contribution',
                'company_id': self.id,
                'register_id': self._get_contribution_register(_("Social Insurance")).id,
                },
            {
                'name': _('Social Insurance by Company'),
                'struct_id': struct.id,
                'sequence': 1231,
                'code': 'CSINS',
                'category_id': self._get_salary_rule_categ('C_INSURANCE').id,
                'condition_select': 'python',
                'condition_python': 'result = contributions.SOCIAL_INSURANCE and contributions.SOCIAL_INSURANCE.company_contribution > 0 and not payslip.thirteen_month_pay',
                'amount_select': 'code',
                'appears_on_payslip': False,
                'amount_python_compute': 'result = contributions.SOCIAL_INSURANCE.company_contribution',
                'company_id': self.id,
                'register_id': self._get_contribution_register(_("Social Insurance")).id,
                },
            # Health insurance
            {
                'name': _('Health Insurance by Employee'),
                'struct_id': struct.id,
                'sequence': 1240,
                'code': 'EHINS',
                'category_id': self._get_salary_rule_categ('E_INSURANCE').id,
                'condition_select': 'python',
                'condition_python': 'result = contributions.HEALTH_INSURANCE and contributions.HEALTH_INSURANCE.employee_contribution > 0 and not payslip.thirteen_month_pay',
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': 'result = -1 * contributions.HEALTH_INSURANCE.employee_contribution',
                'company_id': self.id,
                'register_id': self._get_contribution_register(_("Health Insurance")).id,
                },
            {
                'name': _('Health Insurance by Company'),
                'struct_id': struct.id,
                'sequence': 1241,
                'code': 'CHINS',
                'category_id': self._get_salary_rule_categ('C_INSURANCE').id,
                'condition_select': 'python',
                'condition_python': 'result = contributions.HEALTH_INSURANCE and contributions.HEALTH_INSURANCE.company_contribution > 0 and not payslip.thirteen_month_pay',
                'amount_select': 'code',
                'appears_on_payslip': False,
                'amount_python_compute': 'result = contributions.HEALTH_INSURANCE.company_contribution',
                'company_id': self.id,
                'register_id': self._get_contribution_register(_("Health Insurance")).id,
                },
            # Unemployment insurance
            {
                'name': _('Unemployment Insurance by Employee'),
                'struct_id': struct.id,
                'sequence': 1250,
                'code': 'EUEINS',
                'category_id': self._get_salary_rule_categ('E_INSURANCE').id,
                'condition_select': 'python',
                'condition_python': 'result = contributions.UNEMPLOYMENT_UNSURANCE and contributions.UNEMPLOYMENT_UNSURANCE.employee_contribution > 0 and not payslip.thirteen_month_pay',
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': 'result = -1 * contributions.UNEMPLOYMENT_UNSURANCE.employee_contribution',
                'company_id': self.id,
                'register_id': self._get_contribution_register(_("Unemployment Insurance")).id,
                },
            {
                'name': _('Unemployment Insurance by Company'),
                'struct_id': struct.id,
                'sequence': 1251,
                'code': 'CUEINS',
                'category_id': self._get_salary_rule_categ('C_INSURANCE').id,
                'condition_select': 'python',
                'condition_python': 'result = contributions.UNEMPLOYMENT_UNSURANCE and contributions.UNEMPLOYMENT_UNSURANCE.company_contribution > 0 and not payslip.thirteen_month_pay',
                'amount_select': 'code',
                'appears_on_payslip': False,
                'amount_python_compute': 'result = contributions.UNEMPLOYMENT_UNSURANCE.company_contribution',
                'company_id': self.id,
                'register_id': self._get_contribution_register(_("Unemployment Insurance")).id,
                },
            # Labor Union Fee
            {
                'name': _('Labor Union Fee by Employee'),
                'struct_id': struct.id,
                'sequence': 2000,
                'code': 'ELUF',
                'category_id': self._get_salary_rule_categ('E_LU').id,
                'condition_select': 'python',
                'condition_python': 'result = contributions.LABOR_UNION and contributions.LABOR_UNION.employee_contribution > 0 and not payslip.thirteen_month_pay',
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': 'result = -1 * contributions.LABOR_UNION.employee_contribution',
                'company_id': self.id,
                'register_id': self._get_contribution_register(_("Labor Union")).id,
                },
            {
                'name': _('Labor Union Fee by Company'),
                'struct_id': struct.id,
                'sequence': 2100,
                'code': 'CLUF',
                'category_id': self._get_salary_rule_categ('C_LU').id,
                'condition_select': 'python',
                'condition_python': 'result = contributions.LABOR_UNION and contributions.LABOR_UNION.company_contribution > 0 and not payslip.thirteen_month_pay',
                'amount_select': 'code',
                'appears_on_payslip': False,
                'amount_python_compute': 'result = contributions.LABOR_UNION.company_contribution',
                'company_id': self.id,
                'register_id': self._get_contribution_register(_("Labor Union")).id,
                },
            # TAX
            {
                'name': _('Personal Tax Base Deduction'),
                'struct_id': struct.id,
                'sequence': 3100,
                'code': 'TBDED',
                'category_id': self._get_salary_rule_categ('MISC').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'appears_on_payslip': False,
                'amount_python_compute': 'result = payslip.personal_tax_rule_id.personal_tax_base_ded + payslip.dependent_deduction - categories.DED_BEFORE_TAX',
                'company_id': self.id
                },
            {
                'name': _('Personal Tax Base'),
                'struct_id': struct.id,
                'sequence': 3150,
                'code': 'TAXBASE',
                'category_id': self._get_salary_rule_categ('TAXBASE').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'appears_on_payslip': False,
                'amount_python_compute': """
result=categories.GROSS
if payslip.personal_tax_rule_id.apply_tax_base_deduction:
    result -= TBDED
if result < 0.0:
    result = 0.0
""",
                'company_id': self.id
                },
            {
                'name': _('Personal Income Tax'),
                'struct_id': struct.id,
                'sequence': 3200,
                'code': 'PTAX',
                'category_id': self._get_salary_rule_categ('PTAX').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': """
# DO NOT MODIFY UNLESS YOU KNOW WHAT YOU ARE DOING

# the the base for tax computation from TAXBASE rule
tax_base = TAXBASE

# set the initial value for the tax amount
tax = 0.0

# get the personal income tax rule from payslip
tax_rule = payslip.personal_tax_rule_id

# compute tax amount base on the policy of either Flat Rate or Progressive Tax Table
if tax_rule.personal_tax_policy == 'flat_rate':
    tax += tax_rule.personal_tax_flat_rate * tax_base / 100.0

elif tax_rule.personal_tax_policy == 'escalation':
    for rule in tax_rule.progress_ids.sorted('rate', reverse=True):
        rule_base = rule._get_base(payslip)
        if tax_base > rule_base:
            diff = tax_base - rule.base
            tax += rule.rate * diff / 100.0
            tax_base -= diff
result = -1 * tax
""",
                'company_id': self.id
                },
            # tax exemption allowances
            {
                'name': _('Harmful Subsidies'),
                'struct_id': struct.id,
                'sequence': 4100,
                'code': 'HARMFUL',
                'category_id': self._get_salary_rule_categ('HARMFUL').id,
                'condition_select': 'python',
                'condition_python': "result = advantages.HARMFUL and advantages.HARMFUL.amount > 0",
                'amount_select': 'code',
                'appears_on_payslip': True,
                'amount_python_compute': """
alw = 0.0
if payslip.thirteen_month_pay:
    alw = payslip.get_average_amount_in_year('HARMFUL')
else:
    # Loop over the payslip's Worked Days that link to contract for allowance
    for line in worked_days_paid_lines:
        alw += line.contract_id.get_advatage_amount_by_code('HARMFUL') * line.paid_rate
result = alw
""",
                'company_id': self.id
                },
            # NET
            {
                'name': _('Net Salary'),
                'struct_id': struct.id,
                'sequence': 10000,
                'code': 'NET',
                'category_id': self._get_salary_rule_categ('NET').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = categories.GROSS + categories.ALWNOTAX + categories.DED_BEFORE_TAX + categories.DED_AFTER_TAX + categories.PTAX',
                'register_id': self._get_contribution_register(_('Employees')).id,
                'company_id': self.id
                },
            ]
        return vals_list

    def _get_salary_rules_by_code(self, code):
        return self.env['hr.salary.rule'].sudo().search([('code', '=', code), ('company_id', 'in', self.ids)])

    def _parepare_salary_rules_data(self, struct):
        self.ensure_one()
        existing_rules = self.env['hr.salary.rule'].sudo().search([('struct_id', '=', struct.id), ('company_id', '=', self.id)])
        data = []
        for vals in self._parepare_salary_rules_vals_list(struct):
            if not existing_rules.filtered(lambda r: r.code == vals['code']):
                data.append(vals)
        return data

    def _prepare_salary_structure_data(self):
        self.ensure_one()
        return {
            'name': _('Base for new structures'),
            'code': 'BASE',
            'parent_id': False,
            'company_id': self.id
            }

    def _generate_salary_structures(self):
        self._generate_contribution_register()
        self._generate_payrol_contribution_types()
        self._generate_hr_advantage_templates()
        self._generate_salary_rule_categories()

        # use sudo to pass the multi-company rule during new company creation
        # when the user has not been assigned with new company access right yet
        salary_rule_obj = self.env['hr.salary.rule'].sudo()
        for r in self:
            structure_obj = self.env['hr.payroll.structure'].sudo().with_context(ignore_check=True)
            struct_vals = r._prepare_salary_structure_data()
            struct = structure_obj.search([('company_id', '=', r.id), ('code', '=', struct_vals['code'])], limit=1)
            if not struct:
                struct = structure_obj.create(struct_vals)
            struct_type = struct.type_id.with_company(r)
            if not struct_type.property_regular_struct_id:
                struct_type.property_regular_struct_id = struct
            salary_rule_obj.with_context(ignore_check=True).create(r._parepare_salary_rules_data(struct))
        return True

    def _generate_salary_slip_sequences(self):
        vals_list = []
        ir_sequence_obj = self.env['ir.sequence'].sudo()
        for r in self:
            # only generate sequence if not exists
            existing = ir_sequence_obj.search([('company_id', '=', r.id), ('code', '=', 'salary.slip')])
            if not existing:
                vals_list.append({
                    'name': _("Salary Slip"),
                    'code': 'salary.slip',
                    'prefix': 'SLIP/',
                    'padding': 5,
                    'company_id': r.id
                    })
        if vals_list:
            ir_sequence_obj.create(vals_list)

    def _generate_payroll_rules(self):
        return self._generate_salary_structures()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super(ResCompany, self).create(vals_list)
        companies._generate_salary_structures()
        companies._generate_salary_slip_sequences()
        return companies

    def _get_contracts_for_auto_payslip_generation_domain(self, start_date, end_date, employees=None):
        domain = [
            ('payslips_auto_generation', '=', True),
            ('company_id', 'in', self.ids),
            ('state', 'not in', ('draft', 'cancel')),
            ('date_start', '<=', end_date),
            '|', ('date_end', '=', False), ('date_end', '>', start_date)
            ]
        if employees:
            domain = [('employee_id', 'in', employees.ids)] + domain
        return domain

    def _get_batches_for_auto_payslip_generation_domain(self, start_date, end_date):
        domain = [
            ('company_id', 'in', self.ids),
            '|',
                '&', ('date_start', '>=', start_date), ('date_start', '<=', end_date),
                '&', ('date_end', '>=', start_date), ('date_end', '<=', end_date)
        ]
        return domain

    def _prepare_payslip_batch_data(self, start_date, end_date):
        self.ensure_one()
        return {
            'date_start': start_date,
            'date_end': end_date,
            'company_id': self.id,
            'salary_cycle_id': self.salary_cycle_id.id,
            }

    def _sync_contract_payslips_auto_generation(self):
        contracts_to_sync = self.env['hr.contract'].search([
            ('company_id', 'in', self.ids),
            ('state', '!=', 'cancel'),
            ])
        return contracts_to_sync._compute_payslips_auto_generation()

    @api.model
    def _cron_generate_payslips(self):
        companies = self.env['res.company'].sudo().search([('payslips_auto_generation', '=', True)])
        default_cycle = self.env.ref('to_hr_payroll.hr_salary_cycle_default')
        today = fields.Date.today()
        for company in companies:
            lang = company.payslips_auto_generation_lang or self.env.user.lang
            company = company.with_context(lang=lang)
            cycle = company.salary_cycle_id or default_cycle
            current_cycle_start_date = cycle._get_month_start_date(today)
            date_to_run = current_cycle_start_date + relativedelta(days=company.payslips_auto_generation_day - 1)
            if today < date_to_run:
                continue
            start_date, end_date = cycle._get_previous_month_cycle_interval(today)
            contracts_domain = company._get_contracts_for_auto_payslip_generation_domain(start_date, end_date)
            applicable_contracts = self.env['hr.contract'].with_context(active_test=False).search(contracts_domain)
            if not applicable_contracts:
                continue

            batches_domain = company._get_batches_for_auto_payslip_generation_domain(start_date, end_date)
            existing_batches = self.env['hr.payslip.run'].sudo().search(batches_domain)
            if existing_batches:
                continue

            employees = applicable_contracts.mapped('employee_id')
            if not employees:
                continue
            batch = self.env['hr.payslip.run'].with_context(lang=lang).create(company._prepare_payslip_batch_data(start_date, end_date))
            wizard = self.env['hr.payslip.employees'].with_context(lang=lang).create({
                'batch_id': batch.id,
                'mode': company.payslips_auto_generation_mode,
                'employee_ids': [(6, 0, employees.ids)]
                })
            wizard.with_company(company).with_context(lang=lang).compute_sheet()

        return True
