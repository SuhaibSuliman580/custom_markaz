from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class HrAdvandageTemplate(models.Model):
    _name = 'hr.advantage.template'
    _inherit = ['abstract.hr.advantage', 'mail.thread', 'mail.activity.mixin']
    _description = "Employee's Advantage Template"

    name = fields.Char('Name', required=True, translate=True, tracking=True)
    amount = fields.Monetary(tracking=True, help='Default Monthly Amount for this advantage')
    lower_bound = fields.Float('Lower Bound', compute='_compute_bounds', store=True, required=True, readonly=False,
                               tracking=True,
                               help="Lower bound authorized by the employer for this advantage")
    upper_bound = fields.Float('Upper Bound', compute='_compute_bounds', store=True, required=True, readonly=False,
                               tracking=True,
                               help="Upper bound authorized by the employer for this advantage")
    company_id = fields.Many2one('res.company', string='Company', tracking=True, required=True,
                                 default=lambda self: self.env.company,
                                 ondelete='cascade')
    currency_id = fields.Many2one(related='company_id.currency_id', store=True, tracking=True)
    job_advantage_ids = fields.One2many('hr.job.advantage', 'template_id', string='Job Positions', auto_join=True,
                                        help="The job positions that are applied with this advantage template. "
                                        "when selecting this allowance template and related job position on employee contract, "
                                        "this allowance amount will be set as default value on contract.")

    @api.constrains('amount', 'lower_bound', 'currency_id')
    def _check_lower_bound(self):
        for r in self:
            if not r.currency_id:
                continue
            if float_compare(r.lower_bound, r.amount, precision_rounding=r.currency_id.rounding or 0.01) == 1:
                raise UserError(_("The Lower Bound must be less than or equal to the Monthly Amount"))

    @api.constrains('amount', 'upper_bound', 'currency_id')
    def _check_upper_bound(self):
        for r in self:
            if not r.currency_id:
                continue
            if float_compare(r.upper_bound, r.amount, precision_rounding=r.currency_id.rounding or 0.01) == -1:
                raise UserError(_("The Upper Bound must be greater than or equal to the Monthly Amount"))

    @api.depends('currency_id', 'amount')
    def _compute_bounds(self):
        for r in self:
            lower_bound = r.lower_bound or 0.0
            upper_bound = r.upper_bound or 0.0
            if r.currency_id:
                if float_compare(r.lower_bound, r.amount, precision_rounding=r.currency_id.rounding or 0.01) == 1:
                    lower_bound = r.amount
                if float_compare(r.upper_bound, r.amount, precision_rounding=r.currency_id.rounding or 0.01) == -1:
                    upper_bound = r.amount
            r.lower_bound = lower_bound
            r.upper_bound = upper_bound

    def _update_job_position_advantages(self):
        for r in self:
            job_advantages = self.env['hr.job.advantage'].search([('template_id', '=', r.id)])
            job_advantages.write({
                'amount': r.amount
                })

    def _generate_job_position_advantages(self):
        to_update = self.env['hr.job.advantage'].search([('template_id', 'in', self.ids)])
        if to_update:
            to_update._synch_from_templates()
        for r in self:
            jobs = self.env['hr.job'].search([('company_id', '=', r.company_id.id)]) - to_update.mapped('job_id')
            for job in jobs:
                job.write({
                    'advantage_ids': [(0, 0, {
                        'template_id': r.id,
                        'job_id': job.id,
                        'amount': r.amount
                        })]
                    })

    def action_update_contract_advantage(self):
        action = self.env['ir.actions.act_window']._for_xml_id('to_hr_payroll.update_contract_advantage_action')
        action['context'] = {
            'default_template_id': self.id,
            'default_amount': self.amount,
        }
        return action
