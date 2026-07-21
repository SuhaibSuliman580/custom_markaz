import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMembershipProfilePhase3(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        internal = cls.env.ref('base.group_user')
        employee_group = cls.env.ref('membership_management.group_doctor_data_employee')
        reviewer_group = cls.env.ref('membership_management.group_doctor_data_reviewer')
        executor_group = cls.env.ref('membership_management.group_doctor_data_executor')
        def user(name, login, group):
            return cls.env['res.users'].create({
                'name': name, 'login': login, 'company_id': cls.company.id,
                'company_ids': [(6, 0, [cls.company.id])],
                'groups_id': [(6, 0, [internal.id, group.id])],
            })
        cls.employee = user('Phase 3 Employee', 'phase3.employee', employee_group)
        cls.reviewer = user('Phase 3 Reviewer', 'phase3.reviewer', reviewer_group)
        cls.executor = user('Phase 3 Executor', 'phase3.executor', executor_group)
        cls.specialty = cls.env['medical.specialty'].create({
            'name': 'Phase 3 Specialty', 'code': 'PH3', 'company_id': cls.company.id,
        })
        cls.university = cls.env['medical.unv'].create({
            'name': 'Phase 3 University', 'code': 'PH3U', 'company_id': cls.company.id,
        })

    def _vals(self, token, request_type='onboard_existing_member', partner=None):
        vals = {
            'request_type': request_type, 'company_id': self.company.id,
            'full_name': 'طبيب المرحلة الثالثة ' + token,
            'proposed_english_name': 'Phase Three Doctor ' + token,
            'proposed_nickname': 'الطبيب',
            'proposed_first_name': 'طبيب', 'proposed_father_name': 'سالم',
            'proposed_grandfather_name': 'محمد',
            'proposed_mother_full_name': 'أم الطبيب مع الكنية',
            'national_id': 'NAT-' + token, 'phone': '0944' + token[-6:].zfill(6),
            'proposed_birth_date': '1975-01-01',
            'proposed_registry_place_number': 'دمشق ' + token,
            'email': token.lower() + '@example.com',
            'medical_license_no': 'LIC-' + token,
            'medical_specialty_id': self.specialty.id,
            'historical_membership_number': 'OLD-' + token,
            'proposed_membership_state': 'active',
            'proposed_membership_start_date': '2001-01-01',
            'proposed_membership_end_date': '2030-12-31',
            'proposed_union_status': 'active',
            'proposed_membership_join_date': '2001-01-01',
            'proposed_gender': 'male', 'proposed_birth_place': 'دمشق',
            'proposed_marital_status': 'married',
            'proposed_district': 'المنطقة الطبية',
            'proposed_subdistrict': 'الناحية الطبية',
            'proposed_village': 'القرية الطبية',
            'proposed_residence': 'مكان الإقامة',
            'proposed_university_id': self.university.id,
            'proposed_qualification': 'bachelor', 'proposed_graduation_year': '2000',
            'proposed_specialty_classification': 'rare',
            'proposed_faculty': 'كلية الطب',
            'proposed_academic_degree': 'إجازة في الطب',
            'proposed_certificate_date': '2000-07-01',
            'proposed_certificate_title': 'إجازة طبيب',
            'proposed_city': 'دمشق', 'proposed_workplace_name': 'مشفى الاختبار',
            'proposed_license_issuer': 'وزارة الصحة',
            'proposed_ministry_registration_number': 'MOH-' + token,
            'proposed_ministry_registration_date': '2001-01-02',
            'proposed_license_type': 'permanent',
            'proposed_fund_status': 'contracted',
            'proposed_practice_type': 'عيادة',
            'proposed_professional_capacity': 'طبيب أخصائي',
            'proposed_job_title': 'طبيب',
            'proposed_practice_start_date': '2001-01-01',
            'proposed_fees_paid_until_year': '2024',
        }
        if partner:
            vals['partner_id'] = partner.id
        return vals

    def _create_request(self, token, request_type='onboard_existing_member', partner=None, document=False, **extra):
        vals = self._vals(token, request_type, partner)
        vals.update(extra)
        request = self.env['membership.profile.update'].with_user(self.employee).create(
            vals
        )
        proof = self.env['ir.attachment'].create({
            'name': 'membership-proof.pdf', 'type': 'binary',
            'datas': base64.b64encode(b'proof'), 'res_model': request._name,
            'res_id': request.id,
        })
        request.with_user(self.employee).write({
            'membership_evidence_attachment_ids': [(4, proof.id)],
        })
        if document:
            self.env['membership.profile.document'].with_user(self.employee).create({
                'request_id': request.id, 'document_type': 'medical_license',
                'status': 'provided', 'file_name': 'license.pdf',
                'document_name': 'ترخيص مزاولة', 'document_number': 'DOC-1',
                'issue_date': '2020-01-01', 'expiry_date': '2030-01-01',
                'issuing_authority': 'وزارة الصحة', 'verification_state': 'accepted',
                'file_data': base64.b64encode(b'license'),
            })
            self.env['membership.profile.document'].with_user(self.employee).create({
                'request_id': request.id, 'document_type': 'other',
                'status': 'needs_review', 'file_name': 'unapproved.pdf',
                'file_data': base64.b64encode(b'unapproved'),
            })
        request.with_user(self.employee).action_submit()
        request.with_user(self.reviewer).action_approve()
        return request

    def _protected_counts(self):
        return {m: self.env[m].search_count([]) for m in (
            'membership.application', 'membership.period', 'account.move', 'account.payment',
        )}

    def test_execute_onboarding_creates_one_complete_doctor_and_document(self):
        request = self._create_request('CREATE301', document=True)
        before = self._protected_counts()
        sequence = self.env['ir.sequence'].search([('code', '=', 'membership.number')], limit=1)
        sequence_before = sequence.number_next_actual if sequence else False
        request.with_user(self.executor).action_execute_on_partner()
        doctor = request.executed_partner_id
        self.assertTrue(doctor)
        self.assertTrue(doctor.is_doctor)
        self.assertEqual(doctor.company_id, self.company)
        self.assertEqual(doctor.name, request.full_name)
        self.assertEqual(doctor.doctor_first_name, request.proposed_first_name)
        self.assertEqual(doctor.grandfather_name, request.proposed_grandfather_name)
        self.assertEqual(doctor.marital_status, request.proposed_marital_status)
        self.assertEqual(doctor.doctor_district, request.proposed_district)
        self.assertEqual(doctor.mother_name, request.proposed_mother_full_name)
        self.assertEqual(doctor.university, self.university.name)
        self.assertEqual(doctor.membership_number, request.historical_membership_number)
        self.assertEqual(doctor.fees_paid_until_year, request.proposed_fees_paid_until_year)
        self.assertEqual(doctor.faculty_name, request.proposed_faculty)
        self.assertEqual(doctor.license_issuer, request.proposed_license_issuer)
        self.assertEqual(request.partner_id, doctor)
        self.assertEqual(request.execution_state, 'executed')
        self.assertEqual(len(doctor.doctor_document_ids), 1)
        self.assertEqual(doctor.doctor_document_ids.document_type, 'medical_license')
        self.assertEqual(doctor.doctor_document_ids.document_number, 'DOC-1')
        self.assertEqual(doctor.doctor_document_ids.verification_state, 'accepted')
        self.assertEqual(doctor.doctor_document_ids.source_request_id, request)
        self.assertTrue(doctor.profile_execution_request_ids & request)
        self.assertTrue(self.env['res.partner'].search_count([('id', '=', doctor.id), ('is_doctor', '=', True)]))
        self.assertEqual(before, self._protected_counts())
        if sequence:
            self.assertEqual(sequence.number_next_actual, sequence_before)

    def test_repeat_execution_is_blocked_without_second_doctor(self):
        request = self._create_request('REPEAT302')
        request.with_user(self.executor).action_execute_on_partner()
        doctor = request.executed_partner_id
        with self.assertRaises(UserError):
            request.with_user(self.executor).action_execute_on_partner()
        self.assertEqual(request.executed_partner_id, doctor)
        self.assertEqual(self.env['res.partner'].search_count([('id', '=', doctor.id)]), 1)

    def test_doctor_name_composes_only_when_missing_and_regular_partner_is_unchanged(self):
        doctor = self.env['res.partner'].with_context(default_is_doctor=True).create({
            'doctor_first_name': 'سامر', 'father_name': 'أحمد',
            'grandfather_name': 'محمود', 'nickname': 'السليمان',
        })
        self.assertEqual(doctor.name, 'سامر أحمد محمود السليمان')
        explicitly_named = self.env['res.partner'].with_context(default_is_doctor=True).create({
            'name': 'اسم طبيب معتمد', 'doctor_first_name': 'لا يستبدل',
        })
        self.assertEqual(explicitly_named.name, 'اسم طبيب معتمد')
        contact = self.env['res.partner'].create({'name': 'جهة اتصال عادية'})
        self.assertFalse(contact.is_doctor)
        self.assertEqual(contact.name, 'جهة اتصال عادية')

    def test_profile_mapping_has_matching_types_relations_and_selections(self):
        request_model = self.env['membership.profile.update']
        partner_model = self.env['res.partner']
        proposed_names = []
        partner_names = []
        for proposed_name, partner_name, _label in request_model.PROFILE_FIELD_MAPPING:
            proposed_names.append(proposed_name)
            partner_names.append(partner_name)
            proposed = request_model._fields[proposed_name]
            partner = partner_model._fields[partner_name]
            self.assertEqual(proposed.type, partner.type, (proposed_name, partner_name))
            if proposed.type == 'many2one':
                self.assertEqual(proposed.comodel_name, partner.comodel_name)
            if proposed.type == 'selection':
                self.assertEqual(
                    dict(proposed._description_selection(self.env)),
                    dict(partner._description_selection(self.env)),
                    (proposed_name, partner_name),
                )
        self.assertEqual(len(proposed_names), len(set(proposed_names)))
        self.assertEqual(len(partner_names), len(set(partner_names)))

    def test_evidence_attachment_is_bound_and_readable_by_reviewer(self):
        request = self.env['membership.profile.update'].with_user(self.employee).create(
            self._vals('ATTACH308')
        )
        attachment = self.env['ir.attachment'].with_user(self.employee).create({
            'name': 'evidence.pdf', 'type': 'binary',
            'datas': base64.b64encode(b'evidence'),
            'res_model': request._name, 'res_id': 0,
        })
        request.with_user(self.employee).write({
            'membership_evidence_attachment_ids': [(4, attachment.id)],
        })
        self.assertEqual(attachment.res_model, request._name)
        self.assertEqual(attachment.res_id, request.id)
        self.assertEqual(
            request.with_user(self.reviewer).membership_evidence_attachment_ids.mapped('name'),
            ['evidence.pdf'],
        )

    def test_update_existing_writes_only_nonempty_and_keeps_company(self):
        doctor = self.env['res.partner'].create({
            'name': 'طبيب قديم', 'is_doctor': True, 'company_id': self.company.id,
            'national_id': 'NAT-UPDATE303', 'medical_license_no': 'LIC-UPDATE303',
            'mobile': '0944UPDATE303', 'email': 'keep@example.com', 'city': 'القديمة',
        })
        request = self._create_request('UPDATE303', 'update_existing', doctor, email=False)
        company = doctor.company_id
        request.with_user(self.executor).action_execute_on_partner()
        self.assertEqual(request.executed_partner_id, doctor)
        self.assertEqual(doctor.company_id, company)
        self.assertEqual(doctor.name, request.full_name)
        self.assertEqual(doctor.city, request.proposed_city)
        self.assertEqual(doctor.email, 'keep@example.com')
        audit_lines = request.with_user(self.executor).execution_audit_ids
        self.assertTrue(audit_lines)
        national_audit = audit_lines.filtered(lambda line: line.field_name == 'national_id')
        self.assertNotIn(request.national_id, national_audit.new_value)

    def test_membership_number_only_updates_no_other_doctor_data(self):
        doctor = self.env['res.partner'].create({
            'name': 'طبيب رقم عضوية', 'is_doctor': True,
            'company_id': self.company.id, 'membership_number': 'MEM-OLD-309',
            'email': 'untouched@example.com', 'national_id_unavailable': False,
        })
        request = self.env['membership.profile.update'].with_user(self.employee).create({
            'request_type': 'membership_number_only', 'company_id': self.company.id,
            'partner_id': doctor.id,
            'historical_membership_number': 'MEM-NEW-309',
        })
        request._workflow_write({'state': 'approved'})
        request.with_user(self.executor).action_execute_on_partner()
        self.assertEqual(doctor.membership_number, 'MEM-NEW-309')
        self.assertEqual(doctor.email, 'untouched@example.com')
        self.assertFalse(doctor.national_id_unavailable)

    def test_new_strong_duplicate_blocks_creation(self):
        request = self._create_request('DUPLIC304')
        self.env['res.partner'].create({
            'name': 'تطابق جديد', 'is_doctor': True, 'company_id': self.company.id,
            'national_id': request.national_id,
        })
        before = self.env['res.partner'].search_count([])
        with self.assertRaises(UserError):
            request.with_user(self.executor).action_execute_on_partner()
        self.assertEqual(self.env['res.partner'].search_count([]), before)
        self.assertEqual(request.execution_state, 'pending')

    def test_non_executor_cannot_execute(self):
        request = self._create_request('SECURE305')
        with self.assertRaises(Exception):
            request.with_user(self.employee).action_execute_on_partner()

    def test_open_partner_action_targets_execution_result(self):
        request = self._create_request('OPEN306')
        request.with_user(self.executor).action_execute_on_partner()
        action = request.with_user(self.executor).action_open_executed_partner()
        self.assertEqual(action['res_model'], 'res.partner')
        self.assertEqual(action['res_id'], request.executed_partner_id.id)

    def test_failure_during_document_transfer_rolls_back_created_doctor(self):
        request = self._create_request('ROLLBACK307', document=True)
        source_document = request.document_line_ids.filtered(lambda doc: doc.status == 'provided')
        existing = self.env['res.partner'].create({
            'name': 'وثيقة سابقة', 'is_doctor': True, 'company_id': self.company.id,
        })
        self.env['membership.doctor.document'].with_context(profile_execution=True).create({
            'partner_id': existing.id, 'source_request_id': request.id,
            'source_document_id': source_document.id,
        })
        before = self.env['res.partner'].search_count([])
        with self.assertRaises(Exception):
            request.with_user(self.executor).action_execute_on_partner()
        self.assertEqual(self.env['res.partner'].search_count([]), before)
        self.assertEqual(request.execution_state, 'pending')
        self.assertFalse(request.executed_partner_id)
