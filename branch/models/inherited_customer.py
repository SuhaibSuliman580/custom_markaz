# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartnerIn(models.Model):
    _inherit = 'res.partner'

    @api.model
    def default_get(self, default_fields):
        res = super(ResPartnerIn, self).default_get(default_fields)
        if 'company_id' in default_fields and not res.get('company_id'):
            res['company_id'] = self.env.user.company_id.id
        if self.env.user.branch_id:
            res.update({
                'branch_id' : self.env.user.branch_id.id or False
            })
        return res

    @api.model_create_multi
    def create(self, vals_list):
        company_id = self.env.user.company_id.id
        vals_list = [
            dict(vals, company_id=company_id) if 'company_id' not in vals else vals
            for vals in vals_list
        ]
        return super().create(vals_list)

    branch_id = fields.Many2one('res.branch', string="Branch")
