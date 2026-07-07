from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MembershipServiceType(models.Model):
    _name = 'membership.service.type'
    _description = 'نوع خدمة طبيب'
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(string='الاسم', required=True, translate=True)
    active = fields.Boolean(string='نشط', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='company_id.currency_id',
        readonly=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='المنتج المحاسبي',
        domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    invoice_template_id = fields.Many2one(
        'invoice.service.template',
        string='قالب فاتورة الخدمة',
        domain="[('company_id', '=', company_id)]",
        check_company=True,
    )
    fee = fields.Monetary(string='الرسم', currency_field='currency_id')
    requires_active_membership = fields.Boolean(string='يتطلب عضوية فعالة', default=False)
    requires_attachments = fields.Boolean(string='يتطلب مرفقات', default=False)
    generates_invoice = fields.Boolean(string='ينشئ فاتورة محاسبية', default=True)
    requires_revenue_distribution = fields.Boolean(string='يتطلب توزيع إيراد', default=False)
    notes = fields.Text(string='الملاحظات')

    _sql_constraints = [
        (
            'name_company_unique',
            'unique(name, company_id)',
            'يجب أن يكون اسم نوع الخدمة فريدًا ضمن كل شركة.',
        ),
    ]

    @api.constrains('generates_invoice', 'requires_revenue_distribution', 'product_id', 'invoice_template_id', 'fee')
    def _check_invoice_configuration(self):
        for rec in self:
            if rec.requires_revenue_distribution and not rec.generates_invoice:
                raise ValidationError(_('الخدمة التي تتطلب توزيع إيراد يجب أن تنشئ فاتورة محاسبية.'))
            if not rec.generates_invoice:
                continue
            if rec.invoice_template_id:
                continue
            if not rec.product_id:
                raise ValidationError(
                    _('يرجى ضبط منتج محاسبي أو قالب فاتورة.')
                )
            if rec.fee < 0:
                raise ValidationError(_('لا يمكن أن يكون رسم الخدمة سالبًا.'))

    @api.constrains('company_id', 'product_id', 'invoice_template_id')
    def _check_company_configuration(self):
        for rec in self:
            if rec.product_id.company_id and rec.product_id.company_id != rec.company_id:
                raise ValidationError(_('يجب أن تطابق شركة المنتج شركة الخدمة.'))
            if rec.invoice_template_id and rec.invoice_template_id.company_id != rec.company_id:
                raise ValidationError(_('يجب أن تطابق شركة قالب الفاتورة شركة الخدمة.'))

    def _get_revenue_distribution_products(self):
        self.ensure_one()
        products = self.env['product.product']
        if self.invoice_template_id:
            products |= self.invoice_template_id.line_ids.mapped('product_id')
        elif self.product_id:
            products |= self.product_id
        return products.exists()
