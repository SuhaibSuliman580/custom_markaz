import base64

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestMembershipProfileUpdatePhase1(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({
            'name': 'Doctor Data Other Company',
        })
        cls.employee_group = cls.env.ref(
            'membership_management.group_doctor_data_employee'
        )
        cls.reviewer_group = cls.env.ref(
            'membership_management.group_doctor_data_reviewer'
        )
        cls.admin_group = cls.env.ref(
            'membership_management.group_membership_admin'
        )
        internal_group = cls.env.ref('base.group_user')

        cls.employee = cls.env['res.users'].create({
            'name': 'Doctor Data Employee',
            'login': 'doctor.data.employee.phase1',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'groups_id': [(6, 0, [internal_group.id, cls.employee_group.id])],
        })
        cls.reviewer = cls.env['res.users'].create({
            'name': 'Doctor Data Reviewer',
            'login': 'doctor.data.reviewer.phase1',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'groups_id': [(6, 0, [internal_group.id, cls.reviewer_group.id])],
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Membership Manager Phase1',
            'login': 'membership.manager.phase1',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'groups_id': [(6, 0, [internal_group.id, cls.admin_group.id])],
        })
        cls.specialty = cls.env['medical.specialty'].create({
            'name': 'Phase 1 Specialty',
            'code': 'PH1',
            'company_id': cls.company.id,
        })
        cls.doctor = cls.env['res.partner'].create({
            'name': 'Existing Doctor Phase 1',
            'is_doctor': True,
            'company_id': cls.company.id,
            'national_id': '0012345678',
            'phone': '5551000',
            'medical_license_no': 'LIC-PH1',
            'medical_specialty_id': cls.specialty.id,
        })

    def _existing_vals(self):
        return {
            'name': 'UPD-PH1',
            'request_type': 'update_existing',
            'partner_id': self.doctor.id,
            'company_id': self.company.id,
            'full_name': self.doctor.name,
            'proposed_mother_full_name': 'Phase 1 Mother Family',
            'national_id': self.doctor.national_id,
            'phone': self.doctor.phone,
            'medical_license_no': self.doctor.medical_license_no,
            'medical_specialty_id': self.specialty.id,
        }

    def _onboarding_vals(self):
        return {
            'name': 'ONB-PH1',
            'request_type': 'onboard_existing_member',
            'company_id': self.company.id,
            'full_name': 'Historical Member Phase 1',
            'proposed_mother_full_name': 'Historical Mother Family',
            'national_id': '0098765432',
            'phone': '5552000',
            'medical_license_no': 'OLD-LIC-PH1',
            'medical_specialty_id': self.specialty.id,
            'historical_membership_number': '00042',
            'proposed_union_status': 'active',
            'officer_notes': 'Historical membership record reviewed.',
        }

    def _create_existing(self):
        return self.env['membership.profile.update'].with_user(
            self.employee
        ).create(self._existing_vals())

    def _create_onboarding(self):
        return self.env['membership.profile.update'].with_user(
            self.employee
        ).create(self._onboarding_vals())

    def _attach_evidence(self, request):
        attachment = self.env['ir.attachment'].create({
            'name': 'historical-membership.pdf',
            'type': 'binary',
            'datas': base64.b64encode(b'Phase 1 membership evidence'),
            'res_model': request._name,
            'res_id': request.id,
        })
        request.with_user(self.employee).write({
            'membership_evidence_attachment_ids': [(4, attachment.id)],
        })
        return attachment

    def test_create_update_existing_requires_partner(self):
        request = self._create_existing()
        self.assertEqual(request.partner_id, self.doctor)
        self.assertEqual(request.source, 'manual_profile_completion')

        vals = self._existing_vals()
        vals.pop('partner_id')
        vals['name'] = 'UPD-NO-PARTNER'
        with self.assertRaises(ValidationError):
            self.env['membership.profile.update'].with_user(
                self.employee
            ).create(vals)

    def test_create_onboarding_without_partner(self):
        request = self._create_onboarding()
        self.assertFalse(request.partner_id)
        self.assertEqual(
            request.source, 'manual_existing_member_onboarding',
        )

    def test_source_follows_type_and_cannot_be_edited_manually(self):
        onchange_record = self.env['membership.profile.update'].new({
            'request_type': 'onboard_existing_member',
        })
        onchange_record._onchange_request_type()
        self.assertEqual(
            onchange_record.source, 'manual_existing_member_onboarding',
        )

        onboarding = self.env['membership.profile.update'].with_user(
            self.employee
        ).create(dict(
            self._onboarding_vals(),
            name='ONB-SOURCE',
            source='manual_profile_completion',
        ))
        self.assertEqual(
            onboarding.source, 'manual_existing_member_onboarding',
        )

        existing = self._create_existing()
        with self.assertRaises(AccessError):
            existing.with_user(self.employee).write({
                'source': 'manual_existing_member_onboarding',
            })

        existing.with_user(self.employee).write({
            'request_type': 'onboard_existing_member',
            'partner_id': False,
        })
        self.assertEqual(
            existing.source, 'manual_existing_member_onboarding',
        )
        existing.with_user(self.employee).write({
            'request_type': 'update_existing',
            'partner_id': self.doctor.id,
        })
        self.assertEqual(existing.source, 'manual_profile_completion')

    def test_request_type_cannot_change_after_submission(self):
        request = self._create_existing()
        request.with_user(self.employee).action_submit()
        with self.assertRaises(AccessError):
            request.with_user(self.employee).write({
                'request_type': 'onboard_existing_member',
                'partner_id': False,
            })

    def test_state_labels_are_stabilized_in_arabic(self):
        selection = dict(
            self.env['membership.profile.update']._fields['state'].selection
        )
        self.assertEqual(selection, {
            'draft': 'مسودة',
            'waiting_documents': 'بانتظار الوثائق',
            'waiting_review': 'بانتظار المراجعة',
            'returned': 'معاد للتصحيح',
            'approved': 'تمت الموافقة',
            'cancelled': 'ملغى',
        })

    def test_doctor_list_display_uses_collected_full_name_not_numeric_placeholder(self):
        numeric_doctor = self.env['res.partner'].create({
            'name': '3',
            'is_doctor': True,
            'company_id': self.company.id,
        })
        request = self.env['membership.profile.update'].with_user(
            self.employee
        ).create(dict(
            self._existing_vals(),
            name='UPD-NUMERIC-NAME',
            partner_id=numeric_doctor.id,
            full_name='الطبيب الكامل',
        ))
        self.assertEqual(request.partner_id, numeric_doctor)
        self.assertEqual(request.doctor_display_name, 'الطبيب الكامل')

        onboarding = self._create_onboarding()
        self.assertFalse(onboarding.doctor_display_name)

    def test_reference_uses_profile_update_sequence_after_save(self):
        vals = self._existing_vals()
        vals.pop('name')
        request = self.env['membership.profile.update'].with_user(
            self.employee
        ).create(vals)
        self.assertNotEqual(request.name, 'New')
        self.assertTrue(request.name.startswith('DCR-'))

    def test_company_must_be_allowed_and_match_existing_doctor(self):
        vals = self._onboarding_vals()
        vals['name'] = 'ONB-FOREIGN'
        vals['company_id'] = self.other_company.id
        with self.assertRaises(AccessError):
            self.env['membership.profile.update'].with_user(
                self.employee
            ).create(vals)

        employee_both = self.employee.with_user(self.env.user)
        employee_both.write({
            'company_ids': [(4, self.other_company.id)],
        })
        vals = self._existing_vals()
        vals['name'] = 'UPD-WRONG-COMPANY'
        vals['company_id'] = self.other_company.id
        with self.assertRaises(ValidationError):
            self.env['membership.profile.update'].with_user(
                self.employee
            ).create(vals)

    def test_submit_return_edit_and_resubmit(self):
        request = self._create_existing()
        request.with_user(self.employee).action_submit()
        self.assertEqual(request.state, 'waiting_review')
        self.assertEqual(request.submitted_by_id, self.employee)

        with self.assertRaises(UserError):
            request.with_user(self.reviewer).action_return()

        request.with_user(self.reviewer).write({
            'return_reason': 'Correct the supporting details.',
        })
        request.with_user(self.reviewer).action_return()
        self.assertEqual(request.state, 'returned')

        request.with_user(self.employee).write({'phone': '5551001'})
        request.with_user(self.employee).action_submit()
        self.assertEqual(request.state, 'waiting_review')
        self.assertEqual(request.phone, '5551001')

    def test_waiting_documents_can_resume_completion(self):
        request = self._create_existing()
        request.with_user(self.employee).action_waiting_documents()
        self.assertEqual(request.state, 'waiting_documents')
        with self.assertRaises(AccessError):
            request.with_user(self.employee).write({'phone': '5553000'})
        request.with_user(self.employee).action_resume()
        self.assertEqual(request.state, 'draft')
        request.with_user(self.employee).write({'phone': '5553000'})
        self.assertEqual(request.phone, '5553000')

    def test_onboarding_evidence_is_required_only_on_submit(self):
        onboarding = self._create_onboarding()
        self.assertFalse(onboarding.membership_evidence_attachment_ids)
        with self.assertRaises(UserError):
            onboarding.with_user(self.employee).action_submit()

        self._attach_evidence(onboarding)
        onboarding.with_user(self.employee).action_submit()
        self.assertEqual(onboarding.state, 'waiting_review')
        with self.assertRaises(AccessError):
            onboarding.with_user(self.employee).write({
                'membership_evidence_attachment_ids': [(5, 0, 0)],
            })

        onboarding.with_user(self.reviewer).write({
            'return_reason': 'Replace the membership evidence.',
        })
        onboarding.with_user(self.reviewer).action_return()
        onboarding.with_user(self.employee).write({
            'membership_evidence_attachment_ids': [(5, 0, 0)],
        })
        self.assertFalse(onboarding.membership_evidence_attachment_ids)

        existing = self._create_existing()
        existing.with_user(self.employee).action_submit()
        self.assertEqual(existing.state, 'waiting_review')

    def test_onboarding_approval_does_not_create_partner(self):
        request = self._create_onboarding()
        self._attach_evidence(request)
        partner_count = self.env['res.partner'].search_count([])
        request.with_user(self.employee).action_submit()
        request.with_user(self.reviewer).action_approve()
        self.assertEqual(request.state, 'approved')
        self.assertFalse(request.partner_id)
        self.assertEqual(
            self.env['res.partner'].search_count([]), partner_count,
        )

    def test_employee_cannot_approve_and_submitter_cannot_approve(self):
        request = self._create_existing()
        request.with_user(self.employee).action_submit()
        with self.assertRaises(AccessError):
            request.with_user(self.employee).action_approve()
        with self.assertRaises(AccessError):
            request.with_user(self.employee).with_context(
                profile_update_workflow_token=True,
            ).write({'state': 'approved'})

        own_request = self.env['membership.profile.update'].with_user(
            self.manager
        ).create(dict(self._existing_vals(), name='UPD-MANAGER-OWN'))
        own_request.with_user(self.manager).action_submit()
        with self.assertRaises(AccessError):
            own_request.with_user(self.manager).action_approve()

    def test_approve_is_request_only_and_is_immutable(self):
        request = self._create_existing()
        before_partner = {
            field_name: self.doctor[field_name]
            for field_name in (
                'name',
                'national_id',
                'phone',
                'medical_license_no',
                'medical_specialty_id',
                'doctor_membership_state',
                'membership_number',
            )
        }
        models = (
            'membership.application',
            'membership.period',
            'account.move',
            'account.payment',
        )
        before_counts = {
            model_name: self.env[model_name].search_count([])
            for model_name in models
        }
        membership_sequence = self.env['ir.sequence'].search([
            ('code', '=', 'membership.number'),
        ], limit=1)
        before_sequence = (
            membership_sequence.number_next_actual
            if membership_sequence else False
        )

        request.with_user(self.employee).action_submit()
        request.with_user(self.reviewer).action_approve()
        self.assertEqual(request.state, 'approved')
        self.assertEqual(request.reviewer_id, self.reviewer)

        for field_name, old_value in before_partner.items():
            self.assertEqual(self.doctor[field_name], old_value)
        for model_name, count in before_counts.items():
            self.assertEqual(self.env[model_name].search_count([]), count)
        if membership_sequence:
            self.assertEqual(
                membership_sequence.number_next_actual, before_sequence,
            )

        with self.assertRaises(AccessError):
            request.with_user(self.reviewer).write({'return_reason': 'No'})
        with self.assertRaises(UserError):
            request.with_user(self.reviewer).action_approve()

    def test_cancelled_request_is_immutable(self):
        request = self._create_onboarding()
        request.with_user(self.employee).write({
            'cancellation_reason': 'Duplicate paper request.',
        })
        request.with_user(self.employee).action_cancel()
        self.assertEqual(request.state, 'cancelled')
        with self.assertRaises(AccessError):
            request.with_user(self.employee).write({'phone': '5559999'})

    def test_missing_national_id_requires_exception_and_support(self):
        vals = self._onboarding_vals()
        vals.update({
            'name': 'ONB-NO-NATIONAL',
            'national_id': False,
            'national_id_exception_reason': False,
            'officer_notes': False,
        })
        request = self.env['membership.profile.update'].with_user(
            self.employee
        ).create(vals)
        with self.assertRaises(UserError):
            request.with_user(self.employee).action_submit()

        request.with_user(self.employee).write({
            'national_id_exception_reason': 'Legacy file has no National ID.',
        })
        self._attach_evidence(request)
        request.with_user(self.employee).action_submit()
        self.assertEqual(request.state, 'waiting_review')
        request.with_user(self.reviewer).action_approve()
        self.assertEqual(request.state, 'approved')

    def test_legacy_defaults_preserve_update_semantics(self):
        request = self.env['membership.profile.update'].with_user(
            self.employee
        ).create({
            'name': 'LEGACY-PH1',
            'partner_id': self.doctor.id,
            'company_id': self.company.id,
        })
        self.assertEqual(request.request_type, 'update_existing')
        self.assertEqual(request.source, 'manual_profile_completion')
        self.assertEqual(request.company_id, self.doctor.company_id)

    def test_form_uses_standard_chatter_without_technical_lists(self):
        arch = self.env.ref(
            'membership_management.view_membership_profile_update_form'
        ).arch_db
        self.assertIn('<chatter', arch)
        self.assertNotIn('name="message_ids"', arch)
        self.assertNotIn('name="message_follower_ids"', arch)
        self.assertNotIn('name="activity_ids"', arch)
        self.assertNotIn('string="Chatter"', arch)
        self.assertIn('action_submit_for_review', arch)
        self.assertIn('action_resume', arch)
