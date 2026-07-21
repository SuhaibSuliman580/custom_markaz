from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _is_doctor_creation_context(self):
        if self.env.context.get('default_is_doctor'):
            return True

        params = self.env.context.get('params') or {}
        action_id = params.get('action')
        try:
            action_id = int(action_id)
        except (TypeError, ValueError):
            return False

        doctor_actions = [
            self.env.ref('membership_management.action_doctor_partners', raise_if_not_found=False),
            self.env.ref('finalmod.action_doctor_partners', raise_if_not_found=False),
        ]
        doctor_action_ids = [action.id for action in doctor_actions if action]

        return action_id in doctor_action_ids

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._is_doctor_creation_context():
            res['is_doctor'] = True
            res['company_id'] = self.env.company.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        company_id = self.env.company.id
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            is_doctor = vals.get('is_doctor') or self._is_doctor_creation_context()
            if is_doctor:
                vals['company_id'] = company_id
                if not vals.get('name'):
                    parts = [
                        vals.get('doctor_first_name'), vals.get('father_name'),
                        vals.get('grandfather_name'), vals.get('nickname'),
                    ]
                    composed = ' '.join(part.strip() for part in parts if part and part.strip())
                    if composed:
                        vals['name'] = composed
            prepared.append(vals)
        vals_list = prepared
        return super().create(vals_list)

    def _sync_related_users_company(self, company_id):
        if not company_id:
            return
        Users = self.env['res.users'].sudo().with_context(active_test=False)
        users = self.sudo().mapped('user_ids') | Users.search([('partner_id', 'in', self.ids)])
        for user in users:
            company_ids = set(user.company_ids.ids)
            if user.company_id:
                company_ids.add(user.company_id.id)
            company_ids.add(company_id)
            user_vals = {'company_ids': [(6, 0, sorted(company_ids))]}
            if user.company_id.id != company_id:
                user_vals['company_id'] = company_id
            user.sudo().write(user_vals)

    def write(self, vals):
        user_company_change = 'company_id' in vals
        if vals.get('is_doctor') and 'company_id' not in vals:
            vals = dict(vals, company_id=self.env.company.id)
        allow_doctor_company_change = self.env.context.get('allow_doctor_company_change')
        if user_company_change and not allow_doctor_company_change and not self.env.user.has_group('base.group_system'):
            doctors = self.filtered(lambda partner: partner.is_doctor or vals.get('is_doctor'))
            if doctors:
                raise AccessError(_("Only administrators can change the company of a doctor."))
        if vals.get('company_id'):
            self._sync_related_users_company(vals['company_id'])
        return super().write(vals)

    # ── MEMBERSHIP INFORMATION ──
    @api.onchange('name', 'is_doctor')
    def _onchange_is_doctor_default_company(self):
        if (self.is_doctor or self._is_doctor_creation_context()) and not self.company_id:
            self.company_id = self.env.company

    is_doctor = fields.Boolean(string='Is Doctor', default=False)
    membership_number = fields.Char(string='Membership Number', copy=False)
    doctor_membership_state = fields.Selection([
        ('none', 'No Membership'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ], string='Membership Status', default='none', readonly=True, copy=False)
    membership_start_date = fields.Date(string='Membership Start Date', readonly=True, copy=False)
    membership_end_date = fields.Date(string='Membership End Date', readonly=True, copy=False)
    active_membership_id = fields.Many2one(
        'membership.period', string='Active Membership', readonly=True, copy=False,
    )
    membership_application_ids = fields.One2many(
        'membership.application', 'partner_id', string='Membership Applications',
    )
    membership_period_ids = fields.One2many(
        'membership.period', 'partner_id', string='Membership Periods',
    )
    membership_service_request_ids = fields.One2many(
        'membership.service.request',
        'partner_id',
        string='Service Requests',
    )
    membership_service_request_count = fields.Integer(
        compute='_compute_membership_service_request_count',
        string='Service Request Count',
    )
    membership_join_date = fields.Date(string='Membership Join Date')
    membership_rejoin_date = fields.Date(string='Re-Join Date')
    membership_rejoin_decision = fields.Char(string='Re-Join Decision Number')
    deletion_number = fields.Char(string='Deletion Number')
    branch_return_date = fields.Date(string='Branch Return Date')

    def _compute_membership_service_request_count(self):
        grouped = self.env['membership.service.request'].read_group(
            [('partner_id', 'in', self.ids)],
            ['partner_id'],
            ['partner_id'],
        )
        counts = {
            item['partner_id'][0]: item.get('__count', item.get('partner_id_count', 0))
            for item in grouped
        }
        for partner in self:
            partner.membership_service_request_count = counts.get(partner.id, 0)

    def action_view_membership_service_requests(self):
        self.ensure_one()
        action = self.env.ref(
            'membership_management.action_membership_service_request'
        ).read()[0]
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.id,
            'default_company_id': self.company_id.id or self.env.company.id,
        }
        return action

    def action_open_doctor_360(self):
        self.ensure_one()
        if not self.is_doctor:
            raise AccessError(_("لا يمكن فتح الملف الموحد إلا للطبيب."))
        return self.env['membership.doctor.360'].action_open_for_doctor(self)

    # ── Doctor Personal Info ──
    arabic_name = fields.Char(string='Name (Arabic)')
    english_name = fields.Char(string='الاسم بالإنكليزية')
    nickname = fields.Char(string='Nickname')
    current_residence = fields.Char(string='Current Residence')
    military_service_start_date = fields.Date(string='Military Service Start Date')
    military_service_end_date = fields.Date(string='Military Service End Date')
    national_id = fields.Char(string='National ID / Iqama')
    birth_date = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender')
    nationality_id = fields.Many2one('res.country', string='Nationality')
    medical_specialty_id = fields.Many2one(
        'medical.specialty', string='Medical Specialty', check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    father_name = fields.Char(string='Father Name')
    grandfather_name = fields.Char(string='اسم الجد')
    mother_name = fields.Char(string='Mother Name')
    doctor_first_name = fields.Char(string='الاسم الأول')
    birth_place = fields.Char(string='مكان الولادة')
    marital_status = fields.Selection([
        ('single', 'أعزب'), ('married', 'متزوج'),
        ('divorced', 'مطلق'), ('widowed', 'أرمل'),
    ], string='الحالة الاجتماعية')
    doctor_district = fields.Char(string='المنطقة')
    doctor_subdistrict = fields.Char(string='الناحية')
    doctor_village = fields.Char(string='القرية')
    national_id_unavailable = fields.Boolean(string='الرقم الوطني غير متوفر')
    national_id_unavailable_reason = fields.Text(string='سبب عدم توفر الرقم الوطني')
    certificate_country_id = fields.Many2one('res.country', string='بلد صدور الشهادة')
    doctor_document_ids = fields.One2many(
        'membership.doctor.document', 'partner_id', string='وثائق الطبيب المعتمدة',
    )
    profile_execution_request_ids = fields.One2many(
        'membership.profile.update', 'executed_partner_id', string='طلبات تحديث بيانات الطبيب',
    )
    profile_execution_request_count = fields.Integer(
        compute='_compute_profile_execution_request_count', string='طلبات تحديث البيانات',
    )

    def _compute_profile_execution_request_count(self):
        for partner in self:
            partner.profile_execution_request_count = len(partner.profile_execution_request_ids)

    def action_view_profile_execution_requests(self):
        self.ensure_one()
        action = self.env.ref('membership_management.action_membership_profile_update').read()[0]
        action['domain'] = [
            ('executed_partner_id', '=', self.id),
            ('company_id', 'in', self.env.companies.ids),
        ]
        action['context'] = {'create': False}
        return action
    # social_status = fields.Selection([
    #     ('single', 'Single'),
    #     ('married', 'Married'),
    #     ('engaged', 'Engaged'),
    # ], string='Social Status')
    # wives_count = fields.Integer(string='Number of Wives')
    # children_count = fields.Integer(string='Number of Children')
    registry_place_number = fields.Char(string='Registry Place & Number')

    # ── Medical Qualifications ──
    # medical_specialty = fields.Selection([
    #     ('general', 'General Practice'),
    #     ('internal', 'Internal Medicine'),
    #     ('surgery', 'General Surgery'),
    #     ('pediatrics', 'Pediatrics'),
    #     ('obstetrics', 'Obstetrics & Gynecology'),
    #     ('cardiology', 'Cardiology'),
    #     ('orthopedics', 'Orthopedics'),
    #     ('dermatology', 'Dermatology'),
    #     ('ophthalmology', 'Ophthalmology'),
    #     ('ent', 'ENT (Ear, Nose & Throat)'),
    #     ('neurology', 'Neurology'),
    #     ('psychiatry', 'Psychiatry'),
    #     ('radiology', 'Radiology'),
    #     ('anesthesia', 'Anesthesia'),
    #     ('pathology', 'Pathology'),
    #     ('urology', 'Urology'),
    #     ('oncology', 'Oncology'),
    #     ('dental', 'Dentistry'),
    #     ('pharmacy', 'Pharmacy'),
    #     ('other', 'Other'),
    # ], string='Medical Specialty')
    qualification = fields.Selection([
        ('bachelor', 'Bachelor (MBBS)'),
        ('master', 'Master'),
        ('md', 'MD'),
        ('phd', 'PhD / Doctorate'),
        ('fellowship', 'Fellowship'),
        ('board', 'Board Certified'),
    ], string='Highest Qualification')
    university = fields.Char(string='University / Institution')

    # Dropdown (computed) linked to Universities table, without requiring DB column migration
    university_id = fields.Many2one(
        'medical.unv',
        string='University / Institution',
        compute='_compute_university_id',
        inverse='_inverse_university_id',
        search='_search_university_id',
        store=False,
    )

    graduation_year = fields.Char(string='Graduation Year')
    faculty_name = fields.Char(string='الكلية')
    academic_degree = fields.Char(string='الدرجة العلمية')
    certificate_date = fields.Date(string='تاريخ الحصول على الشهادة')
    certificate_title = fields.Char(string='عنوان / نوع الشهادة')

    @api.depends('university')
    def _compute_university_id(self):
        Univ = self.env['medical.unv']
        for rec in self:
            if rec.university:
                unv = Univ.search([('name', '=', rec.university)], limit=1)
                rec.university_id = unv
            else:
                rec.university_id = False

    def _inverse_university_id(self):
        for rec in self:
            rec.university = rec.university_id.name if rec.university_id else False

    def _search_university_id(self, operator, value):
        """Map searching on university_id to searching by the stored Char field "university"."""
        Univ = self.env['medical.unv']
        # value can be an ID, list of IDs, or a name depending on domain
        if isinstance(value, int):
            name = Univ.browse(value).name or ''
            return [('university', operator, name)]
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], int):
            names = Univ.browse(value).mapped('name')
            return [('university', 'in', names)]
        return [('university', operator, value or '')]

    # ── Medical License ──
    medical_license_no = fields.Char(string='Medical License Number')
    license_issue_date = fields.Date(string='License Issue Date')
    license_expiry_date = fields.Date(string='License Expiry Date')
    license_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary'),
    ], string='License Type')
    license_issuer = fields.Char(string='جهة إصدار الترخيص')
    medical_subspecialty_id = fields.Many2one(
        'medical.specialty', string='الاختصاص الفرعي', check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    permanent_license_date_1 = fields.Date(string='Permanent License Date 1')
    permanent_license_date_2 = fields.Date(string='Permanent License Date 2')
    temporary_license_date_1 = fields.Date(string='Temporary License Date 1')
    temporary_license_date_2 = fields.Date(string='Temporary License Date 2')
    temporary_license_date_3 = fields.Date(string='Temporary License Date 3')
    ministry_registration_number = fields.Char(
        string='Ministry of Health Registration Number'
    )
    ministry_registration_date = fields.Date(
        string='Ministry of Health Registration Date')
    permanent_specialty_date = fields.Date(string='Permanent Specialty Date')
    temporary_specialty_date_2 = fields.Date(string='Temporary Specialty Date 2')
    permanent_specialty_date_2 = fields.Date(string='Permanent Specialty Date 2')
    specialty_date_2 = fields.Date(string='Specialty Date 2')
    specialty_date_3 = fields.Date(string='Specialty Date 3')
    permanent_license_date_3 = fields.Date(string='Permanent License Date 3')
    temporary_specialty_date = fields.Date(string='Temporary Specialty Date')
    deletion_date = fields.Date(string='Deletion Date')
    union_status = fields.Selection([
        ('active', 'Active'),
        ('retired', 'Retired'),
        ('deceased', 'Deceased'),
        ('deleted', 'Deleted'),
        ('transferred', 'Transferred'),
        ('inactive', 'Inactive'),
    ], string='Fund / Union Status')
    fees_paid_until_year = fields.Char(string='Fees Paid Until Year')

    # ── Employment ──
    workplace_name = fields.Char(string='Current Workplace')
    workplace_type = fields.Selection([
        ('government', 'Government Hospital'),
        ('private_hospital', 'Private Hospital'),
        ('clinic', 'Private Clinic'),
        ('university', 'University Hospital'),
        ('military', 'Military Hospital'),
        ('other', 'Other'),
    ], string='Workplace Type')
    years_of_experience = fields.Integer(string='Years of Experience')
    practice_type = fields.Char(string='نوع الممارسة')
    professional_capacity = fields.Char(string='الصفة المهنية')
    doctor_job_title = fields.Char(string='المسمى الوظيفي')
    practice_start_date = fields.Date(string='تاريخ بدء ممارسة المهنة')
    is_employee = fields.Boolean(string='Is Employee')
    fund_status = fields.Selection([
        ('contracted', 'Contracted'),
        ('not_contracted', 'Not Contracted'),
        ('blocked', 'Blocked'),
    ], string='Fund Status')
    transfer_from_entity = fields.Char(string='Transfer From Entity')
    transfer_from_date = fields.Date(string='Transfer From Date')
    transfer_to_entity = fields.Char(string='Transfer To Entity')
    transfer_to_date = fields.Date(string='Transfer To Date')
    outside_country = fields.Boolean(string='Outside Country')
    bank_account_number = fields.Char(string='Bank Account Number')
    bank_name = fields.Char(string='Bank Name')
    retirement_date = fields.Date(string='Retirement Date')
    retirement_decision_number = fields.Char(string='Retirement Decision Number')
    retirement_salary = fields.Float(string='Retirement Salary')
    death_date = fields.Date(string='Death Date')
    death_decision_number = fields.Char(string='Death Decision Number')
    social_security_registered = fields.Boolean(
        string='Registered in Social Security'
    )
    clinic_address = fields.Char(string='Clinic Address')
    clinic_phone = fields.Char(string='Clinic Phone Number')

    # SPECIALTY & DEGREE
    specialty_classification = fields.Selection([
        ('specialist', 'Specialist'),
        ('practitioner', 'Practitioner'),
        ('rare', 'Rare Specialty'),
    ], string='Classification')
    # specialization_certificate_number = fields.Char(
    #     string='Specialization Certificate Number'
    # )
    certificate_issue_place = fields.Selection([
        ('inside', 'Inside Country'),
        ('outside', 'Outside Country'),
    ], string='Certificate Issue Place')
    certificate_modify_date = fields.Date(string='Certificate Modify Date')
    certificate_modify_number = fields.Char(string='Certificate Modify Number')
    specialization_authority_1 = fields.Many2one('medical.specialty', string='Specialization Authority 2')
    specialization_authority_2 = fields.Many2one('medical.specialty', string='Specialization Authority 2')
    specialization_authority_3 = fields.Many2one('medical.specialty', string='Specialization Authority 3')
    # practice_location = fields.Selection([
    #     ('city', 'City'),
    #     ('rural', 'Rural'),
    # ], string='Practice Location')

