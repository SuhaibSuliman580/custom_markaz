from odoo import models, fields, tools


class HrPayrollAnalysis(models.Model):
    _name = 'hr.payroll.analysis'
    _description = "Payroll Analysis"
    _order = 'date_to desc, date_from desc'
    _auto = False

    date_confirmed = fields.Date(string='Date Confirmed')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    date_create = fields.Date(string='Date Created')
    slip_id = fields.Many2one('hr.payslip', string='Payslip', readonly=True)
    register_id = fields.Many2one('hr.contribution.register', string='Contribution Register', readonly=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Salary Rule', readonly=True)
    salary_rule_name = fields.Char(string='Salary Rule Name', translate=True, readonly=True)
    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', readonly=True)
    category_id = fields.Many2one('hr.salary.rule.category', string='Category')
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    barcode = fields.Char(string='Badge ID', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Position', readonly=True)
    amount = fields.Float(string='Amount', digits='Payroll', readonly=True)
    company_cost = fields.Float(string='Company Cost', groups='to_hr_payroll.group_hr_payroll_team_leader')
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    state = fields.Selection([
        ('draft', "Draft"),
        ('verify', "Waiting"),
        ('done', "Done"),
        ('cancel', "Cancelled"),
    ])
    thirteen_month_pay = fields.Boolean(string='13th-Month Pay', readonly=True)
    rule_appears_on_payslip = fields.Boolean(string='Rules Appear on Payslip')
    contribution_register_category_id = fields.Many2one('hr.contribution.category', string='Contribution Register Category')

    def _select(self):
        sql = """
        SELECT
            l.id AS id,
            l.register_id,
            salrule.id AS salary_rule_id,
            salrule.name AS salary_rule_name,
            salstruct.id AS struct_id,
            salrule.appears_on_payslip AS rule_appears_on_payslip,
            salrule.category_id AS category_id,
            l.employee_id,
            emp.barcode,
            l.total as amount,
            CASE WHEN categ.paid_by_company = True
                THEN l.total
                ELSE 0.0
                END AS company_cost,
            l.company_id,
            ps.job_id,
            ps.date_confirmed,
            ps.date_from,
            ps.date_to,
            ps.state AS state,
            ps.create_date AS date_create,
            ps.thirteen_month_pay AS thirteen_month_pay,
            ps.department_id,
            ps.id AS slip_id,
            contrib_reg_cat.id AS contribution_register_category_id
        """
        return sql

    def _from(self):
        sql = """
        FROM
            hr_payslip_line AS l
        """
        return sql

    def _join(self):
        sql = """
            LEFT JOIN hr_payslip AS ps ON ps.id = l.slip_id
            LEFT JOIN hr_employee AS emp ON emp.id = l.employee_id
            LEFT JOIN hr_job as job ON job.id = emp.job_id
            LEFT JOIN hr_department AS dept ON dept.id = ps.department_id
            LEFT JOIN hr_salary_rule AS salrule ON salrule.id = l.salary_rule_id
            LEFT JOIN hr_payroll_structure AS salstruct ON salstruct.id = ps.struct_id
            LEFT JOIN hr_salary_rule_category AS categ ON categ.id = salrule.category_id
            LEFT JOIN hr_contribution_category AS contrib_reg_cat ON contrib_reg_cat.id = salrule.register_category_id
        """
        return sql

    def _where(self):
        sql = """
        WHERE
            ps.state != 'cancel'
        """
        return sql

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
        %s
        %s
        %s
        %s)
        """ % (self._table, self._select(), self._from(), self._join(), self._where()))
