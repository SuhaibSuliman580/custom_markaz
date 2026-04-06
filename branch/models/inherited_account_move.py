# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.model
    def _get_default_branch_id(self, partner_id=False):
        partner_branch = False
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            partner_branch = partner.branch_id.id if partner and partner.branch_id else False
        return (
            self._context.get('branch_id')
            or partner_branch
            or (self.env.user.branch_id.id if self.env.user.branch_id else False)
        )

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        partner_id = res.get('partner_id') or self._context.get('default_partner_id')
        branch_id = self._get_default_branch_id(partner_id=partner_id)
        if branch_id:
            res['branch_id'] = branch_id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_id = vals.get('partner_id')
            if not vals.get('branch_id'):
                vals['branch_id'] = self._get_default_branch_id(partner_id=partner_id)
        moves = super().create(vals_list)
        moves._check_partner_branch_consistency()
        return moves

    def write(self, vals):
        res = super().write(vals)
        tracked = {'partner_id', 'branch_id'}
        if tracked.intersection(vals):
            self._check_partner_branch_consistency()
        return res

    @api.onchange('partner_id')
    def _onchange_partner_id_branch_id(self):
        for move in self:
            partner_branch = move.partner_id.branch_id
            if partner_branch:
                move.branch_id = partner_branch
            elif not move.branch_id and move.env.user.branch_id:
                move.branch_id = move.env.user.branch_id

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_branch = self.branch_id
        if selected_branch:
            user_id = self.env['res.users'].browse(self.env.uid)
            user_branch = user_id.sudo().branch_id
            if user_branch and user_branch.id != selected_branch.id:
                raise UserError(_(
                    "Please select active branch only. Other may create the Multi branch issue.\n\n"
                    "e.g: If you wish to add other branch then Switch branch from the header and set that."
                ))

    def _check_partner_branch_consistency(self):
        for move in self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund', 'out_receipt') and m.partner_id and m.branch_id):
            partner_branch = move.partner_id.branch_id
            if partner_branch and partner_branch != move.branch_id:
                raise ValidationError(_(
                    "The invoice branch (%(invoice_branch)s) must match the doctor/customer branch (%(partner_branch)s) for %(partner)s.",
                    invoice_branch=move.branch_id.display_name,
                    partner_branch=partner_branch.display_name,
                    partner=move.partner_id.display_name,
                ))

    def action_post(self):
        self._check_partner_branch_consistency()
        return super().action_post()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    branch_id = fields.Many2one('res.branch', string="Branch", related="move_id.branch_id", store=True)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        branch_id = self._context.get('branch_id') or (self.env.user.branch_id.id if self.env.user.branch_id else False)
        if self._context.get('default_move_id'):
            move = self.env['account.move'].browse(self._context['default_move_id'])
            if move.branch_id:
                branch_id = move.branch_id.id
        if branch_id:
            res['branch_id'] = branch_id
        return res
