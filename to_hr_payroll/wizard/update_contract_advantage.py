from odoo import fields, models


class UpdateContractAdvantage(models.TransientModel):
    _name = 'update.contract.advantage'
    _description = 'Update Contract Advantages'

    template_id = fields.Many2one('hr.advantage.template', 'Advantage', readonly=True, required=True)
    contract_ids = fields.Many2many('hr.contract', string='Contracts', required=True,
                                    domain="[('employee_id.company_id', '=', company_id)]")
    amount = fields.Monetary('Amount', required=True)
    currency_id = fields.Many2one(related='template_id.currency_id')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def action_confirm(self):
        self.ensure_one()
        contract_advantages = self.contract_ids.advantage_ids.filtered(lambda r: r.template_id == self.template_id)
        if contract_advantages:
            contract_advantages.write({'amount': self.amount})
        vals_list = []
        for contract in (self.contract_ids - contract_advantages.contract_id):
            vals_list.append({
                'contract_id': contract.id,
                'template_id': self.template_id.id,
                'amount': self.amount
            })
        self.env['hr.contract.advantage'].create(vals_list)
