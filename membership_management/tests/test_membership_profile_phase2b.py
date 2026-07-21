import base64

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMembershipProfilePhase2B(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        group = cls.env.ref('membership_management.group_doctor_data_employee')
        internal = cls.env.ref('base.group_user')
        cls.employee = cls.env['res.users'].create({
            'name': 'Phase 2B Employee', 'login': 'phase2b.employee',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'groups_id': [(6, 0, [internal.id, group.id])],
        })
        cls.specialty = cls.env['medical.specialty'].create({
            'name': 'Phase 2B Specialty', 'code': 'PH2B', 'company_id': cls.company.id,
        })
        cls.university = cls.env['medical.unv'].create({
            'name': 'Phase 2B University', 'code': 'U2B', 'company_id': cls.company.id,
        })
        cls.doctor = cls.env['res.partner'].create({
            'name': 'أحمد سالم', 'arabic_name': 'أحمد سالم', 'father_name': 'محمود',
            'mother_name': 'فاطمة الخطيب', 'is_doctor': True,
            'company_id': cls.company.id, 'national_id': 'ID-2B-100',
            'mobile': '0944000000', 'email': 'old@example.com',
            'medical_license_no': 'LIC-2B', 'medical_specialty_id': cls.specialty.id,
            'university': cls.university.name, 'membership_number': 'MEM-2B-100',
        })

    def _request(self, request_type='update_existing', **extra):
        vals = {
            'request_type': request_type, 'company_id': self.company.id,
            'full_name': 'أحمد سالم', 'proposed_english_name': 'Ahmad Salem',
            'proposed_nickname': 'سالم', 'proposed_father_name': 'محمود',
            'proposed_mother_full_name': 'فاطمة الخطيب',
            'national_id': 'ID-2B-100', 'phone': '0944 000 000',
            'proposed_gender': 'male', 'proposed_birth_date': '1980-01-01',
            'proposed_registry_place_number': 'دمشق 2B',
            'email': 'new@example.com', 'medical_license_no': 'LIC-2B',
            'medical_specialty_id': self.specialty.id,
            'proposed_university_id': self.university.id,
            'proposed_graduation_year': '2004',
            'proposed_specialty_classification': 'specialist',
            'historical_membership_number': 'OLD-2B',
            'proposed_membership_state': 'active',
            'proposed_membership_start_date': '2005-01-01',
            'proposed_membership_end_date': '2030-12-31',
            'proposed_membership_join_date': '2005-01-01',
            'proposed_ministry_registration_number': 'MOH-2B',
            'proposed_ministry_registration_date': '2005-01-02',
            'proposed_license_type': 'permanent',
            'proposed_fund_status': 'contracted', 'proposed_union_status': 'active',
        }
        if request_type == 'update_existing':
            vals['partner_id'] = self.doctor.id
        else:
            vals.update({'national_id': 'NEW-2B-200', 'full_name': 'عضو قائم جديد'})
        vals.update(extra)
        return self.env['membership.profile.update'].with_user(self.employee).create(vals)

    def _line(self, request, field_name):
        return request.comparison_line_ids.filtered(lambda line: line.field_name == field_name)

    def test_mandatory_section_order_mapping_and_no_duplicate_fields(self):
        expected = [
            'full_name', 'proposed_english_name', 'proposed_nickname',
            'proposed_father_name', 'proposed_mother_full_name', 'national_id',
            'proposed_gender', 'proposed_birth_date', 'proposed_registry_place_number',
            'proposed_university_id', 'proposed_graduation_year',
            'proposed_specialty_classification', 'medical_specialty_id',
            'historical_membership_number', 'proposed_membership_state',
            'proposed_membership_start_date', 'proposed_membership_end_date',
            'proposed_membership_join_date',
            'proposed_ministry_registration_number',
            'proposed_ministry_registration_date', 'medical_license_no',
            'proposed_license_type', 'proposed_fund_status',
            'proposed_is_employee', 'proposed_union_status',
        ]
        request_model = self.env['membership.profile.update']
        self.assertIn('english_name', self.env['res.partner']._fields)
        self.assertIn('proposed_english_name', request_model._fields)
        self.assertIn(
            ('proposed_english_name', 'english_name', 'الاسم بالإنكليزية'),
            request_model.PROFILE_FIELD_MAPPING,
        )
        form = self.env.ref(
            'membership_management.view_membership_profile_update_form'
        )
        root = etree.fromstring(form.arch_db.encode())
        section = root.xpath(".//group[@string='البيانات الإلزامية']")[0]
        self.assertEqual(section.get('class'), 'o_profile_required_cards')
        cards = section.xpath('./group')
        self.assertEqual(
            [card.get('string') for card in cards],
            ['الهوية الشخصية', 'البيانات العلمية', 'العضوية والترخيص', 'الوضع الحالي'],
        )
        expected_columns = {
            'الهوية الشخصية': [
                ['full_name', 'proposed_nickname', 'proposed_mother_full_name',
                 'proposed_gender', 'proposed_registry_place_number'],
                ['proposed_english_name', 'proposed_father_name', 'national_id',
                 'proposed_birth_date'],
            ],
            'البيانات العلمية': [
                ['proposed_university_id', 'proposed_specialty_classification'],
                ['proposed_graduation_year', 'medical_specialty_id'],
            ],
            'العضوية والترخيص': [
                ['historical_membership_number', 'proposed_membership_state',
                 'proposed_membership_end_date',
                 'proposed_ministry_registration_date', 'proposed_license_type'],
                ['proposed_membership_join_date', 'proposed_membership_start_date',
                 'proposed_ministry_registration_number', 'medical_license_no'],
            ],
            'الوضع الحالي': [
                ['proposed_fund_status', 'proposed_is_employee'],
                ['proposed_union_status'],
            ],
        }
        for card in cards:
            columns = card.xpath('./group')
            self.assertEqual(len(columns), 2)
            self.assertEqual(
                [[field.get('name') for field in column.xpath('./field')]
                 for column in columns],
                expected_columns[card.get('string')],
            )
        for field_name in expected:
            self.assertEqual(
                len(section.xpath(".//field[@name='%s']" % field_name)), 1,
                field_name,
            )
        self.assertEqual(section.get('col'), '1')
        self.assertEqual(
            section.get('invisible'),
            "request_type not in ['onboard_existing_member', 'update_existing']",
        )
        membership_only = root.xpath(".//group[@string='تحديث رقم العضوية']")[0]
        self.assertEqual(
            membership_only.get('invisible'),
            "request_type != 'membership_number_only'",
        )
        partner_arch = self.env.ref('membership_management.view_partner_form_membership').arch_db
        self.assertNotIn('english_name', partner_arch)

    def test_full_request_reports_all_missing_fields_in_one_error(self):
        request = self.env['membership.profile.update'].with_user(self.employee).create({
            'request_type': 'update_existing', 'company_id': self.company.id,
            'partner_id': self.doctor.id,
        })
        with self.assertRaises(UserError) as error:
            request.with_user(self.employee).action_submit()
        message = str(error.exception)
        for label in ('الاسم الكامل', 'الاسم بالإنكليزية', 'مكان ورقم القيد',
                      'سنة التخرج', 'الوضع النقابي'):
            self.assertIn(label, message)

    def test_comparison_new_modified_unchanged_and_not_entered(self):
        request = self._request(proposed_city='دمشق')
        self.assertEqual(self._line(request, 'full_name').difference_state, 'unchanged')
        self.assertEqual(self._line(request, 'email').difference_state, 'modified')
        self.assertEqual(self._line(request, 'proposed_city').difference_state, 'new')
        self.assertEqual(self._line(request, 'proposed_subspecialty_id').difference_state, 'not_entered')
        self.assertEqual(self._line(request, 'proposed_mother_full_name').current_value, 'فاطمة الخطيب')

    def test_partner_change_rebuilds_comparison_without_losing_proposals(self):
        other = self.env['res.partner'].create({
            'name': 'طبيب آخر', 'is_doctor': True, 'company_id': self.company.id,
            'mother_name': 'أم أخرى', 'email': 'other@example.com',
        })
        request = self._request(proposed_city='حلب')
        request.with_user(self.employee).write({'partner_id': other.id})
        self.assertEqual(request.proposed_city, 'حلب')
        self.assertTrue(request.comparison_warning)
        self.assertEqual(self._line(request, 'email').current_value, 'other@example.com')
        self.assertFalse(request.match_result_ids.filtered(lambda line: line.decision == 'selected'))

    def test_onchange_shows_current_profile_without_copying_it_to_proposals(self):
        request = self.env['membership.profile.update'].with_user(self.employee).new({
            'request_type': 'membership_number_only', 'company_id': self.company.id,
            'partner_id': self.doctor.id,
        })
        request._onchange_partner_current_data()
        current_membership = request.comparison_line_ids.filtered(
            lambda line: line.field_name == 'historical_membership_number'
        )
        current_email = request.comparison_line_ids.filtered(
            lambda line: line.field_name == 'email'
        )
        self.assertEqual(current_membership.current_value, 'MEM-2B-100')
        self.assertEqual(current_email.current_value, 'old@example.com')
        self.assertFalse(request.historical_membership_number)
        self.assertFalse(request.email)

    def test_onchange_partner_change_keeps_proposal_and_shows_new_current_values(self):
        other = self.env['res.partner'].create({
            'name': 'طبيب ثان', 'is_doctor': True, 'company_id': self.company.id,
            'membership_number': 'MEM-SECOND', 'email': 'second@example.com',
        })
        request = self.env['membership.profile.update'].with_user(self.employee).new({
            'request_type': 'update_existing', 'company_id': self.company.id,
            'partner_id': self.doctor.id,
            'historical_membership_number': 'MEM-PROPOSED',
        })
        request._onchange_partner_current_data()
        request.partner_id = other
        request._onchange_partner_current_data()
        membership = request.comparison_line_ids.filtered(
            lambda line: line.field_name == 'historical_membership_number'
        )
        self.assertEqual(membership.current_value, 'MEM-SECOND')
        self.assertEqual(membership.proposed_value, 'MEM-PROPOSED')
        self.assertEqual(request.historical_membership_number, 'MEM-PROPOSED')

    def test_copy_current_data_changes_request_only(self):
        request = self._request(email='manual@example.com')
        before = self.doctor.read()[0]
        request.with_user(self.employee).action_copy_current_data()
        self.assertEqual(request.email, self.doctor.email)
        self.assertEqual(request.proposed_university_id, self.university)
        self.assertEqual(before, self.doctor.read()[0])

    def test_document_is_owned_by_request(self):
        request = self._request()
        document = self.env['membership.profile.document'].with_user(self.employee).create({
            'request_id': request.id, 'document_type': 'medical_license',
            'file_name': 'license.pdf', 'file_data': base64.b64encode(b'pdf-data'),
            'employee_note': 'نسخة ورقية ممسوحة',
        })
        self.assertEqual(document.request_id, request)
        self.assertFalse(document._fields.get('partner_id'))

    def test_onboarding_full_profile_submits_without_partner_or_side_effects(self):
        request = self._request('onboard_existing_member')
        attachment = self.env['ir.attachment'].create({
            'name': 'proof.pdf', 'type': 'binary', 'datas': base64.b64encode(b'proof'),
            'res_model': request._name, 'res_id': request.id,
        })
        request.with_user(self.employee).write({
            'membership_evidence_attachment_ids': [(4, attachment.id)],
        })
        protected = {
            model: self.env[model].search_count([])
            for model in ('res.partner', 'membership.application', 'membership.period', 'account.move', 'account.payment')
        }
        membership_sequence = self.env['ir.sequence'].search([('code', '=', 'membership.number')], limit=1)
        sequence_before = membership_sequence.number_next_actual if membership_sequence else False
        request.with_user(self.employee).action_submit()
        self.assertEqual(request.state, 'waiting_review')
        self.assertFalse(request.partner_id)
        for model, count in protected.items():
            self.assertEqual(self.env[model].search_count([]), count)
        if membership_sequence:
            self.assertEqual(membership_sequence.number_next_actual, sequence_before)

    def test_national_id_placeholder_is_rejected_only_on_submit(self):
        request = self._request(national_id='000000')
        self.assertEqual(request.state, 'draft')
        with self.assertRaises(Exception):
            request.with_user(self.employee).action_submit()

    def test_membership_number_only_can_submit_using_current_required_profile(self):
        before = self.doctor.read()[0]
        request = self.env['membership.profile.update'].with_user(self.employee).create({
            'request_type': 'membership_number_only', 'company_id': self.company.id,
            'partner_id': self.doctor.id,
            'historical_membership_number': 'MEM-2B-NEW',
        })
        request.with_user(self.employee).action_submit()
        self.assertEqual(request.state, 'waiting_review')
        self.assertEqual(request.historical_membership_number, 'MEM-2B-NEW')
        self.assertEqual(request.current_membership_number, 'MEM-2B-100')
        self.assertEqual(before, self.doctor.read()[0])

    def test_reference_data_from_unallowed_company_cannot_be_selected(self):
        other_company = self.env['res.company'].create({'name': 'Phase 2B Forbidden Company'})
        foreign_university = self.env['medical.unv'].with_company(other_company).create({
            'name': 'Forbidden University', 'company_id': other_company.id,
        })
        request = self._request()
        with self.assertRaises(Exception):
            request.with_user(self.employee).write({
                'proposed_university_id': foreign_university.id,
            })
