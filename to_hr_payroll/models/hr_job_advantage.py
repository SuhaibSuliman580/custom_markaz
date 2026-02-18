from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class HrJobAdvandage(models.Model):
    _name = 'hr.job.advantage'
    _inherit = ['abstract.hr.advantage', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'template_id'
    _description = "Employee's Advantage on Job Position"

    template_id = fields.Many2one('hr.advantage.template', string='Advantage', required=True, ondelete='restrict', tracking=True,
                                  domain="[('company_id', 'in', (False, company_id))]")
    job_id = fields.Many2one('hr.job', string='Job Position', required=True, ondelete='cascade', tracking=True)

    # default company: use domain to filter by the company,
    # Otherwise, on view, job_id = False => company=False
    company_id = fields.Many2one(related='job_id.company_id', store=True, tracking=True)
    currency_id = fields.Many2one(related='job_id.currency_id', store=True, tracking=True)
    code = fields.Char(related='template_id.code')
    amount = fields.Monetary(compute='_compute_amount', store=True, readonly=False, tracking=True)
    # Override `based_on_time_off_type_id` field
    based_on_time_off_type_id = fields.Many2one(compute="_compute_based_on_time_off_type_id", store=True, readonly=False,
                                                domain="[('company_id', 'in', (False, company_id))]")

    _sql_constraints = [
        ('name_template_id',
         'UNIQUE(template_id,job_id)',
         "The advantage must be unique per job position!"),
    ]

    @api.constrains('template_id', 'amount', 'currency_id')
    def _check_amount(self):
        for r in self:
            if not r.template_id or not r.currency_id:
                continue
            if float_compare(r.amount, r.template_id.lower_bound, precision_rounding=r.currency_id.rounding) == -1:
                raise UserError(_("You cannot specify an amount that is less than the Lower Bound of the template %s") % r.template_id.name)
            if float_compare(r.amount, r.template_id.upper_bound, precision_rounding=r.currency_id.rounding) == 1:
                raise UserError(_("You cannot specify an amount that is greater than the Upper Bound of the template %s") % r.template_id.name)

    @api.depends('template_id')
    def _compute_based_on_time_off_type_id(self):
        for r in self:
            r.based_on_time_off_type_id = r.template_id.based_on_time_off_type_id

    @api.depends('template_id')
    def _compute_amount(self):
        for r in self:
            if r.template_id:
                r.amount = r.template_id.amount
            else:
                r.amount = 0.0

    def _synch_from_templates(self):
        for r in self:
            r.amount = r.template_id.amount
