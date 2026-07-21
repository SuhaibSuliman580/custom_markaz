import hashlib

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

from .membership_profile_match_result import (
    normalize_arabic_name, normalize_identifier, normalize_phone,
)


class MembershipProfileUpdate(models.Model):
    _name = 'membership.profile.update'
    _description = 'طلب جمع بيانات طبيب'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _check_company_auto = True

    _EMPLOYEE_GROUP = 'membership_management.group_doctor_data_employee'
    _REVIEWER_GROUP = 'membership_management.group_doctor_data_reviewer'
    _MANAGER_GROUP = 'membership_management.group_membership_admin'
    _EXECUTOR_GROUP = 'membership_management.group_doctor_data_executor'
    _EDITABLE_STATES = ('draft', 'returned')
    _LOCKED_STATES = ('approved', 'cancelled')
    _WORKFLOW_TOKEN = object()
    _EXECUTION_TOKEN = object()
    _WORKFLOW_FIELDS = {
        'state',
        'submitted_by_id',
        'submitted_date',
        'reviewer_id',
        'reviewed_date',
        'return_reason',
        'cancellation_reason',
    }

    name = fields.Char(
        string='المرجع',
        required=True,
        readonly=True,
        default=lambda self: _('New'),
        copy=False,
    )
    request_type = fields.Selection([
        ('update_existing', 'استكمال بيانات طبيب موجود'),
        ('onboard_existing_member', 'إدخال عضو قائم'),
    ], string='نوع الطلب', required=True, default='update_existing',
       tracking=True, copy=False)
    source = fields.Selection([
        ('manual_profile_completion', 'استكمال يدوي لملف طبيب'),
        ('manual_existing_member_onboarding', 'إدخال يدوي لعضو قائم'),
    ], string='مصدر الطلب', required=True, default='manual_profile_completion',
       readonly=True, tracking=True, copy=False)
    partner_id = fields.Many2one(
        'res.partner',
        string='الطبيب',
        domain=[('is_doctor', '=', True)],
        tracking=True,
        check_company=True,
    )
    doctor_display_name = fields.Char(
        string='الطبيب',
        compute='_compute_doctor_display_name',
    )
    company_id = fields.Many2one(
        'res.company',
        string='النقابة',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('waiting_documents', 'بانتظار الوثائق'),
        ('waiting_review', 'بانتظار المراجعة'),
        ('returned', 'معاد للتصحيح'),
        ('approved', 'تمت الموافقة'),
        ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, tracking=True, copy=False)

    # Kept for backward compatibility. Profile collection must never use it to
    # modify the doctor's operational membership state.
    previous_membership_state = fields.Selection([
        ('none', 'No Membership'),
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ], string='حالة العضوية السابقة', readonly=True, copy=False)

    officer_notes = fields.Text(string='ملاحظات موظف الذاتية')
    submitted_by_id = fields.Many2one(
        'res.users', string='أرسله', readonly=True, copy=False,
    )
    submitted_date = fields.Datetime(
        string='تاريخ الإرسال', readonly=True, copy=False,
    )
    reviewer_id = fields.Many2one(
        'res.users', string='المراجع', readonly=True, copy=False,
    )
    reviewed_date = fields.Datetime(
        string='تاريخ المراجعة', readonly=True, copy=False,
    )
    return_reason = fields.Text(string='سبب الإعادة', copy=False)
    cancellation_reason = fields.Text(string='سبب الإلغاء', copy=False)
    reviewer_notes = fields.Text(string='ملاحظات المراجع', copy=False)

    historical_membership_number = fields.Char(
        string='رقم العضوية السابق', copy=False, tracking=True,
    )
    proposed_union_status = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['union_status']._description_selection(self.env),
        string='الوضع النقابي', tracking=True,
    )
    proposed_membership_join_date = fields.Date(
        string='تاريخ الانتساب الأصلي', tracking=True,
    )
    proposed_fees_paid_until_year = fields.Char(
        string='الرسوم مدفوعة حتى عام', tracking=True,
    )
    proposed_membership_state = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['doctor_membership_state']._description_selection(self.env),
        string='حالة العضوية',
    )
    proposed_membership_start_date = fields.Date(string='تاريخ بدء العضوية')
    proposed_membership_end_date = fields.Date(string='تاريخ نهاية العضوية')
    proposed_active_membership_id = fields.Many2one(
        'membership.period', string='العضوية النشطة', check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    proposed_membership_rejoin_date = fields.Date(string='تاريخ إعادة الانضمام')
    proposed_membership_rejoin_decision = fields.Char(string='رقم قرار إعادة الانضمام')
    proposed_deletion_number = fields.Char(string='رقم الشطب')
    proposed_branch_return_date = fields.Date(string='تاريخ عودة الفرع')
    proposed_deletion_date = fields.Date(string='تاريخ الشطب')
    proposed_fund_status = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['fund_status']._description_selection(self.env),
        string='الوضع بالنسبة للصندوق',
    )
    proposed_bank_name = fields.Char(string='اسم البنك')
    proposed_bank_account_number = fields.Char(string='رقم الحساب البنكي')
    proposed_outside_country = fields.Boolean(string='خارج القطر')
    proposed_social_security_registered = fields.Boolean(string='مسجل لدى الضمان الاجتماعي')
    proposed_retirement_date = fields.Date(string='تاريخ التقاعد')
    proposed_retirement_decision_number = fields.Char(string='رقم قرار التقاعد')
    proposed_retirement_salary = fields.Float(string='الراتب التقاعدي')
    proposed_death_date = fields.Date(string='تاريخ الوفاة')
    proposed_death_decision_number = fields.Char(string='رقم قرار الوفاة')
    membership_evidence_attachment_ids = fields.Many2many(
        'ir.attachment',
        'membership_profile_update_evidence_rel',
        'request_id',
        'attachment_id',
        string='مستندات إثبات العضوية',
        copy=False,
    )
    national_id_exception_reason = fields.Text(
        string='سبب عدم توفر الرقم الوطني',
    )
    proposed_national_id_unavailable = fields.Boolean(string='الرقم الوطني غير متوفر')

    # Phase 1 keeps the existing proposed fields but deliberately does not
    # write any of them to res.partner.
    full_name = fields.Char(string='الاسم الكامل', tracking=True)
    proposed_arabic_name = fields.Char(string='الاسم بالعربي')
    # Personal identifier: deliberately excluded from automatic chatter tracking.
    national_id = fields.Char(string='الرقم الوطني')
    phone = fields.Char(string='الجوال / الهاتف', tracking=True)
    email = fields.Char(string='البريد الإلكتروني', tracking=True)
    medical_license_no = fields.Char(
        string='رقم الترخيص الطبي', tracking=True,
    )
    proposed_mother_full_name = fields.Char(
        string='اسم الأم مع الكنية', copy=False,
    )
    match_search_state = fields.Selection([
        ('not_searched', 'لم يتم البحث'),
        ('no_match', 'لا يوجد تطابق محتمل'),
        ('potential', 'يوجد تطابق محتمل'),
        ('selected', 'تم اختيار طبيب موجود'),
        ('manual_review', 'يحتاج مراجعة يدوية'),
    ], string='نتيجة البحث', default='not_searched', required=True, copy=False,
       readonly=True)
    match_search_summary = fields.Char(
        string='ملخص نتيجة البحث', readonly=True, copy=False,
    )
    match_searched_at = fields.Datetime(readonly=True, copy=False)
    match_search_fingerprint = fields.Char(readonly=True, copy=False)
    match_result_ids = fields.One2many(
        'membership.profile.match.result', 'request_id',
        string='التطابقات المحتملة', copy=False, readonly=True,
    )
    medical_specialty_id = fields.Many2one(
        'medical.specialty',
        string='الاختصاص الطبي',
        tracking=True,
        check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    proposed_first_name = fields.Char(string='الاسم الأول')
    proposed_father_name = fields.Char(string='اسم الأب')
    proposed_grandfather_name = fields.Char(string='اسم الجد')
    proposed_nickname = fields.Char(string='الكنية')
    proposed_gender = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['gender']._description_selection(self.env),
        string='الجنس',
    )
    proposed_birth_date = fields.Date(string='تاريخ الميلاد')
    proposed_birth_place = fields.Char(string='مكان الولادة')
    proposed_marital_status = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['marital_status']._description_selection(self.env),
        string='الحالة الاجتماعية',
    )
    proposed_nationality_id = fields.Many2one('res.country', string='الجنسية')
    proposed_image_1920 = fields.Binary(string='الصورة الشخصية', attachment=True)
    proposed_secondary_phone = fields.Char(string='هاتف إضافي')
    proposed_state_id = fields.Many2one('res.country.state', string='المحافظة', domain="[('country_id', '=', proposed_country_id)]")
    proposed_city = fields.Char(string='المدينة / المنطقة')
    proposed_district = fields.Char(string='المنطقة')
    proposed_subdistrict = fields.Char(string='الناحية')
    proposed_village = fields.Char(string='القرية')
    proposed_residence = fields.Char(string='مكان الإقامة')
    proposed_registry_place_number = fields.Char(string='مكان ورقم القيد')
    proposed_military_service_start_date = fields.Date(string='تاريخ بدء الخدمة العسكرية')
    proposed_military_service_end_date = fields.Date(string='تاريخ نهاية الخدمة العسكرية')
    proposed_street = fields.Char(string='العنوان التفصيلي')
    proposed_street2 = fields.Char(string='تفاصيل عنوان إضافية')
    proposed_country_id = fields.Many2one('res.country', string='الدولة')
    proposed_license_issue_date = fields.Date(string='تاريخ إصدار الترخيص')
    proposed_license_expiry_date = fields.Date(string='تاريخ انتهاء الترخيص')
    proposed_license_type = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['license_type']._description_selection(self.env),
        string='نوع الترخيص',
    )
    proposed_license_issuer = fields.Char(string='جهة إصدار الترخيص')
    proposed_subspecialty_id = fields.Many2one(
        'medical.specialty', string='الاختصاص الفرعي', check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    proposed_workplace_name = fields.Char(string='جهة العمل')
    proposed_workplace_type = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['workplace_type']._description_selection(self.env),
        string='نوع مكان العمل',
    )
    proposed_clinic_address = fields.Char(string='مكان ممارسة العمل / عنوان العيادة')
    proposed_clinic_phone = fields.Char(string='هاتف العيادة')
    proposed_years_of_experience = fields.Integer(string='سنوات الخبرة')
    proposed_practice_type = fields.Char(string='نوع الممارسة')
    proposed_professional_capacity = fields.Char(string='الصفة المهنية')
    proposed_job_title = fields.Char(string='المسمى الوظيفي')
    proposed_practice_start_date = fields.Date(string='تاريخ بدء ممارسة المهنة')
    proposed_qualification = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['qualification']._description_selection(self.env),
        string='المؤهل العلمي',
    )
    proposed_university_id = fields.Many2one(
        'medical.unv', string='الجامعة', check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    proposed_graduation_year = fields.Char(string='سنة التخرج')
    proposed_faculty = fields.Char(string='الكلية')
    proposed_academic_degree = fields.Char(string='الدرجة العلمية')
    proposed_certificate_country_id = fields.Many2one('res.country', string='بلد صدور الشهادة')
    proposed_certificate_date = fields.Date(string='تاريخ الحصول على الشهادة')
    proposed_certificate_title = fields.Char(string='عنوان / نوع الشهادة')
    proposed_specialty_classification = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['specialty_classification']._description_selection(self.env),
        string='التصنيف',
    )
    proposed_certificate_issue_place = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['certificate_issue_place']._description_selection(self.env),
        string='مكان إصدار الشهادة',
    )
    proposed_certificate_modify_date = fields.Date(string='تاريخ تعديل الشهادة')
    proposed_certificate_modify_number = fields.Char(string='رقم شهادة التعديل')
    proposed_specialization_authority_1 = fields.Many2one('medical.specialty', string='جهة الاختصاص', check_company=True, domain="[('company_id', '=', company_id)]")
    proposed_specialization_authority_2 = fields.Many2one('medical.specialty', string='جهة الاختصاص 2', check_company=True, domain="[('company_id', '=', company_id)]")
    proposed_specialization_authority_3 = fields.Many2one('medical.specialty', string='جهة الاختصاص 3', check_company=True, domain="[('company_id', '=', company_id)]")
    proposed_ministry_registration_number = fields.Char(string='رقم تسجيل وزارة الصحة')
    proposed_ministry_registration_date = fields.Date(string='تاريخ التسجيل لدى وزارة الصحة')
    proposed_permanent_license_date_1 = fields.Date(string='تاريخ الترخيص الدائم 1')
    proposed_permanent_license_date_2 = fields.Date(string='تاريخ الترخيص الدائم 2')
    proposed_permanent_license_date_3 = fields.Date(string='تاريخ الترخيص الدائم 3')
    proposed_temporary_license_date_1 = fields.Date(string='تاريخ الترخيص المؤقت 1')
    proposed_temporary_license_date_2 = fields.Date(string='تاريخ الترخيص المؤقت 2')
    proposed_temporary_license_date_3 = fields.Date(string='تاريخ الترخيص المؤقت 3')
    proposed_permanent_specialty_date_2 = fields.Date(string='تاريخ الاختصاص الدائم 2')
    proposed_temporary_specialty_date = fields.Date(string='تاريخ الاختصاص المؤقت')
    proposed_temporary_specialty_date_2 = fields.Date(string='تاريخ الاختصاص المؤقت 2')
    proposed_specialty_date_2 = fields.Date(string='Specialty Date 2')
    proposed_specialty_date_3 = fields.Date(string='Specialty Date 3')
    proposed_is_employee = fields.Boolean(string='أنت موظف')
    proposed_transfer_from_entity = fields.Char(string='من جهة النقل')
    proposed_transfer_from_date = fields.Date(string='تاريخ النقل من')
    proposed_transfer_to_entity = fields.Char(string='إلى جهة النقل')
    proposed_transfer_to_date = fields.Date(string='تاريخ النقل إلى')
    proposed_specialty_date = fields.Date(string='تاريخ الحصول على الاختصاص')
    comparison_warning = fields.Char(string='تنبيه المقارنة', readonly=True, copy=False)
    comparison_line_ids = fields.One2many(
        'membership.profile.comparison', 'request_id', string='مقارنة البيانات',
        readonly=True, copy=False,
    )
    document_line_ids = fields.One2many(
        'membership.profile.document', 'request_id', string='الوثائق', copy=False,
    )
    execution_state = fields.Selection([
        ('pending', 'غير منفذ'), ('executed', 'تم التنفيذ'),
    ], string='حالة التنفيذ', default='pending', required=True, readonly=True, copy=False)
    execution_type = fields.Selection([
        ('create', 'إنشاء طبيب'), ('update', 'تحديث طبيب'),
    ], string='نوع التنفيذ', readonly=True, copy=False)
    executed_at = fields.Datetime(string='تاريخ التنفيذ', readonly=True, copy=False)
    executed_by_id = fields.Many2one('res.users', string='نفذه', readonly=True, copy=False)
    executed_partner_id = fields.Many2one('res.partner', string='الطبيب الناتج', readonly=True, copy=False, index=True)
    execution_audit_ids = fields.One2many(
        'membership.profile.execution.audit', 'request_id', string='أثر التنفيذ',
        readonly=True, copy=False,
    )

    PROFILE_FIELD_MAPPING = (
        ('full_name', 'name', 'الاسم الكامل'),
        ('proposed_arabic_name', 'arabic_name', 'الاسم بالعربي'),
        ('proposed_first_name', 'doctor_first_name', 'الاسم الأول'),
        ('proposed_father_name', 'father_name', 'اسم الأب'),
        ('proposed_grandfather_name', 'grandfather_name', 'اسم الجد'),
        ('proposed_nickname', 'nickname', 'الكنية'),
        ('proposed_mother_full_name', 'mother_name', 'اسم الأم مع الكنية'),
        ('proposed_gender', 'gender', 'الجنس'),
        ('proposed_birth_date', 'birth_date', 'تاريخ الميلاد'),
        ('proposed_birth_place', 'birth_place', 'مكان الولادة'),
        ('proposed_marital_status', 'marital_status', 'الحالة الاجتماعية'),
        ('national_id', 'national_id', 'الرقم الوطني'),
        ('proposed_national_id_unavailable', 'national_id_unavailable', 'الرقم الوطني غير متوفر'),
        ('national_id_exception_reason', 'national_id_unavailable_reason', 'سبب عدم توفر الرقم الوطني'),
        ('proposed_nationality_id', 'nationality_id', 'الجنسية'),
        ('proposed_image_1920', 'image_1920', 'الصورة الشخصية'),
        ('proposed_registry_place_number', 'registry_place_number', 'مكان ورقم القيد'),
        ('proposed_military_service_start_date', 'military_service_start_date', 'تاريخ بدء الخدمة العسكرية'),
        ('proposed_military_service_end_date', 'military_service_end_date', 'تاريخ نهاية الخدمة العسكرية'),
        ('phone', 'mobile', 'الهاتف الأساسي'),
        ('proposed_secondary_phone', 'phone', 'الهاتف الإضافي'),
        ('email', 'email', 'البريد الإلكتروني'),
        ('proposed_state_id', 'state_id', 'المحافظة'),
        ('proposed_city', 'city', 'المدينة / المنطقة'),
        ('proposed_district', 'doctor_district', 'المنطقة'),
        ('proposed_subdistrict', 'doctor_subdistrict', 'الناحية'),
        ('proposed_village', 'doctor_village', 'القرية'),
        ('proposed_residence', 'current_residence', 'مكان الإقامة'),
        ('proposed_street', 'street', 'العنوان التفصيلي'),
        ('proposed_street2', 'street2', 'تفاصيل العنوان'),
        ('proposed_country_id', 'country_id', 'الدولة'),
        ('medical_license_no', 'medical_license_no', 'رقم الترخيص الطبي'),
        ('proposed_license_issue_date', 'license_issue_date', 'تاريخ الترخيص'),
        ('proposed_license_expiry_date', 'license_expiry_date', 'انتهاء الترخيص'),
        ('proposed_license_type', 'license_type', 'نوع الترخيص'),
        ('proposed_license_issuer', 'license_issuer', 'جهة إصدار الترخيص'),
        ('historical_membership_number', 'membership_number', 'رقم العضوية السابق'),
        ('proposed_membership_join_date', 'membership_join_date', 'تاريخ الانتساب السابق'),
        ('proposed_union_status', 'union_status', 'الوضع النقابي'),
        ('proposed_fees_paid_until_year', 'fees_paid_until_year', 'الرسوم مدفوعة حتى عام'),
        ('proposed_membership_state', 'doctor_membership_state', 'حالة العضوية'),
        ('proposed_membership_start_date', 'membership_start_date', 'تاريخ بدء العضوية'),
        ('proposed_membership_end_date', 'membership_end_date', 'تاريخ نهاية العضوية'),
        ('proposed_active_membership_id', 'active_membership_id', 'العضوية النشطة'),
        ('proposed_membership_rejoin_date', 'membership_rejoin_date', 'تاريخ إعادة الانضمام'),
        ('proposed_membership_rejoin_decision', 'membership_rejoin_decision', 'رقم قرار إعادة الانضمام'),
        ('proposed_deletion_number', 'deletion_number', 'رقم الشطب'),
        ('proposed_branch_return_date', 'branch_return_date', 'تاريخ عودة الفرع'),
        ('proposed_deletion_date', 'deletion_date', 'تاريخ الشطب'),
        ('proposed_fund_status', 'fund_status', 'الوضع بالنسبة للصندوق'),
        ('proposed_bank_name', 'bank_name', 'اسم البنك'),
        ('proposed_bank_account_number', 'bank_account_number', 'رقم الحساب البنكي'),
        ('proposed_outside_country', 'outside_country', 'خارج القطر'),
        ('proposed_social_security_registered', 'social_security_registered', 'مسجل لدى الضمان الاجتماعي'),
        ('proposed_retirement_date', 'retirement_date', 'تاريخ التقاعد'),
        ('proposed_retirement_decision_number', 'retirement_decision_number', 'رقم قرار التقاعد'),
        ('proposed_retirement_salary', 'retirement_salary', 'الراتب التقاعدي'),
        ('proposed_death_date', 'death_date', 'تاريخ الوفاة'),
        ('proposed_death_decision_number', 'death_decision_number', 'رقم قرار الوفاة'),
        ('medical_specialty_id', 'medical_specialty_id', 'الاختصاص الطبي'),
        ('proposed_subspecialty_id', 'medical_subspecialty_id', 'الاختصاص الفرعي'),
        ('proposed_workplace_name', 'workplace_name', 'جهة العمل'),
        ('proposed_workplace_type', 'workplace_type', 'نوع مكان العمل'),
        ('proposed_clinic_address', 'clinic_address', 'مكان ممارسة العمل'),
        ('proposed_clinic_phone', 'clinic_phone', 'هاتف العيادة'),
        ('proposed_years_of_experience', 'years_of_experience', 'سنوات الخبرة'),
        ('proposed_practice_type', 'practice_type', 'نوع الممارسة'),
        ('proposed_professional_capacity', 'professional_capacity', 'الصفة المهنية'),
        ('proposed_job_title', 'doctor_job_title', 'المسمى الوظيفي'),
        ('proposed_practice_start_date', 'practice_start_date', 'تاريخ بدء ممارسة المهنة'),
        ('proposed_qualification', 'qualification', 'المؤهل العلمي'),
        ('proposed_university_id', 'university_id', 'الجامعة / المؤسسة'),
        ('proposed_graduation_year', 'graduation_year', 'سنة التخرج'),
        ('proposed_faculty', 'faculty_name', 'الكلية'),
        ('proposed_academic_degree', 'academic_degree', 'الدرجة العلمية'),
        ('proposed_certificate_country_id', 'certificate_country_id', 'بلد صدور الشهادة'),
        ('proposed_certificate_date', 'certificate_date', 'تاريخ الشهادة'),
        ('proposed_certificate_title', 'certificate_title', 'عنوان / نوع الشهادة'),
        ('proposed_specialty_classification', 'specialty_classification', 'التصنيف'),
        ('proposed_certificate_issue_place', 'certificate_issue_place', 'مكان إصدار الشهادة'),
        ('proposed_certificate_modify_date', 'certificate_modify_date', 'تاريخ تعديل الشهادة'),
        ('proposed_certificate_modify_number', 'certificate_modify_number', 'رقم شهادة التعديل'),
        ('proposed_specialization_authority_1', 'specialization_authority_1', 'جهة الاختصاص'),
        ('proposed_specialization_authority_2', 'specialization_authority_2', 'جهة الاختصاص 2'),
        ('proposed_specialization_authority_3', 'specialization_authority_3', 'جهة الاختصاص 3'),
        ('proposed_specialty_date', 'permanent_specialty_date', 'تاريخ الاختصاص'),
        ('proposed_ministry_registration_number', 'ministry_registration_number', 'رقم تسجيل وزارة الصحة'),
        ('proposed_ministry_registration_date', 'ministry_registration_date', 'تاريخ التسجيل لدى وزارة الصحة'),
        ('proposed_permanent_license_date_1', 'permanent_license_date_1', 'تاريخ الترخيص الدائم 1'),
        ('proposed_permanent_license_date_2', 'permanent_license_date_2', 'تاريخ الترخيص الدائم 2'),
        ('proposed_permanent_license_date_3', 'permanent_license_date_3', 'تاريخ الترخيص الدائم 3'),
        ('proposed_temporary_license_date_1', 'temporary_license_date_1', 'تاريخ الترخيص المؤقت 1'),
        ('proposed_temporary_license_date_2', 'temporary_license_date_2', 'تاريخ الترخيص المؤقت 2'),
        ('proposed_temporary_license_date_3', 'temporary_license_date_3', 'تاريخ الترخيص المؤقت 3'),
        ('proposed_permanent_specialty_date_2', 'permanent_specialty_date_2', 'تاريخ الاختصاص الدائم 2'),
        ('proposed_temporary_specialty_date', 'temporary_specialty_date', 'تاريخ الاختصاص المؤقت'),
        ('proposed_temporary_specialty_date_2', 'temporary_specialty_date_2', 'تاريخ الاختصاص المؤقت 2'),
        ('proposed_specialty_date_2', 'specialty_date_2', 'Specialty Date 2'),
        ('proposed_specialty_date_3', 'specialty_date_3', 'Specialty Date 3'),
        ('proposed_is_employee', 'is_employee', 'أنت موظف'),
        ('proposed_transfer_from_entity', 'transfer_from_entity', 'من جهة النقل'),
        ('proposed_transfer_from_date', 'transfer_from_date', 'تاريخ النقل من'),
        ('proposed_transfer_to_entity', 'transfer_to_entity', 'إلى جهة النقل'),
        ('proposed_transfer_to_date', 'transfer_to_date', 'تاريخ النقل إلى'),
    )

    _COMPARISON_FIELDS = PROFILE_FIELD_MAPPING
    _EXECUTION_MAPPING = PROFILE_FIELD_MAPPING

    @api.model
    def _source_for_request_type(self, request_type):
        return (
            'manual_existing_member_onboarding'
            if request_type == 'onboard_existing_member'
            else 'manual_profile_completion'
        )

    @api.onchange('request_type')
    def _onchange_request_type(self):
        for rec in self:
            rec.source = rec._source_for_request_type(rec.request_type)
            if rec.request_type == 'onboard_existing_member':
                rec.partner_id = False

    @api.depends('request_type', 'partner_id', 'partner_id.name', 'full_name')
    def _compute_doctor_display_name(self):
        for rec in self:
            if rec.request_type != 'update_existing' or not rec.partner_id:
                rec.doctor_display_name = False
                continue
            # The relation remains partner_id. The request's reviewed full-name
            # value is used for display because legacy partner names may contain
            # only an old numeric placeholder.
            rec.doctor_display_name = (
                rec.full_name or rec.partner_id.display_name
            )

    @api.onchange('partner_id')
    def _onchange_partner_current_data(self):
        for rec in self:
            if rec.request_type != 'update_existing' or not rec.partner_id:
                rec.comparison_line_ids = [(5, 0, 0)]
                continue
            rec._check_allowed_company(rec.partner_id.company_id)
            if rec.partner_id.company_id != rec.company_id:
                raise ValidationError(_(
                    'شركة الطبيب يجب أن تطابق شركة الطلب.'
                ))
            rec.comparison_line_ids = [
                (5, 0, 0),
                *((0, 0, vals) for vals in rec._prepare_comparison_line_values()),
            ]
            if rec._origin and rec._origin.partner_id != rec.partner_id:
                rec.comparison_warning = _(
                    'تم تغيير الطبيب؛ تعرض المقارنة القيم الحالية للطبيب الجديد.'
                )

    @api.model
    def _check_allowed_company(self, company):
        if not company or company not in self.env.companies:
            raise AccessError(_(
                'You can only create or edit doctor data requests for an allowed company.'
            ))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        prepared_vals_list = []
        for incoming_vals in vals_list:
            vals = dict(incoming_vals)
            request_type = vals.get('request_type') or 'update_existing'
            vals['request_type'] = request_type
            vals['source'] = self._source_for_request_type(request_type)
            vals['state'] = 'draft'
            vals.pop('submitted_by_id', None)
            vals.pop('submitted_date', None)
            vals.pop('reviewer_id', None)
            vals.pop('reviewed_date', None)

            partner = (
                self.env['res.partner'].browse(vals['partner_id']).exists()
                if vals.get('partner_id') else self.env['res.partner']
            )
            company = (
                self.env['res.company'].browse(vals['company_id']).exists()
                if vals.get('company_id') else partner.company_id or self.env.company
            )
            self._check_allowed_company(company)
            vals['company_id'] = company.id

            if request_type == 'update_existing':
                if not partner:
                    raise ValidationError(_(
                        'An existing doctor is required for a profile completion request.'
                    ))
                if partner.company_id and partner.company_id != company:
                    raise ValidationError(_(
                        'The request company must match the existing doctor company.'
                    ))
            elif request_type == 'onboard_existing_member':
                if partner:
                    raise ValidationError(_(
                        'An existing-member onboarding request must not select a doctor before approval.'
                    ))
            else:
                raise ValidationError(_('Unsupported doctor data request type.'))

            if vals.get('name', _('New')) == _('New'):
                vals['name'] = sequence.next_by_code(
                    'membership.profile.update'
                ) or _('New')
            prepared_vals_list.append(vals)
        records = super().create(prepared_vals_list)
        records._refresh_comparison_lines()
        records._bind_membership_evidence_attachments()
        return records

    def _bind_membership_evidence_attachments(self):
        """Bind newly uploaded evidence to its saved request for Odoo ACL checks."""
        for rec in self:
            attachments = rec.membership_evidence_attachment_ids.filtered(
                lambda attachment: (
                    attachment.res_model in (False, rec._name)
                    and not attachment.res_id
                )
            )
            if attachments:
                attachments.write({'res_model': rec._name, 'res_id': rec.id})

    def write(self, vals):
        vals = dict(vals)
        execution_write = (
            self.env.context.get('profile_execution_token') is self._EXECUTION_TOKEN
        )
        execution_fields = {
            'execution_state', 'execution_type', 'executed_at',
            'executed_by_id', 'executed_partner_id',
        }
        if not execution_write and set(vals) & execution_fields:
            raise AccessError(_('استخدم إجراء تنفيذ الطلب لتحديث بيانات التنفيذ.'))
        if 'reviewer_notes' in vals and not self._is_reviewer():
            raise AccessError(_('Only a doctor data reviewer can edit reviewer notes.'))
        workflow_write = (
            self.env.context.get('profile_update_workflow_token')
            is self._WORKFLOW_TOKEN
        )
        if not workflow_write and 'source' in vals and 'request_type' not in vals:
            raise AccessError(_('لا يمكن تعديل مصدر الطلب يدويًا.'))
        review_note_write = (
            not workflow_write
            and set(vals).issubset({
                'return_reason', 'cancellation_reason', 'reviewer_notes',
            })
            and self._is_reviewer()
        )
        if not workflow_write and set(vals) & self._WORKFLOW_FIELDS:
            if not review_note_write:
                raise AccessError(_('Use the workflow actions to change request status.'))

        for rec in self:
            if rec.execution_state == 'executed' and vals and not execution_write:
                raise AccessError(_('لا يمكن تعديل طلب تم تنفيذه على ملف الطبيب.'))
            if rec.state in self._LOCKED_STATES and vals and not execution_write:
                raise AccessError(_('Approved and cancelled requests cannot be modified.'))
            if (
                not workflow_write and not execution_write
                and not review_note_write
                and not (
                    self.env.user.has_group(self._EMPLOYEE_GROUP)
                    or self.env.user.has_group(self._MANAGER_GROUP)
                )
            ):
                raise AccessError(_('Only a doctor data employee can edit requests.'))
            if (
                not workflow_write and not execution_write
                and not review_note_write
                and rec.state not in self._EDITABLE_STATES
            ):
                raise AccessError(_(
                    'Only draft or returned requests can be edited by the data employee.'
                ))
            if review_note_write and rec.state != 'waiting_review':
                raise AccessError(_(
                    'Review notes can only be edited while the request is waiting for review.'
                ))
            if 'request_type' in vals and rec.state != 'draft':
                raise AccessError(_('لا يمكن تغيير نوع الطلب بعد مغادرة حالة المسودة.'))

            company = rec.company_id
            if vals.get('company_id'):
                company = self.env['res.company'].browse(vals['company_id']).exists()
                self._check_allowed_company(company)

            request_type = vals.get('request_type', rec.request_type)
            partner = rec.partner_id
            if 'partner_id' in vals:
                partner = (
                    self.env['res.partner'].browse(vals['partner_id']).exists()
                    if vals['partner_id'] else self.env['res.partner']
                )
            if (
                request_type == 'update_existing'
                and partner
                and ('partner_id' in vals or 'request_type' in vals)
            ):
                self._check_allowed_company(partner.company_id)
                if partner.company_id != company:
                    raise ValidationError(_(
                        'شركة الطبيب يجب أن تطابق شركة الطلب.'
                    ))

            if request_type == 'update_existing':
                if not partner:
                    raise ValidationError(_(
                        'An existing doctor is required for a profile completion request.'
                    ))
                if partner.company_id and partner.company_id != company:
                    raise ValidationError(_(
                        'The request company must match the existing doctor company.'
                    ))
            elif request_type == 'onboard_existing_member' and partner and not execution_write:
                raise ValidationError(_(
                    'An existing-member onboarding request cannot select a doctor in Phase 1.'
                ))

            if 'request_type' in vals:
                vals['source'] = self._source_for_request_type(request_type)
        old_partners = {rec.id: rec.partner_id for rec in self} if 'partner_id' in vals else {}
        records_to_sync = self if set(vals) & {'partner_id', 'request_type'} else self.browse()
        comparison_changed = bool(set(vals) & ({'partner_id'} | {item[0] for item in self._COMPARISON_FIELDS}))
        result = super().write(vals)
        if 'membership_evidence_attachment_ids' in vals:
            self._bind_membership_evidence_attachments()
        if records_to_sync and not execution_write:
            records_to_sync._sync_match_selection()
            records_to_sync._refresh_match_summary()
        if old_partners and not execution_write:
            for rec in self:
                if old_partners[rec.id] != rec.partner_id and any(rec[field] for field, _current, _label in self._COMPARISON_FIELDS):
                    rec.with_context(profile_comparison_refresh=True).write({
                        'comparison_warning': _('تم تغيير الطبيب؛ راجع أن البيانات المقترحة تخص الطبيب المحدد حاليًا.'),
                    })
        if comparison_changed and not execution_write and not self.env.context.get('profile_comparison_refresh'):
            self._refresh_comparison_lines()
        return result

    def _is_executor(self):
        return (
            self.env.user.has_group(self._EXECUTOR_GROUP)
            or self.env.user.has_group(self._MANAGER_GROUP)
        )

    def _execution_write(self, vals):
        return self.with_context(profile_execution_token=self._EXECUTION_TOKEN).write(vals)

    def _check_execution_references(self):
        for rec in self:
            rec._check_allowed_company(rec.company_id)
            for reference in (
                rec.medical_specialty_id,
                rec.proposed_subspecialty_id,
                rec.proposed_university_id,
                rec.proposed_specialization_authority_1,
                rec.proposed_specialization_authority_2,
                rec.proposed_specialization_authority_3,
            ):
                if reference and reference.company_id != rec.company_id:
                    raise UserError(_('توجد بيانات مرجعية لا تتبع نقابة الطلب.'))
            if (
                rec.proposed_active_membership_id
                and rec.proposed_active_membership_id.company_id != rec.company_id
            ):
                raise UserError(_('العضوية النشطة لا تتبع نقابة الطلب.'))

    def _strong_duplicate_candidates(self):
        self.ensure_one()
        allowed = self.env.user.company_ids
        candidates = self.env['res.partner'].with_context(
            allowed_company_ids=allowed.ids,
        ).search([('is_doctor', '=', True), ('company_id', 'in', allowed.ids)])
        return candidates.filtered(
            lambda partner: (
                (normalize_identifier(self.national_id) and
                 normalize_identifier(self.national_id) == normalize_identifier(partner.national_id))
                or (normalize_identifier(self.medical_license_no) and
                    normalize_identifier(self.medical_license_no) == normalize_identifier(partner.medical_license_no))
                or (partner.company_id == self.company_id and
                    normalize_identifier(self.historical_membership_number) and
                    normalize_identifier(self.historical_membership_number) == normalize_identifier(partner.membership_number))
            )
        )

    def _execution_partner_values(self, partner=None):
        self.ensure_one()
        comparison = {line.field_name: line.difference_state for line in self.comparison_line_ids}
        values = {}
        audit = []
        for proposed_field, partner_field, label in self._EXECUTION_MAPPING:
            value = self[proposed_field]
            if not value:
                continue
            if partner and comparison.get(proposed_field) == 'review':
                continue
            field = self._fields[proposed_field]
            write_value = value.id if field.type == 'many2one' else value
            old_value = partner[partner_field] if partner else False
            partner_field_def = self.env['res.partner']._fields[partner_field]
            old_text = self._comparison_text(partner, partner_field) if partner else ''
            if partner_field_def.type == 'many2one':
                new_text = value.display_name
            elif partner_field_def.type == 'binary':
                new_text = _('مرفقة')
            else:
                new_text = str(value)
            if partner_field in ('national_id', 'mother_name'):
                old_text = self._masked_national_id(old_text) if partner_field == 'national_id' else _('بيانات محمية')
                new_text = self._masked_national_id(new_text) if partner_field == 'national_id' else _('بيانات محمية')
            values[partner_field] = write_value
            audit.append((partner_field, label, old_text, new_text, 'new' if not old_value else ('unchanged' if old_value == value else 'modified')))
        if self.national_id:
            values['national_id_unavailable'] = False
        elif self.proposed_national_id_unavailable or self.national_id_exception_reason:
            values['national_id_unavailable'] = True
        if not self.national_id and self.national_id_exception_reason:
            values['national_id_unavailable_reason'] = self.national_id_exception_reason
            old_reason = partner.national_id_unavailable_reason if partner else ''
            audit.append((
                'national_id_unavailable_reason', 'سبب عدم توفر الرقم الوطني',
                _('بيانات محمية') if old_reason else '', _('بيانات محمية'),
                'new' if not old_reason else (
                    'unchanged' if old_reason == self.national_id_exception_reason else 'modified'
                ),
            ))
        return values, audit

    def action_execute_on_partner(self):
        if not self._is_executor():
            raise AccessError(_('لا تملك صلاحية تنفيذ تحديثات ملفات الأطباء.'))
        for rec in self:
            self.env.cr.execute(
                'SELECT id FROM membership_profile_update WHERE id = %s FOR UPDATE',
                [rec.id],
            )
            rec.invalidate_recordset()
            if rec.execution_state == 'executed':
                raise UserError(_('تم تنفيذ هذا الطلب مسبقًا على ملف الطبيب.'))
            if rec.state != 'approved':
                raise UserError(_('لا يمكن التنفيذ إلا لطلب تمت الموافقة عليه.'))
            rec._check_execution_references()
            if rec.match_searched_at and not rec._match_search_is_current():
                raise UserError(_('نتيجة البحث لم تعد حديثة؛ أعد الطلب للمراجعة وشغّل البحث مجددًا.'))
            selected = rec.match_result_ids.filtered(lambda line: line.decision == 'selected')
            if selected and (len(selected) != 1 or selected.partner_id != rec.partner_id):
                raise UserError(_('نتيجة المطابقة المختارة لا تتوافق مع الطبيب المرتبط بالطلب.'))

            execution_type = 'update' if rec.request_type == 'update_existing' else 'create'
            if execution_type == 'create':
                if rec.partner_id:
                    raise UserError(_('طلب إدخال العضو القائم مرتبط بطبيب بالفعل.'))
                if rec._strong_duplicate_candidates():
                    raise UserError(_('ظهر تطابق قوي جديد؛ يجب إعادة الطلب للمراجعة وحسم التطابق قبل إنشاء الطبيب.'))
                values, audit_values = rec._execution_partner_values()
                values.update({'is_doctor': True, 'company_id': rec.company_id.id})
                partner = self.env['res.partner'].with_company(rec.company_id).with_context(
                    default_is_doctor=True,
                ).create(values)
            else:
                partner = rec.partner_id
                if not partner or partner.company_id != rec.company_id:
                    raise UserError(_('الطبيب المرتبط لا يتبع نقابة الطلب.'))
                values, audit_values = rec._execution_partner_values(partner)
                values.pop('company_id', None)
                partner.write(values)

            executed_at = fields.Datetime.now()
            rec._execution_write({
                'partner_id': partner.id,
                'execution_state': 'executed', 'execution_type': execution_type,
                'executed_at': executed_at, 'executed_by_id': self.env.user.id,
                'executed_partner_id': partner.id,
            })
            Audit = self.env['membership.profile.execution.audit'].with_context(profile_execution=True)
            Audit.create([{
                'request_id': rec.id, 'partner_id': partner.id,
                'execution_type': execution_type, 'executed_by_id': self.env.user.id,
                'executed_at': executed_at, 'field_name': field_name,
                'field_label': label, 'old_value': old, 'new_value': new,
                'difference_state': difference,
            } for field_name, label, old, new, difference in audit_values])
            DoctorDocument = self.env['membership.doctor.document'].with_context(profile_execution=True)
            transferable = rec.document_line_ids.filtered(
                lambda doc: (
                    doc.status == 'provided'
                    and doc.verification_state == 'accepted'
                    and doc.file_data
                )
            )
            if transferable:
                DoctorDocument.create([{
                    'partner_id': partner.id, 'source_request_id': rec.id,
                    'source_document_id': document.id,
                } for document in transferable])
        return True

    def action_open_executed_partner(self):
        self.ensure_one()
        partner = self.executed_partner_id or self.partner_id
        if not partner:
            raise UserError(_('لا يوجد طبيب ناتج لفتحه.'))
        return {
            'type': 'ir.actions.act_window', 'res_model': 'res.partner',
            'view_mode': 'form', 'res_id': partner.id, 'target': 'current',
        }

    @api.model
    def _comparison_text(self, record, field_name):
        value = record[field_name]
        field = record._fields[field_name]
        if not value:
            return ''
        if field.type == 'many2one':
            return value.display_name
        if field.type == 'selection':
            selection = field._description_selection(record.env)
            return dict(selection).get(value, value)
        if field.type == 'binary':
            return _('مرفقة')
        return str(value)

    @api.model
    def _comparison_normalized(self, field_name, value):
        if field_name in ('national_id', 'medical_license_no', 'historical_membership_number'):
            return normalize_identifier(value)
        if 'phone' in field_name:
            return normalize_phone(value)
        if field_name in ('full_name', 'proposed_father_name', 'proposed_nickname', 'proposed_mother_full_name'):
            return normalize_arabic_name(value)
        return ' '.join((value or '').strip().casefold().split())

    def _refresh_comparison_lines(self):
        Line = self.env['membership.profile.comparison'].with_context(profile_comparison_refresh=True)
        for rec in self:
            rec.comparison_line_ids.with_context(profile_comparison_refresh=True).unlink()
            vals_list = rec._prepare_comparison_line_values()
            for vals in vals_list:
                vals['request_id'] = rec.id
            Line.create(vals_list)

    def _prepare_comparison_line_values(self):
        self.ensure_one()
        vals_list = []
        for sequence, (proposed_field, current_field, label) in enumerate(
            self.PROFILE_FIELD_MAPPING, 1
        ):
            proposed = self._comparison_text(self, proposed_field)
            current = self._comparison_text(self.partner_id, current_field) if self.partner_id else ''
            if not proposed:
                difference = 'not_entered'
            elif not self.partner_id or not current:
                difference = 'new'
            elif self._comparison_normalized(proposed_field, proposed) == self._comparison_normalized(proposed_field, current):
                difference = 'unchanged'
            elif proposed_field == 'national_id':
                difference = 'review'
            else:
                difference = 'modified'
            vals_list.append({
                'sequence': sequence, 'field_name': proposed_field,
                'field_label': label, 'current_value': current,
                'proposed_value': proposed, 'difference_state': difference,
            })
        return vals_list

    def action_copy_current_data(self):
        if not self._is_employee():
            raise AccessError(_('فقط موظف جمع البيانات يمكنه نسخ البيانات الحالية.'))
        for rec in self:
            if rec.state != 'draft' or rec.request_type != 'update_existing' or not rec.partner_id:
                raise UserError(_('يمكن النسخ في مسودة استكمال طبيب موجود فقط.'))
            vals = {}
            for proposed_field, current_field, _label in self._COMPARISON_FIELDS:
                value = rec.partner_id[current_field]
                current_field_type = rec.partner_id._fields[current_field].type
                vals[proposed_field] = value.id if current_field_type == 'many2one' else value
            rec.write(vals)
        return True

    @api.constrains('request_type', 'partner_id', 'company_id')
    def _check_request_identity(self):
        for rec in self:
            if rec.request_type == 'update_existing' and not rec.partner_id:
                raise ValidationError(_(
                    'An existing doctor is required for a profile completion request.'
                ))
            if (
                rec.request_type == 'update_existing'
                and rec.partner_id.company_id
                and rec.partner_id.company_id != rec.company_id
            ):
                raise ValidationError(_(
                    'The request company must match the existing doctor company.'
                ))
            if (
                rec.request_type == 'onboard_existing_member'
                and rec.partner_id
                and rec.state != 'approved'
            ):
                raise ValidationError(_(
                    'An existing-member onboarding request must not select a doctor before approval.'
                ))

    def _workflow_write(self, vals):
        return self.with_context(
            profile_update_workflow_token=self._WORKFLOW_TOKEN,
        ).write(vals)

    def _is_reviewer(self):
        return (
            self.env.user.has_group(self._REVIEWER_GROUP)
            or self.env.user.has_group(self._MANAGER_GROUP)
        )

    def _is_employee(self):
        return (
            self.env.user.has_group(self._EMPLOYEE_GROUP)
            or self.env.user.has_group(self._MANAGER_GROUP)
        )

    def _validate_submission(self):
        for rec in self:
            rec._check_allowed_company(rec.company_id)
            missing = []
            for proposed_field, current_field, label in (
                ('full_name', 'name', _('الاسم الكامل')),
                ('proposed_mother_full_name', 'mother_name', _('اسم الأم مع الكنية')),
                ('phone', 'mobile', _('الجوال / الهاتف')),
                ('medical_license_no', 'medical_license_no', _('رقم الترخيص الطبي')),
                ('medical_specialty_id', 'medical_specialty_id', _('الاختصاص الطبي')),
            ):
                current_value = (
                    rec.partner_id[current_field]
                    if rec.request_type == 'update_existing' and rec.partner_id
                    else False
                )
                if not rec[proposed_field] and not current_value:
                    missing.append(label)
            current_national = (
                rec.partner_id.national_id
                if rec.request_type == 'update_existing' and rec.partner_id else False
            )
            current_national_exception = (
                rec.partner_id.national_id_unavailable_reason
                if rec.request_type == 'update_existing' and rec.partner_id else False
            )
            if (
                not rec.national_id
                and not rec.national_id_exception_reason
                and not current_national
                and not current_national_exception
            ):
                missing.append(_('الرقم الوطني أو سبب عدم توفره'))
            # Validate only a newly proposed identifier. Existing legacy values
            # are displayed for review but are not rewritten by unrelated requests.
            normalized_national = normalize_identifier(rec.national_id)
            if normalized_national and len(normalized_national) >= 6 and len(set(normalized_national)) == 1:
                raise UserError(_('الرقم الوطني المدخل قيمة وهمية عامة؛ أدخل الرقم الصحيح أو سجل سبب عدم توفره.'))
            if rec.request_type == 'onboard_existing_member':
                if not rec.historical_membership_number:
                    missing.append(_('رقم العضوية السابق'))
                if not rec.proposed_union_status:
                    missing.append(_('الوضع النقابي'))
                if not rec.membership_evidence_attachment_ids:
                    missing.append(_('مستندات إثبات العضوية'))
            if missing:
                raise UserError(
                    _('Complete the following fields before submission:\n- %s')
                    % '\n- '.join(missing)
                )

            if rec.request_type == 'onboard_existing_member':
                if not rec._match_search_is_current():
                    rec.action_search_potential_matches()
                unresolved_national = rec.match_result_ids.filtered(
                    lambda line: line.national_id_match and line.decision == 'pending'
                )
                if unresolved_national:
                    raise UserError(_(
                        'يوجد تطابق قوي بالرقم الوطني. راجع النتيجة واختر الطبيب '
                        'أو أكد أنه شخص مختلف مع تسجيل السبب قبل الإرسال.'
                    ))

    def _match_fingerprint(self):
        self.ensure_one()
        values = (
            self.company_id.id, self.full_name, self.proposed_mother_full_name,
            self.national_id, self.medical_license_no,
            self.historical_membership_number, self.phone,
        )
        payload = '|'.join(str(value or '').strip() for value in values)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def _match_search_is_current(self):
        self.ensure_one()
        return bool(
            self.match_searched_at
            and self.match_search_fingerprint == self._match_fingerprint()
        )

    @api.model
    def _masked_national_id(self, value):
        value = (value or '').strip()
        if len(value) <= 4:
            return '*' * len(value)
        return ('*' * (len(value) - 4)) + value[-4:]

    def _candidate_match_values(self, partner):
        self.ensure_one()
        reasons = []
        national_match = bool(
            normalize_identifier(self.national_id)
            and normalize_identifier(self.national_id) == normalize_identifier(partner.national_id)
        )
        national_conflict = bool(
            normalize_identifier(self.national_id)
            and normalize_identifier(partner.national_id)
            and not national_match
        )
        license_match = bool(
            normalize_identifier(self.medical_license_no)
            and normalize_identifier(self.medical_license_no)
            == normalize_identifier(partner.medical_license_no)
        )
        membership_match = bool(
            self.company_id == partner.company_id
            and normalize_identifier(self.historical_membership_number)
            and normalize_identifier(self.historical_membership_number)
            == normalize_identifier(partner.membership_number)
        )
        phone_value = partner.mobile or partner.phone
        phone_match = bool(
            normalize_phone(self.phone)
            and normalize_phone(self.phone) == normalize_phone(phone_value)
        )
        partner_display_name = partner.display_name or partner.name
        partner_search_name = partner.arabic_name or partner.name
        partner_name = partner_display_name
        if (
            partner.arabic_name
            and normalize_arabic_name(partner.arabic_name)
            != normalize_arabic_name(partner_display_name)
        ):
            # Showing both prevents an Arabic-name snapshot from looking like a
            # different partner than the Many2one display name.
            partner_name = '%s — %s' % (partner_display_name, partner.arabic_name)
        name_similarity = self.env['membership.profile.match.result']._name_similarity(
            self.full_name, partner_search_name,
        )
        name_match = name_similarity >= 0.82
        mother_match = bool(
            normalize_arabic_name(self.proposed_mother_full_name)
            and normalize_arabic_name(self.proposed_mother_full_name)
            == normalize_arabic_name(partner.mother_name)
        )

        if national_match:
            reasons.append(_('تطابق الرقم الوطني'))
        if license_match:
            reasons.append(_('تطابق رقم الترخيص'))
        if membership_match:
            reasons.append(_('تطابق رقم العضوية داخل النقابة'))
        if name_match and mother_match:
            reasons.append(_('تشابه الاسم وتطابق اسم الأم مع الكنية'))
        elif name_match:
            reasons.append(_('تشابه الاسم'))
        if phone_match:
            reasons.append(_('تطابق الهاتف فقط') if len(reasons) == 0 else _('تطابق الهاتف'))
        if national_conflict and name_match:
            reasons.append(_('الرقم الوطني مختلف ويستلزم مراجعة يدوية'))

        if national_match or license_match or membership_match:
            level, rank = 'strong', 3
        elif name_match and mother_match:
            level, rank = 'medium', 2
        elif name_match or phone_match:
            level, rank = 'weak', 1
        else:
            return False
        return {
            'level': level, 'level_rank': rank,
            'national_id_match': national_match,
            'reason': '، '.join(reasons),
            'doctor_name': partner_name,
            'mother_full_name': partner.mother_name,
            'masked_national_id': self._masked_national_id(partner.national_id),
            'medical_license_no': partner.medical_license_no,
            'membership_number': partner.membership_number,
            'phone': phone_value,
        }

    def action_search_potential_matches(self):
        if not self._is_employee():
            raise AccessError(_('فقط موظف جمع بيانات الأطباء يمكنه تشغيل البحث.'))
        Result = self.env['membership.profile.match.result'].with_context(
            profile_match_search=True,
        )
        allowed_companies = self.env.user.company_ids
        for rec in self:
            rec._check_allowed_company(rec.company_id)
            if rec.state not in rec._EDITABLE_STATES:
                raise UserError(_('يمكن تشغيل البحث فقط عندما يكون الطلب قابلًا للتحرير.'))
            rec.match_result_ids.with_context(profile_match_search=True).unlink()
            candidates = self.env['res.partner'].with_context(
                allowed_company_ids=allowed_companies.ids,
            ).search([
                ('is_doctor', '=', True),
                ('company_id', 'in', allowed_companies.ids),
            ])
            values = []
            for partner in candidates:
                match = rec._candidate_match_values(partner)
                if not match:
                    continue
                same_company = partner.company_id == rec.company_id
                match.update({
                    'request_id': rec.id,
                    'partner_id': partner.id,
                    'same_company': same_company,
                    'cross_company_warning': not same_company,
                })
                values.append(match)
            if values:
                Result.create(values)
            rec.write({
                'match_searched_at': fields.Datetime.now(),
                'match_search_fingerprint': rec._match_fingerprint(),
            })
            rec._sync_match_selection()
            rec._refresh_match_summary()
        return True

    def _sync_match_selection(self, preferred_result=None):
        """Keep the single selected result aligned with the request partner."""
        for rec in self:
            results = rec.match_result_ids
            matching = results.filtered(
                lambda line: rec.partner_id and line.partner_id == rec.partner_id
            )
            preferred = self.env['membership.profile.match.result']
            if (
                preferred_result
                and preferred_result.request_id == rec
                and preferred_result in matching
            ):
                preferred = preferred_result
            elif matching:
                preferred = matching[:1]

            stale_selected = results.filtered(
                lambda line: line.decision == 'selected' and line != preferred
            )
            if stale_selected:
                stale_selected.write({
                    'decision': 'pending', 'different_reason': False,
                })
            if preferred and preferred.decision != 'selected':
                preferred.write({
                    'decision': 'selected', 'different_reason': False,
                })

    def _refresh_match_summary(self):
        for rec in self:
            results = rec.match_result_ids
            selected = results.filtered(
                lambda line: (
                    line.decision == 'selected'
                    and rec.partner_id
                    and line.partner_id == rec.partner_id
                )
            )
            pending = results.filtered(lambda line: line.decision == 'pending')
            if selected:
                state = 'selected'
                summary = _('تم اختيار طبيب موجود.')
            elif not results:
                state = 'no_match'
                summary = _(
                    'لم يُعثر على طبيب مطابق، ويمكن استكمال إدخال العضو القائم.'
                )
            elif pending:
                state = 'manual_review'
                summary = _('توجد نتائج محتملة تحتاج مراجعة يدوية.')
            else:
                state = 'potential'
                summary = _('تمت مراجعة نتائج التطابق المحتملة.')
            rec.write({'match_search_state': state, 'match_search_summary': summary})

    def action_waiting_documents(self):
        if not self._is_employee():
            raise AccessError(_('Only a doctor data employee can request documents.'))
        for rec in self:
            if rec.state not in self._EDITABLE_STATES:
                raise UserError(_('Only draft or returned requests can wait for documents.'))
            rec._workflow_write({'state': 'waiting_documents'})
        return True

    def action_resume(self):
        if not self._is_employee():
            raise AccessError(_('Only a doctor data employee can resume editing.'))
        for rec in self:
            if rec.state != 'waiting_documents':
                raise UserError(_('Only requests waiting for documents can resume editing.'))
            rec._workflow_write({'state': 'draft'})
        return True

    def action_submit(self):
        if not self._is_employee():
            raise AccessError(_('Only a doctor data employee can submit requests.'))
        for rec in self:
            if rec.state not in ('draft', 'returned', 'waiting_documents'):
                raise UserError(_('Only editable requests can be submitted for review.'))
            rec._validate_submission()
            rec._workflow_write({
                'state': 'waiting_review',
                'submitted_by_id': self.env.user.id,
                'submitted_date': fields.Datetime.now(),
                'return_reason': False,
            })
        return True

    def action_submit_for_review(self):
        return self.action_submit()

    def action_return(self):
        if not self._is_reviewer():
            raise AccessError(_('Only a doctor data reviewer can return requests.'))
        for rec in self:
            if rec.state != 'waiting_review':
                raise UserError(_('Only requests waiting for review can be returned.'))
            if not rec.return_reason:
                raise UserError(_('A return reason is required.'))
            rec._workflow_write({
                'state': 'returned',
                'reviewer_id': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })
        return True

    def action_approve(self):
        if not self._is_reviewer():
            raise AccessError(_('Only a doctor data reviewer can approve requests.'))
        for rec in self:
            if rec.state != 'waiting_review':
                raise UserError(_('Only requests waiting for review can be approved.'))
            if rec.create_uid == self.env.user or rec.submitted_by_id == self.env.user:
                raise AccessError(_('You cannot approve a request you created or submitted.'))
            if (
                rec.request_type == 'onboard_existing_member'
                and not rec.national_id
                and not rec.membership_evidence_attachment_ids
                and not rec.reviewer_notes
            ):
                raise UserError(_(
                    'A supporting document or reviewer note is required to approve '
                    'an existing member without a National ID.'
                ))
            # Phase 1 intentionally approves only the request structure. It
            # neither creates nor updates a doctor and does not invoke any
            # membership, invoice, payment, period, or sequence workflow.
            rec._workflow_write({
                'state': 'approved',
                'reviewer_id': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state in self._LOCKED_STATES:
                raise UserError(_('This request is already closed.'))
            if not rec.cancellation_reason:
                raise UserError(_('A cancellation reason is required.'))
            if rec.state == 'waiting_review' and not rec._is_reviewer():
                raise AccessError(_(
                    'Only a reviewer can cancel a request waiting for review.'
                ))
            if rec.state != 'waiting_review' and not rec._is_employee():
                raise AccessError(_(
                    'Only a doctor data employee can cancel an editable request.'
                ))
            rec._workflow_write({
                'state': 'cancelled',
                'reviewer_id': self.env.user.id if rec._is_reviewer() else False,
                'reviewed_date': fields.Datetime.now(),
            })
        return True

    # Compatibility aliases for callers from the previous workflow. They no
    # longer touch doctor_membership_state.
    def action_need_info(self):
        return self.action_return()

    def action_reject(self):
        return self.action_cancel()
