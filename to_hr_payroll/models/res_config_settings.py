from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

#     module_to_hr_payroll_work_entry = fields.Boolean(string='Work Entry')
    module_to_hr_payroll_account = fields.Boolean(string='Payroll Accounting')
    module_l10n_vn_viin_hr_payroll = fields.Boolean(string='Vietnam Payroll')
    module_viin_hr_payroll_administrative_region = fields.Boolean(string='Enable Payroll Administrative Region')

    basic_wage_rule_categ_id = fields.Many2one(related='company_id.basic_wage_rule_categ_id', readonly=False, domain="[('company_id','=',company_id)]")
    gross_salary_rule_categ_id = fields.Many2one(related='company_id.gross_salary_rule_categ_id', readonly=False, domain="[('company_id','=',company_id)]")
    tax_base_rule_categ_id = fields.Many2one(related='company_id.tax_base_rule_categ_id', readonly=False, domain="[('company_id','=',company_id)]")
    net_income_salary_rule_categ_id = fields.Many2one(related='company_id.net_income_salary_rule_categ_id', readonly=False, domain="[('company_id','=',company_id)]")

    payslips_auto_generation = fields.Boolean(related='company_id.payslips_auto_generation', readonly=False)
    payslips_auto_generation_mode = fields.Selection(related='company_id.payslips_auto_generation_mode', readonly=False)
    payslips_auto_generation_day = fields.Integer(related='company_id.payslips_auto_generation_day', readonly=False)
    payslips_auto_generation_lang = fields.Selection(related='company_id.payslips_auto_generation_lang', readonly=False)
    salary_cycle_id = fields.Many2one(related='company_id.salary_cycle_id', readonly=False)

    def action_generate_payroll_rules(self):
        return self.mapped('company_id')._generate_payroll_rules()

    def action_sync_contract_payslips_auto_generation(self):
        return self.mapped('company_id')._sync_contract_payslips_auto_generation()
