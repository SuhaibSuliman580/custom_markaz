from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_apply_invoice_template_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apply Invoice Template',
            'res_model': 'invoice.template.apply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_company_id': self.company_id.id,
            },
        }
