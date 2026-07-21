import re
import unicodedata
from difflib import SequenceMatcher

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


_ARABIC_TRANSLATION = str.maketrans({
    'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا',
    'ى': 'ي', 'ئ': 'ي', 'ؤ': 'و', 'ة': 'ه',
})


def normalize_identifier(value):
    """Normalize identifiers for comparison without changing stored values."""
    return re.sub(r'[^0-9A-Za-z\u0600-\u06ff]', '', value or '').casefold()


def normalize_phone(value):
    digits = re.sub(r'\D', '', value or '')
    # Compare local/mobile suffixes while tolerating country prefixes.
    return digits[-9:] if len(digits) > 9 else digits


def normalize_arabic_name(value):
    value = unicodedata.normalize('NFKD', value or '')
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    value = value.translate(_ARABIC_TRANSLATION).casefold()
    return ' '.join(re.findall(r'[0-9a-z\u0600-\u06ff]+', value))


class MembershipProfileMatchResult(models.Model):
    _name = 'membership.profile.match.result'
    _description = 'نتيجة مطابقة طبيب محتملة'
    _order = 'same_company desc, level_rank desc, id'

    request_id = fields.Many2one(
        'membership.profile.update', required=True, ondelete='cascade', index=True,
    )
    partner_id = fields.Many2one('res.partner', string='الطبيب', required=True, readonly=True)
    company_id = fields.Many2one(
        'res.company', related='partner_id.company_id', string='النقابة', store=True,
        readonly=True,
    )
    same_company = fields.Boolean(string='من النقابة نفسها', readonly=True)
    cross_company_warning = fields.Boolean(string='تحذير شركة أخرى', readonly=True)
    doctor_name = fields.Char(string='اسم الطبيب الكامل', readonly=True)
    mother_full_name = fields.Char(string='اسم الأم مع الكنية', readonly=True)
    masked_national_id = fields.Char(string='الرقم الوطني', readonly=True)
    medical_license_no = fields.Char(string='رقم الترخيص', readonly=True)
    membership_number = fields.Char(string='رقم العضوية', readonly=True)
    phone = fields.Char(string='الهاتف', readonly=True)
    reason = fields.Char(string='سبب اقتراح التطابق', readonly=True)
    level = fields.Selection([
        ('strong', 'قوي'), ('medium', 'متوسط'), ('weak', 'ضعيف'),
    ], string='مستوى التطابق', required=True, readonly=True)
    level_rank = fields.Integer(readonly=True)
    national_id_match = fields.Boolean(readonly=True)
    decision = fields.Selection([
        ('pending', 'بانتظار القرار'),
        ('selected', 'تم اختيار الطبيب'),
        ('different', 'ليس الطبيب نفسه'),
    ], default='pending', required=True, string='القرار')
    different_reason = fields.Char(string='سبب اختلاف الشخص')

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('profile_match_search'):
            raise AccessError(_('نتائج المطابقة تُنشأ فقط بواسطة عملية البحث.'))
        return super().create(vals_list)

    def write(self, vals):
        if (
            not self.env.context.get('profile_match_search')
            and not set(vals).issubset({'decision', 'different_reason'})
        ):
            raise AccessError(_('لا يمكن تعديل بيانات نتيجة المطابقة الفنية.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get('profile_match_search'):
            raise AccessError(_('نتائج المطابقة تُحذف فقط عند إعادة تشغيل البحث.'))
        return super().unlink()

    @api.constrains('decision', 'different_reason')
    def _check_different_reason(self):
        for rec in self:
            if rec.decision == 'different' and not (rec.different_reason or '').strip():
                raise ValidationError(_('يجب تسجيل سبب مختصر لاعتبار الشخص مختلفًا.'))

    def action_select_partner(self):
        self.ensure_one()
        request = self.request_id
        if not request._is_employee():
            raise AccessError(_('فقط موظف جمع بيانات الأطباء يمكنه اختيار الطبيب.'))
        if request.state not in request._EDITABLE_STATES:
            raise UserError(_('يمكن اختيار الطبيب فقط عندما يكون الطلب قابلًا للتحرير.'))
        if not self.same_company:
            raise UserError(_('لا يمكن ربط الطلب بطبيب من نقابة أخرى.'))
        request.write({
            'request_type': 'update_existing',
            'partner_id': self.partner_id.id,
        })
        request._sync_match_selection(preferred_result=self)
        request._refresh_match_summary()
        return True

    def action_mark_different(self):
        self.ensure_one()
        if not (self.request_id._is_employee() or self.request_id._is_reviewer()):
            raise AccessError(_('ليس لديك صلاحية مراجعة نتيجة المطابقة.'))
        if not (self.different_reason or '').strip():
            raise UserError(_('أدخل سببًا مختصرًا قبل تأكيد أن الطبيب ليس الشخص نفسه.'))
        self.decision = 'different'
        self.request_id._refresh_match_summary()
        return True

    @api.model
    def _name_similarity(self, left, right):
        left = normalize_arabic_name(left)
        right = normalize_arabic_name(right)
        if not left or not right:
            return 0.0
        if left == right:
            return 1.0
        return SequenceMatcher(None, left, right).ratio()
