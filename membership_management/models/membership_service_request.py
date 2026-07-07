from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import html_escape


class MembershipServiceRequest(models.Model):
    _name = 'membership.service.request'
    _description = 'طلب خدمة طبيب'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _check_company_auto = True

    name = fields.Char(
        string='المرجع',
        required=True,
        readonly=True,
        default=lambda self: _('New'),
        copy=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='الطبيب',
        required=True,
        domain="[('is_doctor', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    service_type_id = fields.Many2one(
        'membership.service.type',
        string='نوع الخدمة',
        required=True,
        tracking=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
        check_company=True,
    )
    membership_period_id = fields.Many2one(
        'membership.period',
        string='فترة العضوية',
        readonly=True,
        copy=False,
        check_company=True,
    )
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('waiting_financial_approval', 'بانتظار تصديق المالية'),
        ('waiting_payment', 'بانتظار الدفع'),
        ('paid', 'مدفوع'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'منجز'),
        ('cancelled', 'ملغى'),
    ], default='draft', required=True, tracking=True, copy=False)
    invoice_id = fields.Many2one(
        'account.move',
        string='الفاتورة',
        readonly=True,
        copy=False,
        check_company=True,
    )
    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='حالة الدفع',
    )
    revenue_distribution_required = fields.Boolean(
        string='يتطلب توزيع إيراد',
        compute='_compute_revenue_distribution_status',
        search='_search_revenue_distribution_required',
    )
    revenue_distribution_ready = fields.Boolean(
        string='توزيع الإيراد جاهز',
        compute='_compute_revenue_distribution_status',
        search='_search_revenue_distribution_ready',
    )
    revenue_distribution_status_message = fields.Text(
        string='حالة توزيع الإيراد',
        compute='_compute_revenue_distribution_status',
    )
    revenue_distribution_product_names = fields.Text(
        string='المنتجات التي تم فحصها',
        compute='_compute_revenue_distribution_status',
    )
    financial_validation_ready = fields.Boolean(
        string='جاهز لاعتماد المالية',
        compute='_compute_financial_validation',
        search='_search_financial_validation_ready',
    )
    financial_validation_result = fields.Char(
        string='نتيجة التحليل المالي',
        compute='_compute_financial_validation',
    )
    financial_validation_failure_message = fields.Text(
        string='أسباب عدم الجاهزية',
        compute='_compute_financial_validation',
    )
    financial_validation_html = fields.Html(
        string='التحليل المالي',
        compute='_compute_financial_validation',
        sanitize=False,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='company_id.currency_id',
        readonly=True,
    )
    fee = fields.Monetary(
        string='الرسم',
        related='service_type_id.fee',
        currency_field='currency_id',
        readonly=True,
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'membership_service_request_ir_attachment_rel',
        'request_id',
        'attachment_id',
        string='المرفقات',
    )
    request_notes = fields.Text(
        string='ملاحظات الذاتية',
        groups='membership_management.group_membership_service_registration,membership_management.group_membership_service_manager',
    )
    finance_notes = fields.Text(
        string='ملاحظات المالية',
        groups='membership_management.group_membership_service_finance,membership_management.group_membership_service_manager',
    )
    cashier_notes = fields.Text(
        string='ملاحظات الصندوق',
        groups='membership_management.group_membership_service_cashier,membership_management.group_membership_service_manager',
    )
    service_notes = fields.Text(
        string='ملاحظات تنفيذ الخدمة',
        groups='membership_management.group_membership_service_registration,membership_management.group_membership_service_manager',
    )
    cancel_reason = fields.Text(
        string='سبب الرفض/الإلغاء',
        groups='membership_management.group_membership_service_finance,membership_management.group_membership_service_manager',
    )
    submitted_by_id = fields.Many2one('res.users', string='أُرسل بواسطة', readonly=True, copy=False)
    submitted_date = fields.Datetime(string='تاريخ الإرسال', readonly=True, copy=False)
    financial_approved_by_id = fields.Many2one('res.users', string='صدّقت المالية بواسطة', readonly=True, copy=False)
    financial_approved_date = fields.Datetime(string='تاريخ تصديق المالية', readonly=True, copy=False)
    paid_date = fields.Datetime(string='تاريخ الدفع', readonly=True, copy=False)
    started_by_id = fields.Many2one('res.users', string='بدأ التنفيذ بواسطة', readonly=True, copy=False)
    started_date = fields.Datetime(string='تاريخ بدء التنفيذ', readonly=True, copy=False)
    completed_by_id = fields.Many2one('res.users', string='أُنجز بواسطة', readonly=True, copy=False)
    completed_date = fields.Datetime(string='تاريخ الإنجاز', readonly=True, copy=False)
    cancelled_by_id = fields.Many2one('res.users', string='أُلغي بواسطة', readonly=True, copy=False)
    cancelled_date = fields.Datetime(string='تاريخ الإلغاء', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'membership.service.request'
                ) or _('New')
            if vals.get('partner_id') and not vals.get('company_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                vals['company_id'] = partner.company_id.id or self.env.company.id
        requests = super().create(vals_list)
        requests._set_membership_period()
        return requests

    def _is_service_manager(self):
        return self.env.user.has_group('membership_management.group_membership_service_manager')

    def _check_manual_write_permissions(self, vals):
        if self.env.context.get('membership_service_workflow_write') or self._is_service_manager():
            return

        vals_keys = set(vals)
        note_fields = {
            'request_notes',
            'finance_notes',
            'cashier_notes',
            'service_notes',
            'cancel_reason',
        }
        workflow_fields = {
            'state',
            'invoice_id',
            'submitted_by_id',
            'submitted_date',
            'financial_approved_by_id',
            'financial_approved_date',
            'paid_date',
            'started_by_id',
            'started_date',
            'completed_by_id',
            'completed_date',
            'cancelled_by_id',
            'cancelled_date',
        }

        if vals_keys & workflow_fields:
            raise AccessError(_('لا يمكن تعديل مرحلة سير العمل أو حقول التدقيق يدويًا. استخدم أزرار سير العمل.'))

        if 'request_notes' in vals_keys and not self.env.user.has_group('membership_management.group_membership_service_registration'):
            raise AccessError(_('ملاحظات الذاتية يكتبها مستخدمو قسم الذاتية فقط.'))
        if 'finance_notes' in vals_keys and not self.env.user.has_group('membership_management.group_membership_service_finance'):
            raise AccessError(_('ملاحظات المالية يكتبها مستخدمو المالية فقط.'))
        if 'cashier_notes' in vals_keys and not self.env.user.has_group('membership_management.group_membership_service_cashier'):
            raise AccessError(_('ملاحظات الصندوق يكتبها مستخدمو الصندوق فقط.'))
        if 'service_notes' in vals_keys and not self.env.user.has_group('membership_management.group_membership_service_registration'):
            raise AccessError(_('ملاحظات تنفيذ الخدمة يكتبها مستخدمو قسم الذاتية فقط.'))
        if 'cancel_reason' in vals_keys and not self.env.user.has_group('membership_management.group_membership_service_finance'):
            raise AccessError(_('سبب الرفض يكتبه مستخدمو المالية فقط، وسبب الإلغاء يكتبه المدير عند الإلغاء.'))

        for rec in self:
            if 'request_notes' in vals_keys and rec.state not in ('draft', 'waiting_financial_approval'):
                raise AccessError(_('ملاحظات الذاتية تعدّل قبل إرسال الطلب أو أثناء انتظار تصديق المالية فقط.'))
            if 'finance_notes' in vals_keys and rec.state != 'waiting_financial_approval':
                raise AccessError(_('ملاحظات المالية تعدّل أثناء انتظار تصديق المالية فقط.'))
            if 'cashier_notes' in vals_keys and rec.state not in ('waiting_payment', 'paid'):
                raise AccessError(_('ملاحظات الصندوق تعدّل أثناء انتظار الدفع أو بعد الدفع فقط.'))
            if 'service_notes' in vals_keys and rec.state not in ('paid', 'in_progress'):
                raise AccessError(_('ملاحظات تنفيذ الخدمة تعدّل أثناء بدء التنفيذ أو أثناء التنفيذ فقط.'))
            if 'cancel_reason' in vals_keys and rec.state != 'waiting_financial_approval':
                raise AccessError(_('سبب الرفض يكتب أثناء انتظار تصديق المالية فقط.'))

        if self.env.user.has_group('membership_management.group_membership_service_cashier'):
            forbidden = vals_keys - {'cashier_notes'}
            if forbidden:
                raise AccessError(_('الصندوق يستطيع تعديل ملاحظات الصندوق فقط.'))

        non_note_fields = vals_keys - note_fields
        if non_note_fields and not self.env.user.has_group('membership_management.group_membership_service_registration'):
            raise AccessError(_('لا يمكن تعديل بيانات الطلب الأساسية إلا من قبل قسم الذاتية أو المدير.'))

    def _workflow_write(self, vals):
        return self.with_context(membership_service_workflow_write=True).write(vals)

    def write(self, vals):
        self._check_manual_write_permissions(vals)
        res = super().write(vals)
        if 'partner_id' in vals:
            self._set_membership_period()
        return res

    def _post_workflow_message(self, body):
        self.message_post(body=body)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            if rec.partner_id:
                rec.company_id = rec.partner_id.company_id or rec.env.company
                rec.membership_period_id = rec.partner_id.active_membership_id

    def _set_membership_period(self):
        for rec in self:
            if rec.partner_id and rec.partner_id.active_membership_id:
                rec.membership_period_id = rec.partner_id.active_membership_id.id
            else:
                rec.membership_period_id = False

    @api.constrains('company_id', 'partner_id', 'service_type_id', 'membership_period_id')
    def _check_company_consistency(self):
        for rec in self:
            if rec.partner_id.company_id and rec.partner_id.company_id != rec.company_id:
                raise ValidationError(_('يجب أن تطابق شركة الطبيب شركة الطلب.'))
            if rec.service_type_id and rec.service_type_id.company_id != rec.company_id:
                raise ValidationError(_('يجب أن تطابق شركة نوع الخدمة شركة الطلب.'))
            if rec.membership_period_id and rec.membership_period_id.company_id != rec.company_id:
                raise ValidationError(_('يجب أن تطابق شركة فترة العضوية شركة الطلب.'))

    def _validate_before_submit(self):
        for rec in self:
            service = rec.service_type_id
            if service.requires_active_membership and rec.partner_id.doctor_membership_state != 'active':
                raise UserError(_('هذه الخدمة تتطلب عضوية فعالة.'))
            if service.requires_attachments and not rec.attachment_ids:
                raise UserError(_('يرجى إرفاق المستندات المطلوبة قبل الإرسال.'))

    @api.depends(
        'company_id',
        'service_type_id',
        'service_type_id.requires_revenue_distribution',
        'service_type_id.product_id',
        'service_type_id.invoice_template_id',
        'service_type_id.invoice_template_id.line_ids.product_id',
    )
    def _compute_revenue_distribution_status(self):
        for rec in self:
            required = bool(rec.service_type_id.requires_revenue_distribution)
            ready = True
            message = _('هذه الخدمة لا تتطلب توزيع إيراد.')
            if required:
                ready, message = rec._check_revenue_distribution_ready()
            products = rec._get_service_revenue_distribution_products()
            rec.revenue_distribution_required = required
            rec.revenue_distribution_ready = ready
            rec.revenue_distribution_status_message = message
            rec.revenue_distribution_product_names = '\n'.join(products.mapped('display_name')) if products else _('لا توجد منتجات للفحص.')

    def _search_revenue_distribution_required(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_('عامل البحث غير مدعوم لحقل يتطلب توزيع إيراد.'))
        required_domain = [('service_type_id.requires_revenue_distribution', '=', True)]
        if (operator == '=' and value) or (operator == '!=' and not value):
            return required_domain
        return ['!', *required_domain]

    def _search_revenue_distribution_ready(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_('عامل البحث غير مدعوم لحقل جاهزية توزيع الإيراد.'))
        ready_ids = []
        requests = self.search([('service_type_id.requires_revenue_distribution', '=', True)])
        for request in requests:
            ready, _message = request._check_revenue_distribution_ready()
            if ready:
                ready_ids.append(request.id)
        ready_domain = [('id', 'in', ready_ids)]
        if (operator == '=' and value) or (operator == '!=' and not value):
            return ready_domain
        return ['!', *ready_domain]

    @api.depends(
        'partner_id',
        'company_id',
        'service_type_id',
        'service_type_id.product_id',
        'service_type_id.invoice_template_id',
        'service_type_id.invoice_template_id.line_ids.product_id',
        'service_type_id.invoice_template_id.line_ids.price_unit',
        'service_type_id.fee',
        'service_type_id.requires_active_membership',
        'service_type_id.requires_attachments',
        'service_type_id.requires_revenue_distribution',
        'service_type_id.generates_invoice',
        'attachment_ids',
        'invoice_id',
        'state',
    )
    def _compute_financial_validation(self):
        for rec in self:
            if rec.state in ('waiting_payment', 'paid', 'in_progress', 'completed') and rec.invoice_id:
                rec.financial_validation_ready = True
                rec.financial_validation_result = _('تم اعتماد المالية')
                rec.financial_validation_failure_message = False
                rec.financial_validation_html = rec._format_financial_validation_html(
                    _('تم اعتماد المالية'),
                    [],
                    [],
                )
                continue
            if rec.state == 'cancelled':
                rec.financial_validation_ready = False
                rec.financial_validation_result = _('ملغى')
                rec.financial_validation_failure_message = rec.cancel_reason or False
                rec.financial_validation_html = rec._format_financial_validation_html(
                    _('ملغى'),
                    [rec.cancel_reason] if rec.cancel_reason else [],
                    [],
                )
                continue
            result = rec._get_financial_validation_result()
            rec.financial_validation_ready = result['ready']
            rec.financial_validation_result = result['result_label']
            rec.financial_validation_failure_message = result['failure_message']
            rec.financial_validation_html = result['html']

    def _search_financial_validation_ready(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_('عامل البحث غير مدعوم لحقل جاهزية اعتماد المالية.'))
        ready_ids = []
        requests = self.search([('state', '=', 'waiting_financial_approval')])
        for request in requests:
            if request._get_financial_validation_result()['ready']:
                ready_ids.append(request.id)
        ready_domain = [('id', 'in', ready_ids)]
        if (operator == '=' and value) or (operator == '!=' and not value):
            return ready_domain
        return ['!', *ready_domain]

    def _format_financial_validation_html(self, result_label, errors, distribution_rows):
        result_class = 'alert-success' if not errors else 'alert-danger'
        parts = [
            '<div class="o_membership_financial_validation">',
            '<div class="alert %s" role="alert"><strong>%s</strong></div>' % (
                result_class,
                html_escape(result_label),
            ),
        ]

        parts.append('<h4>%s</h4>' % html_escape(_('توزيع الإيراد')))
        if distribution_rows:
            parts.append('<div style="display: flex; flex-direction: column; gap: 8px; min-width: 360px;">')
            for row in distribution_rows:
                parts.append(
                    '<div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; '
                    'padding: 10px 12px; border: 1px solid #d8dadd; border-radius: 6px; background: #fff;">'
                    '<div style="min-width: 0;">'
                    '<div style="font-weight: 600; white-space: normal; overflow-wrap: break-word;">%s</div>'
                    '<div style="font-size: 12px; color: #6b7280; white-space: normal; overflow-wrap: break-word;">%s</div>'
                    '</div>'
                    '<div style="flex: 0 0 auto; font-weight: 700; font-size: 16px; direction: ltr; white-space: nowrap;">%s%%</div>'
                    '</div>' % (
                        html_escape(row['fund_box']),
                        html_escape(row['product']),
                        html_escape('%.2f' % row['percentage']),
                    )
                )
            parts.append('</div>')
        else:
            parts.append('<p class="text-muted">%s</p>' % html_escape(_('لا توجد صناديق توزيع لعرضها.')))
        parts.append('</div>')
        return ''.join(parts)

    def _format_financial_validation_html(self, result_label, errors, distribution_rows):
        result_class = 'alert-success' if not errors else 'alert-danger'
        parts = [
            '<div class="o_membership_financial_validation">',
            '<div class="alert %s" role="alert"><strong>%s</strong></div>' % (
                result_class,
                html_escape(result_label),
            ),
        ]
        if errors:
            parts.append(
                '<div class="alert alert-warning" role="alert"><strong>%s</strong>'
                '<ul style="margin: 8px 0 0 0;">' % html_escape(_('أسباب عدم الجاهزية'))
            )
            for error in errors:
                parts.append('<li>%s</li>' % html_escape(error))
            parts.append('</ul></div>')

        parts.append('<h4>%s</h4>' % html_escape(_('تحليل توزيع الإيراد')))
        if distribution_rows:
            parts.append('<div style="display: flex; flex-direction: column; gap: 8px; min-width: 360px;">')
            for row in distribution_rows:
                parts.append(
                    '<div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; '
                    'padding: 10px 12px; border: 1px solid #d8dadd; border-radius: 6px; background: #fff;">'
                    '<div style="min-width: 0;">'
                    '<div style="font-weight: 600; white-space: normal; overflow-wrap: break-word;">%s</div>'
                    '<div style="font-size: 12px; color: #6b7280; white-space: normal; overflow-wrap: break-word;">%s</div>'
                    '</div>'
                    '<div style="display: flex; gap: 18px; flex: 0 0 auto; align-items: center; direction: ltr; white-space: nowrap;">'
                    '<span style="font-weight: 700; font-size: 16px;">%s%%</span>'
                    '<span style="font-weight: 700; font-size: 16px;">%s</span>'
                    '</div>'
                    '</div>' % (
                        html_escape(row['fund_box']),
                        html_escape(row['product']),
                        html_escape('%.2f' % row['percentage']),
                        html_escape(row.get('expected_amount_label') or ''),
                    )
                )
            parts.append('</div>')
        else:
            parts.append('<p class="text-muted">%s</p>' % html_escape(_('لا توجد صناديق توزيع لعرضها.')))
        parts.append('</div>')
        return ''.join(parts)

    def _get_financial_validation_result(self):
        self.ensure_one()
        sections = [
            {'title': _('التحقق من بيانات الطلب'), 'checks': []},
            {'title': _('تحليل توزيع الإيراد'), 'checks': []},
            {'title': _('التحقق من جاهزية الفاتورة'), 'checks': []},
        ]
        errors = []
        distribution_rows = []

        def add(section_index, label, ok, success_message, failure_message, required=True):
            message = success_message if ok else failure_message
            sections[section_index]['checks'].append({
                'label': label,
                'ok': bool(ok),
                'message': message,
            })
            if required and not ok:
                errors.append(failure_message)

        service = self.service_type_id
        partner = self.partner_id
        company = self.company_id
        products = self._get_service_revenue_distribution_products()
        currency = self.currency_id or company.currency_id
        product_amounts = {}
        if service and service.invoice_template_id:
            for template_line in service.invoice_template_id.line_ids:
                if template_line.product_id:
                    product_amounts[template_line.product_id.id] = product_amounts.get(template_line.product_id.id, 0.0) + (
                        template_line.quantity * template_line.price_unit
                    )
        elif service and service.product_id:
            product_amounts[service.product_id.id] = self.fee or 0.0

        add(0, _('الطبيب موجود'), bool(partner), _('تم تحديد الطبيب.'), _('لا يوجد طبيب مرتبط بالطلب.'))
        add(0, _('نوع الخدمة موجود'), bool(service), _('تم تحديد نوع الخدمة.'), _('لا يوجد نوع خدمة مرتبط بالطلب.'))
        add(0, _('الشركة موجودة'), bool(company), _('تم تحديد الشركة.'), _('لا توجد شركة مرتبطة بالطلب.'))
        add(0, _('الرسم أكبر من صفر'), bool(service and self.fee > 0), _('الرسم مضبوط بقيمة أكبر من صفر.'), _('رسم الخدمة يجب أن يكون أكبر من صفر.'))

        has_product_or_template = bool(service and (service.product_id or service.invoice_template_id))
        add(
            0,
            _('المنتج المحاسبي موجود أو قالب الفاتورة موجود'),
            has_product_or_template,
            _('يوجد منتج محاسبي أو قالب فاتورة.'),
            _('لا يوجد منتج محاسبي أو قالب فاتورة لنوع الخدمة.'),
        )

        active_membership_ok = not service.requires_active_membership or partner.doctor_membership_state == 'active'
        add(
            0,
            _('العضوية فعالة إذا كانت الخدمة تتطلب عضوية فعالة'),
            active_membership_ok,
            _('شرط العضوية الفعالة محقق.'),
            _('هذه الخدمة تتطلب عضوية فعالة للطبيب.'),
        )

        attachments_ok = not service.requires_attachments or bool(self.attachment_ids)
        add(
            0,
            _('المرفقات موجودة إذا كانت الخدمة تتطلب مرفقات'),
            attachments_ok,
            _('شرط المرفقات محقق.'),
            _('الخدمة تتطلب مرفقات ولم يتم رفع أي مرفق.'),
        )

        distribution_required = bool(service.requires_revenue_distribution)
        add(
            1,
            _('هل الخدمة تتطلب توزيع إيراد'),
            distribution_required,
            _('الخدمة تتطلب توزيع إيراد.'),
            _('الخدمة لا تتطلب توزيع إيراد.'),
            required=False,
        )
        product_names = '، '.join(products.mapped('display_name')) if products else _('لا توجد منتجات للفحص.')
        add(
            1,
            _('المنتجات التي تم فحصها'),
            bool(products),
            product_names,
            _('لا توجد منتجات للفحص.'),
            required=False,
        )

        if distribution_required:
            add(1, _('توجد منتجات للفحص'), bool(products), _('تم العثور على منتجات الخدمة.'), _('لا توجد منتجات محاسبية مرتبطة بنوع الخدمة أو قالب الفاتورة.'))
            for product in products:
                template = product.product_tmpl_id
                product_label = product.display_name
                add(
                    1,
                    _('المنتج مفعل للتوزيع: %s') % product_label,
                    bool(template.enable_revenue_distribution),
                    _('المنتج مفعل لتوزيع الإيراد.'),
                    _('المنتج "%s" غير مفعّل عليه توزيع الإيراد.') % product_label,
                )
                company_lines = template.distribution_line_ids.filtered(lambda line: line.company_id == company)
                add(
                    1,
                    _('توجد قواعد توزيع لنفس الشركة: %s') % product_label,
                    bool(company_lines),
                    _('توجد قواعد توزيع لنفس شركة الطلب.'),
                    _('لا توجد قواعد توزيع للمنتج "%s" ضمن شركة الطلب.') % product_label,
                )
                if company_lines:
                    total = sum(company_lines.mapped('percentage'))
                    add(
                        1,
                        _('مجموع النسب يساوي 100%%: %s') % product_label,
                        abs(total - 100.0) <= 0.0001,
                        _('مجموع نسب التوزيع يساوي 100%.'),
                        _('مجموع نسب التوزيع للمنتج "%(product)s" يساوي %(total).4f%% وليس 100%%.') % {
                            'product': product_label,
                            'total': total,
                        },
                    )
                    for line in company_lines:
                        fund = line.fund_box_id
                        fund_label = fund.display_name if fund else _('بدون صندوق')
                        expected_amount = product_amounts.get(product.id, self.fee or 0.0) * line.percentage / 100.0
                        distribution_rows.append({
                            'product': product_label,
                            'fund_box': fund_label,
                            'percentage': line.percentage,
                            'expected_amount_label': '%.2f %s' % (expected_amount, currency.symbol or currency.name),
                        })
                        add(1, _('الصندوق فعال: %s') % fund_label, bool(fund and fund.active), _('الصندوق فعال.'), _('الصندوق "%s" غير فعال.') % fund_label)
                        add(1, _('الصندوق تابع لنفس الشركة: %s') % fund_label, bool(fund and fund.company_id == company), _('الصندوق تابع لنفس شركة الطلب.'), _('الصندوق "%s" لا يتبع شركة الطلب.') % fund_label)
                        add(1, _('حساب الإيراد موجود للصندوق: %s') % fund_label, bool(fund and fund.income_account_id), _('حساب الإيراد موجود.'), _('الصندوق "%s" لا يحتوي على حساب إيراد.') % fund_label)
                        analytic = fund.analytic_account_id if fund else False
                        analytic_ok = not analytic or not analytic.company_id or analytic.company_id == company
                        add(1, _('الحساب التحليلي متوافق: %s') % fund_label, analytic_ok, _('الحساب التحليلي متوافق.'), _('الحساب التحليلي للصندوق "%s" يجب أن يكون لنفس شركة الطلب أو بدون شركة.') % fund_label)
        else:
            add(1, _('تحليل قواعد التوزيع'), True, _('لا يلزم فحص قواعد التوزيع لهذه الخدمة.'), _('لا يلزم فحص قواعد التوزيع لهذه الخدمة.'), required=False)

        invoice_can_be_created = bool(service and service.generates_invoice)
        add(2, _('يمكن إنشاء الفاتورة'), invoice_can_be_created, _('نوع الخدمة مضبوط لإنشاء فاتورة.'), _('نوع الخدمة لا ينشئ فاتورة محاسبية.'))
        add(2, _('لا توجد فاتورة سابقة لنفس الطلب'), not bool(self.invoice_id), _('لا توجد فاتورة مرتبطة مسبقاً.'), _('توجد فاتورة مرتبطة سابقاً بهذا الطلب.'))
        add(2, _('المنتجات صالحة'), bool(products), _('منتجات الفاتورة محددة.'), _('لا توجد منتجات صالحة لإنشاء الفاتورة.'))

        if service.invoice_template_id:
            template_lines = service.invoice_template_id.line_ids
            total_price = sum(line.quantity * line.price_unit for line in template_lines)
            price_ok = bool(template_lines) and total_price > 0
            add(2, _('السعر / الرسم صحيح'), price_ok, _('قالب الفاتورة يحتوي على قيمة أكبر من صفر.'), _('قالب الفاتورة لا يحتوي على قيمة فوترة أكبر من صفر.'))
        else:
            add(2, _('السعر / الرسم صحيح'), bool(self.fee > 0), _('الرسم مضبوط بقيمة صحيحة.'), _('السعر أو الرسم يجب أن يكون أكبر من صفر.'))

        product_company_ok = True
        for product in products:
            if product.company_id and product.company_id != company:
                product_company_ok = False
                break
        template_company_ok = not service.invoice_template_id or service.invoice_template_id.company_id == company
        add(
            2,
            _('الشركة متوافقة'),
            bool(product_company_ok and template_company_ok),
            _('شركة المنتجات وقالب الفاتورة متوافقة مع شركة الطلب.'),
            _('يوجد منتج أو قالب فاتورة تابع لشركة مختلفة عن شركة الطلب.'),
        )
        partner_invoice_ok = bool(partner and partner.active and (not partner.company_id or partner.company_id == company))
        add(
            2,
            _('الشريك/الطبيب قابل للفوترة'),
            partner_invoice_ok,
            _('الشريك قابل للفوترة ضمن شركة الطلب.'),
            _('الشريك/الطبيب غير قابل للفوترة ضمن شركة الطلب.'),
        )

        ready = not errors
        result_label = _('جاهز لاعتماد المالية') if ready else _('غير جاهز لاعتماد المالية')
        failure_message = '\n'.join(errors)
        return {
            'ready': ready,
            'result_label': result_label,
            'errors': errors,
            'failure_message': failure_message,
            'sections': sections,
            'html': self._format_financial_validation_html(result_label, errors, distribution_rows),
        }

    def _check_financial_validation_ready(self):
        for rec in self:
            result = rec._get_financial_validation_result()
            if not result['ready']:
                raise UserError(_('لا يمكن تصديق المالية لأن الطلب غير جاهز:\n- %s') % '\n- '.join(result['errors']))
        return True

    def _get_service_revenue_distribution_products(self):
        self.ensure_one()
        if not self.service_type_id:
            return self.env['product.product']
        return self.service_type_id._get_revenue_distribution_products()

    def _check_revenue_distribution_ready(self, raise_exception=False):
        self.ensure_one()
        if not self.service_type_id.requires_revenue_distribution:
            return True, _('هذه الخدمة لا تتطلب توزيع إيراد.')

        company = self.company_id
        products = self._get_service_revenue_distribution_products()
        errors = []
        if not products:
            errors.append(_('لا توجد منتجات محاسبية مرتبطة بنوع الخدمة أو قالب الفاتورة.'))

        for product in products:
            template = product.product_tmpl_id
            product_name = product.display_name
            if not template.enable_revenue_distribution:
                errors.append(_('المنتج "%s" غير مفعّل عليه توزيع الإيراد.') % product_name)
                continue

            company_lines = template.distribution_line_ids.filtered(lambda line: line.company_id == company)
            if not company_lines:
                errors.append(_('لا توجد أسطر توزيع إيراد للمنتج "%(product)s" ضمن شركة "%(company)s".') % {
                    'product': product_name,
                    'company': company.display_name,
                })
                continue

            total = sum(company_lines.mapped('percentage'))
            if abs(total - 100.0) > 0.0001:
                errors.append(_('مجموع نسب توزيع الإيراد للمنتج "%(product)s" في شركة "%(company)s" يساوي %(total).4f%% ويجب أن يساوي 100%%.') % {
                    'product': product_name,
                    'company': company.display_name,
                    'total': total,
                })

            for line in company_lines:
                fund = line.fund_box_id
                if not fund:
                    errors.append(_('يوجد سطر توزيع للمنتج "%s" بدون صندوق.') % product_name)
                    continue
                if not fund.active:
                    errors.append(_('الصندوق "%s" غير فعّال.') % fund.display_name)
                if fund.company_id != company:
                    errors.append(_('الصندوق "%(fund)s" لا يتبع شركة الطلب "%(company)s".') % {
                        'fund': fund.display_name,
                        'company': company.display_name,
                    })
                if not fund.income_account_id:
                    errors.append(_('الصندوق "%s" لا يحتوي على حساب إيراد.') % fund.display_name)
                analytic = fund.analytic_account_id
                if analytic.company_id and analytic.company_id != company:
                    errors.append(_('الحساب التحليلي للصندوق "%(fund)s" يجب أن يكون لنفس شركة الطلب أو بدون شركة.') % {
                        'fund': fund.display_name,
                    })

        if errors:
            message = _('إعداد توزيع الإيراد غير جاهز:\n- %s') % '\n- '.join(errors)
            if raise_exception:
                raise UserError(message)
            return False, message
        return True, _('إعداد توزيع الإيراد جاهز لكل منتجات الخدمة.')

    def action_submit_to_finance(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('يمكن إرسال الطلبات المسودة فقط إلى المالية.'))
            rec._validate_before_submit()
            rec._workflow_write({
                'state': 'waiting_financial_approval',
                'submitted_by_id': self.env.user.id,
                'submitted_date': fields.Datetime.now(),
            })
            rec._post_workflow_message(_('تم إرسال الطلب إلى المالية بواسطة %s.') % self.env.user.display_name)
        return True

    def action_approve_financial_request(self):
        for rec in self:
            if rec.state != 'waiting_financial_approval':
                raise UserError(_('يمكن تصديق الطلبات المنتظرة لتصديق المالية فقط.'))
            vals = {
                'financial_approved_by_id': self.env.user.id,
                'financial_approved_date': fields.Datetime.now(),
            }
            rec._check_financial_validation_ready()
            if rec.service_type_id.generates_invoice:
                invoice = rec._create_and_post_invoice()
                rec._post_workflow_message(_('تم إنشاء وترحيل الفاتورة %(invoice)s لهذا الطلب.') % {
                    'invoice': invoice.name,
                })
                vals.update({
                    'invoice_id': invoice.id,
                    'state': 'waiting_payment',
                })
            else:
                vals.update({
                    'state': 'paid',
                    'paid_date': fields.Datetime.now(),
                })
            rec._workflow_write(vals)
            rec._post_workflow_message(_('تم تصديق الطلب ماليًا بواسطة %s.') % self.env.user.display_name)
        return True

    def action_reject_financial_request(self):
        for rec in self:
            if rec.state != 'waiting_financial_approval':
                raise UserError(_('يمكن رفض الطلبات المنتظرة لتصديق المالية فقط.'))
            if not rec.cancel_reason:
                raise UserError(_('سبب الرفض إلزامي قبل رفض الطلب.'))
            rec._workflow_write({
                'state': 'cancelled',
                'cancelled_by_id': self.env.user.id,
                'cancelled_date': fields.Datetime.now(),
            })
            rec._post_workflow_message(
                _('تم رفض الطلب من المالية بواسطة %(user)s. السبب: %(reason)s') % {
                    'user': self.env.user.display_name,
                    'reason': rec.cancel_reason,
                }
            )
        return True

    def _create_and_post_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_('توجد فاتورة مسبقًا لهذا الطلب.'))

        service = self.service_type_id
        invoice = self.env['account.move'].with_company(self.company_id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'invoice_origin': self.name,
            'membership_service_request_id': self.id,
        })

        if service.invoice_template_id:
            service.invoice_template_id.action_apply_to_invoice(invoice, replace_existing=True)
        else:
            if not service.product_id:
                raise UserError(_('يرجى ضبط المنتج المحاسبي لهذا النوع من الخدمات.'))
            product = service.product_id
            taxes = product.taxes_id.filtered(lambda tax: tax.company_id == self.company_id)
            invoice.write({
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': product.get_product_multiline_description_sale() or service.name,
                    'quantity': 1.0,
                    'price_unit': service.fee,
                    'tax_ids': [(6, 0, taxes.ids)],
                })],
            })

        invoice.action_post()
        return invoice

    def _mark_paid_from_invoice(self):
        for rec in self:
            if rec.state == 'waiting_payment':
                rec._workflow_write({
                    'state': 'paid',
                    'paid_date': fields.Datetime.now(),
                })
                rec._post_workflow_message(_('تم تحديث حالة الدفع إلى مدفوع بواسطة النظام.'))

    def _mark_waiting_payment_from_invoice(self):
        for rec in self:
            if rec.state == 'paid':
                rec._workflow_write({
                    'state': 'waiting_payment',
                    'paid_date': False,
                })
                rec._post_workflow_message(_('تم إرجاع حالة الدفع إلى بانتظار الدفع لأن الفاتورة لم تعد مدفوعة.'))

    def action_sync_payment_status(self):
        for rec in self:
            if not rec.invoice_id:
                raise UserError(_('لا توجد فاتورة مرتبطة بهذا الطلب.'))
            if rec.invoice_id.payment_state in ('paid', 'in_payment'):
                rec._mark_paid_from_invoice()
                continue
            raise UserError(_(
                'الفاتورة المرتبطة لم تُدفع بعد. حالة الدفع الحالية: %s'
            ) % (rec.invoice_id.payment_state or _('غير معروف')))
        return True

    def action_start_service(self):
        for rec in self:
            if rec.state != 'paid':
                raise UserError(_('يمكن بدء تنفيذ الطلبات المدفوعة فقط.'))
            rec._workflow_write({
                'state': 'in_progress',
                'started_by_id': self.env.user.id,
                'started_date': fields.Datetime.now(),
            })
            rec._post_workflow_message(_('بدأ تنفيذ الخدمة بواسطة %s.') % self.env.user.display_name)
        return True

    def action_complete_service(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_('يمكن إنهاء الطلبات قيد التنفيذ فقط.'))
            rec._workflow_write({
                'state': 'completed',
                'completed_by_id': self.env.user.id,
                'completed_date': fields.Datetime.now(),
            })
            rec._post_workflow_message(_('تم إنهاء الخدمة بواسطة %s.') % self.env.user.display_name)
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == 'completed':
                raise UserError(_('لا يمكن إلغاء الطلبات المنجزة.'))
            if not rec.cancel_reason:
                raise UserError(_('سبب الإلغاء إلزامي قبل إلغاء الطلب.'))
            rec._workflow_write({
                'state': 'cancelled',
                'cancelled_by_id': self.env.user.id,
                'cancelled_date': fields.Datetime.now(),
            })
            rec._post_workflow_message(
                _('تم إلغاء الطلب بواسطة %(user)s. السبب: %(reason)s') % {
                    'user': self.env.user.display_name,
                    'reason': rec.cancel_reason,
                }
            )
        return True

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('لا توجد فاتورة مرتبطة بهذا الطلب.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('فاتورة طلب خدمة طبيب'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_doctor_360(self):
        self.ensure_one()
        return self.env['membership.doctor.360'].action_open_for_doctor(self.partner_id)
