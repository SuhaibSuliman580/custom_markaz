from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AbstractHrSalaryRule(models.AbstractModel):
    _name = 'abstract.hr.salary.rule'
    _description = 'Hr Salary Rule Abstract'

    name = fields.Char(required=True, translate=True)
    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', required=True, ondelete='restrict')
    company_id = fields.Many2one(related='struct_id.company_id', store=True,
                                 help="The company to which this rule belongs")
    code = fields.Char(required=True,
        help="The code of salary rules can be used as reference in computation of other rules. "
             "In that case, it is case sensitive.")
    sequence = fields.Integer(required=True, index=True, default=5,
        help='Use to arrange calculation sequence')
    quantity = fields.Char(default='1.0',
        help="It is used in computation for percentage and fixed amount. "
             "For e.g. A rule for Meal Voucher having fixed amount of "
             "1€ per worked day can have its quantity defined in expression "
             "like worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True,
                                  domain="[('company_id','=',company_id)]")
    active = fields.Boolean(default=True,
        help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    appears_on_payslip = fields.Boolean(string='Appears on Payslip', default=True,
        help="Used to display the salary rule on payslip printed version.")
    register_id = fields.Many2one('hr.contribution.register', string='Contribution Register', ondelete='restrict',
        help="Eventual third party involved in the salary payment of the employees.")
    register_category_id = fields.Many2one('hr.contribution.category', string='Contribution Register Category',
                                            related='register_id.category_id', store=True)
    note = fields.Text(string='Description')

    @api.constrains('register_id')
    def _check_register_partner(self):
        ignore_check = self._context.get('ignore_check', False)
        for r in self:
            if not ignore_check and r.register_id and not r.register_id.partner_id and r.register_category_id.partner_required:
                raise ValidationError(_("The contribution category '%s' requires a partner for its contribution registers."
                                        " Please specify a partner for the contribution register '%s'")
                                        % (r.register_category_id.name, r.register_id.name))
