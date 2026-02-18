from odoo import fields, models


class HrContributionRegister(models.Model):
    _name = 'hr.contribution.register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contribution Register'

    name = fields.Char(required=True, translate=True, tracking=True)
    category_id = fields.Many2one('hr.contribution.category', string='Category', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, tracking=True,
                                 default=lambda self: self.env.company, ondelete='cascade')
    salary_rule_ids = fields.One2many('hr.salary.rule', 'register_id', string='Salary Rules')
    partner_id = fields.Many2one('res.partner', string='Partner', tracking=True, index=True,
                                 domain="[('company_id', 'in', (False, company_id))]",
                                 help="A third party that is involved in the salary payment of salary rules of the employees.\n"
                                 "Please note that, the partner specified here will be ignored if one is specified in the field"
                                 " Contribution Register Partner of the employee department or a parent department of the"
                                 " employee department.")
    department_register_partner_ids = fields.One2many('hr.department.register.partner', 'contribution_register_id',
                                                      string='Department Register Partner',
                                                      help="When set the partner for each department. The generated salary entries "
                                                      " will separate the jounal item according to partners have been set up.")
    payslip_line_ids = fields.One2many('hr.payslip.line', 'register_id', string='Payslip Line', readonly=True)
    note = fields.Text(string='Description')
