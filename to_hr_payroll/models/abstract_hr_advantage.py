from odoo import fields, models, api


class AbstractHrAdvantage(models.AbstractModel):
    _name = 'abstract.hr.advantage'
    _description = 'Hr Advantage Abstract'

    code = fields.Char('Code', required=True)
    currency_id = fields.Many2one('res.currency')
    amount = fields.Monetary(string='Monthly Amount', default=0.0, required=True, help='Monthly Amount for this advantage')
    included_in_payroll_contribution_register = fields.Boolean(
        string='Included in Payroll Contribution Register',
        help="If enabled, base amount of this allowance on the contract will be included "
        "in contribution registers when generate new contribution registers on the contract.")
    based_on_time_off_type_id = fields.Many2one('hr.leave.type', 'TimeOff Type',
        help="If specified, time off of this type may generate advantages for payslips based on time off time.\n"
        "Eg: with timeoff type for business travel,\n"
        "       allowance amount = number of hours off * cost of 1 hour of business travel\n")
    amount_type = fields.Selection([
        ('monthly_base', 'Monthly base'),
        ('timeoff_hour_base', 'Timeoff Hour Base')],
        default='monthly_base', string='Amount Type',
        compute="_compute_amount_type", store=True)

    @api.depends('based_on_time_off_type_id')
    def _compute_amount_type(self):
        for r in self:
            r.amount_type = 'timeoff_hour_base' if r.based_on_time_off_type_id else 'monthly_base'
