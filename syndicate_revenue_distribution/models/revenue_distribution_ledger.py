from odoo import api, fields, models


class SyndicateRevenueDistributionLedgerLine(models.Model):
    _name = 'syndicate.revenue.distribution.ledger.line'
    _description = 'Revenue Distribution Ledger Line'
    _order = 'invoice_date, move_id, id'
    _check_company_auto = True

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        copy=False,
        default='New',
    )
    move_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        readonly=True,
        ondelete='restrict',
        index=True,
    )
    move_line_id = fields.Many2one(
        'account.move.line',
        string='Generated Move Line',
        readonly=True,
        ondelete='set null',
        index=True,
    )
    source_move_line_id = fields.Many2one(
        'account.move.line',
        string='Source Move Line',
        readonly=True,
        ondelete='set null',
    )
    journal_entry_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        ondelete='restrict',
    )
    invoice_date = fields.Date(string='Invoice Date', readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    fund_box_id = fields.Many2one('syndicate.fund.box', string='Fund Box', readonly=True, index=True)
    account_id = fields.Many2one('account.account', string='Income Account', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
    )
    percentage = fields.Float(string='Percentage', readonly=True, digits=(16, 4))
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    original_amount = fields.Monetary(
        string='Original Amount',
        currency_field='currency_id',
        readonly=True,
    )
    distributed_amount = fields.Monetary(
        string='Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    company_id = fields.Many2one('res.company', string='Company', readonly=True, index=True)
    state = fields.Selection(
        [
            ('posted', 'Posted'),
            ('cancelled', 'Cancelled'),
            ('reversed', 'Reversed'),
        ],
        string='State',
        default='posted',
        required=True,
        readonly=True,
        index=True,
    )
    ledger_source = fields.Selection(
        [
            ('invoice_post', 'Invoice Post'),
            ('reversal', 'Reversal'),
            ('manual_adjustment', 'Manual Adjustment'),
        ],
        string='Ledger Source',
        default='invoice_post',
        required=True,
        readonly=True,
        index=True,
    )
    distribution_source = fields.Selection(
        [
            ('product', 'Product'),
            ('template', 'Template'),
            ('manual', 'Manual'),
        ],
        string='Distribution Source',
        default='product',
        required=True,
        readonly=True,
        index=True,
    )
    created_by_id = fields.Many2one(
        'res.users',
        string='Created By',
        related='create_uid',
        readonly=True,
    )
    created_on = fields.Datetime(
        string='Created On',
        related='create_date',
        readonly=True,
    )
    invoice_number_snapshot = fields.Char(
        string='Invoice Number Snapshot',
        readonly=True,
        copy=False,
    )
    partner_name_snapshot = fields.Char(
        string='Partner Name Snapshot',
        readonly=True,
        copy=False,
    )
    partner_ref_snapshot = fields.Char(
        string='Partner Reference Snapshot',
        readonly=True,
        copy=False,
    )
    product_name_snapshot = fields.Char(
        string='Product Name Snapshot',
        readonly=True,
        copy=False,
    )
    product_default_code_snapshot = fields.Char(
        string='Product Internal Reference Snapshot',
        readonly=True,
        copy=False,
    )
    product_type_snapshot = fields.Char(
        string='Product Type Snapshot',
        readonly=True,
        copy=False,
    )
    fund_box_code_snapshot = fields.Char(
        string='Fund Box Code Snapshot',
        readonly=True,
        copy=False,
    )
    fund_box_name_snapshot = fields.Char(
        string='Fund Box Name Snapshot',
        readonly=True,
        copy=False,
    )
    account_code_snapshot = fields.Char(
        string='Income Account Code Snapshot',
        readonly=True,
        copy=False,
    )
    account_name_snapshot = fields.Char(
        string='Income Account Name Snapshot',
        readonly=True,
        copy=False,
    )
    analytic_account_name_snapshot = fields.Char(
        string='Analytic Account Name Snapshot',
        readonly=True,
        copy=False,
    )
    company_name_snapshot = fields.Char(
        string='Company Name Snapshot',
        readonly=True,
        copy=False,
    )
    currency_name_snapshot = fields.Char(
        string='Currency Name Snapshot',
        readonly=True,
        copy=False,
    )
    currency_symbol_snapshot = fields.Char(
        string='Currency Symbol Snapshot',
        readonly=True,
        copy=False,
    )
    reversal_move_id = fields.Many2one(
        'account.move',
        string='Reversal Move',
        readonly=True,
        ondelete='set null',
    )
    reversed_ledger_id = fields.Many2one(
        'syndicate.revenue.distribution.ledger.line',
        string='Reversed Ledger Line',
        readonly=True,
        ondelete='set null',
    )

    _sql_constraints = [
        (
            'move_line_source_unique',
            'unique(move_line_id, ledger_source)',
            'Ledger line already exists for this move line and source.',
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'syndicate.revenue.distribution.ledger.line'
                    ) or 'New'
                )
        return super().create(vals_list)
