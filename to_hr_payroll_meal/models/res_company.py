from odoo import models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _prepare_contribution_register_data(self):
        res = super(ResCompany, self)._prepare_contribution_register_data()
        res.append({
            'name': _('HR Meal Order Deduction'),
            'partner_id': False,
            'category_id': self.env.ref('to_hr_payroll_meal.hr_contribution_category_deduction').id,
            'company_id': self.id
            })
        return res

    def _prepare_salary_rule_categories_data(self):
        res = super(ResCompany, self)._prepare_salary_rule_categories_data()
        res.append({
            'name': _('HR Meal Order Deduction'),
            'code': 'MODED', 'company_id': self.id,
            'parent_id': self._get_salary_rule_categ('DED_BEFORE_TAX').id,
            })
        return res

    def _parepare_salary_rules_vals_list(self, struct):
        res = super(ResCompany, self)._parepare_salary_rules_vals_list(struct)
        res.append(self._prepare_meal_order_salary_rules(struct))
        return res

    def _prepare_meal_order_salary_rules(self, struct):
        self.ensure_one()
        return {
            'name': _('HR Meal Order Deduction Amount'),
            'sequence': 3160,
            'code': 'MODED',
            'struct_id': struct.id,
            'category_id': self._get_salary_rule_categ('MODED').id,
            'condition_select': 'python',
            'condition_python': 'result = True if payslip.meal_order_line_ids else False',
            'amount_select': 'code',
            'appears_on_payslip': True,
            'amount_python_compute': "result = -1 * sum(payslip.meal_order_line_ids.mapped('employee_amount'))",
            'register_id': self._get_contribution_register(_("HR Meal Order Deduction")).id,
            'company_id': self.id
            }

    def _prepare_meal_order_salary_rules_data(self, struct):
        self.ensure_one()
        data = {}
        rule = self._prepare_meal_order_salary_rules(struct)
        existing_rules = self.env['hr.salary.rule'].sudo().search([('struct_id', '=', struct.id), ('company_id', '=', self.id), ('code', '=', rule['code'])])
        if not existing_rules:
            data = rule
        return data

    def _generate_meal_order_salary_rules(self):
        self._generate_contribution_register()
        self._generate_salary_rule_categories()

        salary_rule_obj = self.env['hr.salary.rule'].sudo()
        structure_obj = self.env['hr.payroll.structure'].sudo()

        for r in self:
            structs = structure_obj.search([
                ('company_id', '=', r.id),
                ('code', '=', 'BASE')
            ])

            for struct in structs:
                rule_data = r._prepare_meal_order_salary_rules_data(struct)
                if rule_data:
                    salary_rule_obj.create(rule_data)
        return True
