from odoo import models, fields, api, _


class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    code = fields.Char(string='Code', size=20, help="The unique code of the tag")

    @api.depends('applicability', 'country_id', 'code')
    def _compute_display_name(self):
        super()._compute_display_name()
        for r in self:
            if r.code:
                display_name = _("%s - %s", r.code, r.display_name)
                r.display_name = display_name

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
        tags = self.search(domain + args, limit=limit)
        return tags.name_get()
