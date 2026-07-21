import base64

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestMembershipProfileMatchPhase2A(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({'name': 'Phase 2A Other Union'})
        employee_group = cls.env.ref('membership_management.group_doctor_data_employee')
        internal_group = cls.env.ref('base.group_user')
        cls.employee = cls.env['res.users'].create({
            'name': 'Phase 2A Employee',
            'login': 'phase2a.employee',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id, cls.other_company.id])],
            'groups_id': [(6, 0, [internal_group.id, employee_group.id])],
        })
        cls.specialty = cls.env['medical.specialty'].create({
            'name': 'Phase 2A Specialty', 'code': 'PH2A',
            'company_id': cls.company.id,
        })
        cls.university = cls.env['medical.unv'].create({
            'name': 'Phase 2A University', 'code': 'PH2AU',
            'company_id': cls.company.id,
        })

    def _request(self, **overrides):
        vals = {
            'request_type': 'onboard_existing_member',
            'company_id': self.company.id,
            'full_name': 'أحمد علي الحسن',
            'proposed_english_name': 'Ahmad Ali Alhasan',
            'proposed_nickname': 'الحسن',
            'proposed_father_name': 'علي',
            'proposed_mother_full_name': 'فاطمة محمود الخطيب',
            'national_id': 'N-200-100',
            'proposed_gender': 'male', 'proposed_birth_date': '1980-01-01',
            'proposed_registry_place_number': 'دمشق 100',
            'proposed_university_id': self.university.id,
            'proposed_graduation_year': '2004',
            'proposed_specialty_classification': 'specialist',
            'phone': '+963 944 111 222',
            'medical_license_no': 'LIC-200',
            'medical_specialty_id': self.specialty.id,
            'historical_membership_number': 'MEM-200',
            'proposed_membership_state': 'active',
            'proposed_membership_start_date': '2005-01-01',
            'proposed_membership_end_date': '2030-12-31',
            'proposed_union_status': 'active',
            'proposed_membership_join_date': '2005-01-01',
            'proposed_ministry_registration_number': 'MOH-2A',
            'proposed_ministry_registration_date': '2005-01-02',
            'proposed_license_type': 'permanent',
            'proposed_fund_status': 'contracted',
        }
        vals.update(overrides)
        return self.env['membership.profile.update'].with_user(self.employee).create(vals)

    def _doctor(self, company=None, **overrides):
        company = company or self.company
        vals = {
            'name': 'أحمد علي الحسن', 'arabic_name': 'أحمد علي الحسن',
            'mother_name': 'فاطمة محمود الخطيب',
            'is_doctor': True, 'company_id': company.id,
            'national_id': 'N200100', 'mobile': '0944111222',
            'medical_license_no': 'LIC200', 'membership_number': 'MEM200',
        }
        vals.update(overrides)
        return self.env['res.partner'].with_company(company).create(vals)

    def _attach(self, request):
        attachment = self.env['ir.attachment'].create({
            'name': 'phase2a-proof.pdf', 'type': 'binary',
            'datas': base64.b64encode(b'proof'),
            'res_model': request._name, 'res_id': request.id,
        })
        request.with_user(self.employee).write({
            'membership_evidence_attachment_ids': [(4, attachment.id)],
        })

    def _protected_counts(self):
        return {
            model: self.env[model].search_count([])
            for model in (
                'res.partner', 'membership.application', 'account.move',
                'account.payment', 'membership.period',
            )
        }

    def test_empty_company_is_normal_and_has_no_business_side_effects(self):
        request = self._request(
            full_name='شخص غير موجود', national_id='UNIQUE-2A',
            medical_license_no='UNIQUE-LIC-2A',
            historical_membership_number='UNIQUE-MEM-2A', phone='0999999999',
        )
        before = self._protected_counts()
        membership_sequence = self.env['ir.sequence'].search([
            ('code', '=', 'membership.number'),
        ], limit=1)
        sequence_before = (
            membership_sequence.number_next_actual if membership_sequence else False
        )
        request.with_user(self.employee).action_search_potential_matches()
        self.assertEqual(request.match_search_state, 'no_match')
        self.assertFalse(request.match_result_ids)
        self.assertEqual(before, self._protected_counts())
        self._attach(request)
        request.with_user(self.employee).action_submit()
        self.assertEqual(request.state, 'waiting_review')
        if membership_sequence:
            self.assertEqual(membership_sequence.number_next_actual, sequence_before)

    def test_national_identifier_is_strong_and_blocks_until_reviewed(self):
        doctor = self._doctor()
        request = self._request()
        self._attach(request)
        request.with_user(self.employee).action_search_potential_matches()
        result = request.match_result_ids.filtered(lambda line: line.partner_id == doctor)
        self.assertEqual(result.level, 'strong')
        self.assertTrue(result.national_id_match)
        self.assertIn('الرقم الوطني', result.reason)
        self.assertNotEqual(result.masked_national_id, doctor.national_id)
        with self.assertRaises(UserError):
            request.with_user(self.employee).action_submit()
        result.with_user(self.employee).write({'different_reason': 'تشابه أرقام في السجل الورقي'})
        result.with_user(self.employee).action_mark_different()
        request.with_user(self.employee).action_submit()
        self.assertEqual(request.state, 'waiting_review')

    def test_same_name_different_mother_is_not_automatic_identity(self):
        self._doctor(
            national_id='OTHER-ID', medical_license_no='OTHER-LIC',
            membership_number='OTHER-MEM', mobile='0933000000',
            mother_name='أم مختلفة تمامًا',
        )
        request = self._request(
            national_id='REQUEST-ID', medical_license_no='REQUEST-LIC',
            historical_membership_number='REQUEST-MEM', phone='0911000000',
        )
        request.with_user(self.employee).action_search_potential_matches()
        result = request.match_result_ids
        self.assertEqual(result.level, 'weak')
        self.assertEqual(result.decision, 'pending')
        self.assertEqual(result.mother_full_name, 'أم مختلفة تمامًا')
        self.assertFalse(request.partner_id)

    def test_name_and_mother_with_conflicting_national_needs_manual_review(self):
        self._doctor(national_id='DIFFERENT-NATIONAL')
        request = self._request(
            national_id='REQUEST-NATIONAL', medical_license_no='OTHER-LIC',
            historical_membership_number='OTHER-MEM', phone='0911000000',
        )
        request.with_user(self.employee).action_search_potential_matches()
        result = request.match_result_ids
        self.assertEqual(result.level, 'medium')
        self.assertIn('الرقم الوطني مختلف', result.reason)
        self.assertFalse(request.partner_id)

    def test_license_and_membership_match_are_strong_in_request_company(self):
        doctor = self._doctor(national_id='OTHER-ID', mobile='0933000000')
        request = self._request(national_id='REQUEST-ID', phone='0911000000')
        request.with_user(self.employee).action_search_potential_matches()
        result = request.match_result_ids.filtered(lambda line: line.partner_id == doctor)
        self.assertEqual(result.level, 'strong')
        self.assertIn('رقم الترخيص', result.reason)
        self.assertIn('رقم العضوية', result.reason)

    def test_allowed_other_company_is_warning_and_cannot_be_selected(self):
        foreign = self._doctor(self.other_company)
        request = self._request()
        request.with_user(self.employee).action_search_potential_matches()
        result = request.match_result_ids.filtered(lambda line: line.partner_id == foreign)
        self.assertTrue(result.cross_company_warning)
        self.assertFalse(result.same_company)
        with self.assertRaises(UserError):
            result.with_user(self.employee).action_select_partner()
        self.assertFalse(request.partner_id)

    def test_unallowed_company_doctor_is_not_disclosed(self):
        forbidden_company = self.env['res.company'].create({
            'name': 'Phase 2A Forbidden Union',
        })
        forbidden = self._doctor(forbidden_company)
        request = self._request()
        request.with_user(self.employee).action_search_potential_matches()
        self.assertNotIn(forbidden, request.match_result_ids.mapped('partner_id'))

    def test_select_same_company_partner_is_explicit_and_preserves_partner(self):
        doctor = self._doctor()
        request = self._request()
        before_partner_values = doctor.read()[0]
        request.with_user(self.employee).action_search_potential_matches()
        result = request.match_result_ids.filtered(lambda line: line.partner_id == doctor)
        result.with_user(self.employee).action_select_partner()
        self.assertEqual(request.request_type, 'update_existing')
        self.assertEqual(request.partner_id, doctor)
        self.assertEqual(request.source, 'manual_profile_completion')
        self.assertEqual(
            len(request.match_result_ids.filtered(lambda line: line.decision == 'selected')),
            1,
        )
        self.assertEqual(
            request.match_result_ids.filtered(lambda line: line.decision == 'selected').partner_id,
            request.partner_id,
        )
        self.assertEqual(request.match_search_state, 'selected')
        self.assertEqual(request.match_search_summary, 'تم اختيار طبيب موجود.')
        after_partner_values = doctor.read()[0]
        self.assertEqual(before_partner_values, after_partner_values)

    def test_manual_partner_change_clears_conflicting_selection(self):
        matched = self._doctor()
        unrelated = self._doctor(
            name='طبيب آخر', arabic_name='طبيب آخر', mother_name='أم أخرى',
            national_id='OTHER-900', medical_license_no='OTHER-LIC-900',
            membership_number='OTHER-MEM-900', mobile='0900000000',
        )
        request = self._request()
        request.with_user(self.employee).action_search_potential_matches()
        request.match_result_ids.filtered(
            lambda line: line.partner_id == matched
        ).with_user(self.employee).action_select_partner()
        request.with_user(self.employee).write({'partner_id': unrelated.id})
        self.assertEqual(request.partner_id, unrelated)
        self.assertFalse(
            request.match_result_ids.filtered(lambda line: line.decision == 'selected')
        )
        self.assertNotEqual(request.match_search_state, 'selected')

    def test_manual_partner_change_selects_matching_result_only(self):
        first = self._doctor(national_id='N200100-A')
        second = self._doctor(national_id='N200100-B')
        request = self._request(national_id=False)
        request.with_user(self.employee).action_search_potential_matches()
        request.with_user(self.employee).write({
            'request_type': 'update_existing', 'partner_id': second.id,
        })
        selected = request.match_result_ids.filtered(
            lambda line: line.decision == 'selected'
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected.partner_id, second)
        self.assertNotEqual(selected.partner_id, first)

    def test_repeated_search_replaces_results_and_preserves_compatible_selection(self):
        doctor = self._doctor()
        request = self._request()
        request.with_user(self.employee).action_search_potential_matches()
        request.match_result_ids.filtered(
            lambda line: line.partner_id == doctor
        ).with_user(self.employee).action_select_partner()
        first_ids = set(request.match_result_ids.ids)
        first_count = len(first_ids)
        request.with_user(self.employee).action_search_potential_matches()
        second_ids = set(request.match_result_ids.ids)
        self.assertEqual(len(second_ids), first_count)
        self.assertFalse(first_ids & second_ids)
        self.assertEqual(len(request.match_result_ids.mapped('partner_id')), first_count)
        selected = request.match_result_ids.filtered(
            lambda line: line.decision == 'selected'
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected.partner_id, request.partner_id)

    def test_update_existing_still_requires_same_company_partner(self):
        foreign = self._doctor(self.other_company)
        with self.assertRaises(ValidationError):
            self.env['membership.profile.update'].with_user(self.employee).create({
                'request_type': 'update_existing', 'company_id': self.company.id,
                'partner_id': foreign.id, 'full_name': foreign.name,
            })
