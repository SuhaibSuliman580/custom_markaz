from odoo import api, fields, models


class SyndicateRevenueDistributionLedgerLine(models.Model):
    _name = 'syndicate.revenue.distribution.ledger.line'
    _description = 'سطر دفتر توزيع الإيرادات'
    _order = 'invoice_date, move_id, id'
    _check_company_auto = True

    name = fields.Char(
        string='الاسم',
        required=True,
        readonly=True,
        copy=False,
        default='New',
    )
    move_id = fields.Many2one(
        'account.move',
        string='الفاتورة',
        required=True,
        readonly=True,
        ondelete='restrict',
        index=True,
    )
    move_line_id = fields.Many2one(
        'account.move.line',
        string='سطر القيد المنشأ',
        readonly=True,
        ondelete='set null',
        index=True,
    )
    source_move_line_id = fields.Many2one(
        'account.move.line',
        string='سطر القيد المصدر',
        readonly=True,
        ondelete='set null',
    )
    journal_entry_id = fields.Many2one(
        'account.move',
        string='قيد اليومية',
        readonly=True,
        ondelete='restrict',
    )
    invoice_date = fields.Date(string='تاريخ الفاتورة', readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string='الشريك', readonly=True)
    product_id = fields.Many2one('product.product', string='المنتج', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='قالب المنتج', readonly=True)
    fund_box_id = fields.Many2one('syndicate.fund.box', string='الصندوق', readonly=True, index=True)
    account_id = fields.Many2one('account.account', string='حساب الإيراد', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='الحساب التحليلي',
        readonly=True,
    )
    percentage = fields.Float(string='النسبة', readonly=True, digits=(16, 4))
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    original_amount = fields.Monetary(
        string='المبلغ الأصلي',
        currency_field='currency_id',
        readonly=True,
    )
    distributed_amount = fields.Monetary(
        string='المبلغ الموزع',
        currency_field='currency_id',
        readonly=True,
    )
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True, index=True)
    state = fields.Selection(
        [
            ('posted', 'مرحّل'),
            ('cancelled', 'ملغى'),
            ('reversed', 'معكوس'),
        ],
        string='الحالة',
        default='posted',
        required=True,
        readonly=True,
        index=True,
    )
    ledger_source = fields.Selection(
        [
            ('invoice_post', 'ترحيل الفاتورة'),
            ('reversal', 'عكس القيد'),
            ('manual_adjustment', 'تسوية يدوية'),
        ],
        string='مصدر الدفتر',
        default='invoice_post',
        required=True,
        readonly=True,
        index=True,
    )
    distribution_source = fields.Selection(
        [
            ('product', 'المنتج'),
            ('template', 'القالب'),
            ('manual', 'يدوي'),
        ],
        string='مصدر التوزيع',
        default='product',
        required=True,
        readonly=True,
        index=True,
    )
    created_by_id = fields.Many2one(
        'res.users',
        string='أنشئ بواسطة',
        related='create_uid',
        readonly=True,
    )
    created_on = fields.Datetime(
        string='أنشئ في',
        related='create_date',
        readonly=True,
    )
    invoice_number_snapshot = fields.Char(
        string='لقطة رقم الفاتورة',
        readonly=True,
        copy=False,
    )
    partner_name_snapshot = fields.Char(
        string='لقطة اسم الشريك',
        readonly=True,
        copy=False,
    )
    partner_ref_snapshot = fields.Char(
        string='لقطة مرجع الشريك',
        readonly=True,
        copy=False,
    )
    product_name_snapshot = fields.Char(
        string='لقطة اسم المنتج',
        readonly=True,
        copy=False,
    )
    product_default_code_snapshot = fields.Char(
        string='لقطة المرجع الداخلي للمنتج',
        readonly=True,
        copy=False,
    )
    product_type_snapshot = fields.Char(
        string='لقطة نوع المنتج',
        readonly=True,
        copy=False,
    )
    fund_box_code_snapshot = fields.Char(
        string='لقطة كود الصندوق',
        readonly=True,
        copy=False,
    )
    fund_box_name_snapshot = fields.Char(
        string='لقطة اسم الصندوق',
        readonly=True,
        copy=False,
    )
    account_code_snapshot = fields.Char(
        string='لقطة كود حساب الإيراد',
        readonly=True,
        copy=False,
    )
    account_name_snapshot = fields.Char(
        string='لقطة اسم حساب الإيراد',
        readonly=True,
        copy=False,
    )
    analytic_account_name_snapshot = fields.Char(
        string='لقطة اسم الحساب التحليلي',
        readonly=True,
        copy=False,
    )
    company_name_snapshot = fields.Char(
        string='لقطة اسم الشركة',
        readonly=True,
        copy=False,
    )
    currency_name_snapshot = fields.Char(
        string='لقطة اسم العملة',
        readonly=True,
        copy=False,
    )
    currency_symbol_snapshot = fields.Char(
        string='لقطة رمز العملة',
        readonly=True,
        copy=False,
    )
    reversal_move_id = fields.Many2one(
        'account.move',
        string='قيد العكس',
        readonly=True,
        ondelete='set null',
    )
    reversed_ledger_id = fields.Many2one(
        'syndicate.revenue.distribution.ledger.line',
        string='سطر الدفتر المعكوس',
        readonly=True,
        ondelete='set null',
    )

    _sql_constraints = [
        (
            'move_line_source_unique',
            'unique(move_line_id, ledger_source)',
            'يوجد سطر دفتر لهذا السطر المحاسبي وهذا المصدر مسبقاً.',
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
