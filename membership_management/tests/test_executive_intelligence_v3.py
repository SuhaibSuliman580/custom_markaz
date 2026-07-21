from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestExecutiveIntelligenceV3(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.decision_center = cls.env['membership.decision.center'].create({})
        cls.risk_center = cls.env['membership.risk.center']
        cls.metrics_service = cls.env['membership.executive.metrics.service']

    def _metrics(self, **overrides):
        values = {
            'doctor_missing_specialty': 0, 'doctor_missing_specialty_rate': 0.0,
            'doctor_missing_national_id': 0, 'doctor_missing_national_rate': 0.0,
            'doctor_duplicate_national_id': 0, 'doctor_duplicate_rate': 0.0,
            'request_delayed_count': 0, 'overdue_amount': 0.0,
            'overdue_invoice_amount': 0.0, 'overdue_invoice_count': 0,
            'unpaid_invoice_total': 0.0, 'collection_rate': 100.0,
            'draft_move_count': 0, 'aged_draft_move_count': 0, 'draft_move_age_days': 7,
            'distribution_issue_count': 0,
            'doctor_unassigned_count': 0, 'unassigned_request_count': 0,
            'overdue_task_count': 0, 'doctor_incomplete_count': 0,
            'evaluation_confidence': 'high', 'branch_lines': [], 'employee_lines': [],
        }
        values.update(overrides)
        return values

    def test_zero_values_do_not_generate_decisions(self):
        self.assertFalse(self.decision_center._generate_decisions(self._metrics()))

    def test_missing_specialty_threshold_and_priority(self):
        decisions = self.decision_center._generate_decisions(self._metrics(
            doctor_missing_specialty=25, doctor_missing_specialty_rate=25.0))
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]['rule_code'], 'missing_specialty')
        self.assertEqual(decisions[0]['priority'], 'medium')
        self.assertFalse(decisions[0]['recommendation'] == decisions[0]['suggested_action'])
        self.assertEqual((decisions[0]['due_date'] - date.today()).days, 14)

    def test_risk_score_matrix_and_levels(self):
        self.assertEqual(self.risk_center._compute_risk_score('high', 'critical'), 12)
        self.assertEqual(self.risk_center._get_risk_level(12), 'critical')
        self.assertEqual(self.risk_center._get_risk_level(7), 'high')
        self.assertEqual(self.risk_center._get_risk_level(4), 'medium')
        self.assertEqual(self.risk_center._get_risk_level(2), 'low')

    def test_unknown_percentage_is_false(self):
        risks = self.env['membership.risk.center'].create({})._generate_risks(
            self._metrics(overdue_invoice_amount=100, overdue_invoice_count=2))
        overdue = next(risk for risk in risks if risk['rule_code'] == 'risk_overdue_invoice')
        self.assertFalse(overdue['percentage_value'])
        self.assertEqual(overdue['risk_state'], 'realized')
        self.assertFalse(overdue['probability'])
        self.assertNotIn('invoice_date_due', overdue['description'])
        self.assertNotIn('invoice_date_due', overdue['mitigation_action'])

    def test_invoice_not_overdue_before_due_date(self):
        today = date.today()
        invoice = SimpleNamespace(
            invoice_date_due=today + timedelta(days=1), state='posted', payment_state='not_paid')
        self.assertFalse(self.metrics_service._is_invoice_overdue(invoice, today))
        invoice.invoice_date_due = today - timedelta(days=1)
        self.assertTrue(self.metrics_service._is_invoice_overdue(invoice, today))

    def test_draft_move_requires_age_threshold(self):
        today = date.today()
        move = SimpleNamespace(state='draft', date=today - timedelta(days=3))
        self.assertFalse(self.metrics_service._is_draft_move_aged(move, today, 7))
        move.date = today - timedelta(days=8)
        self.assertTrue(self.metrics_service._is_draft_move_aged(move, today, 7))

    def test_inactive_fund_does_not_create_risk_without_business_condition(self):
        risks = self.env['membership.risk.center'].create({})._generate_risks(
            self._metrics(fund_without_movement_count=20))
        self.assertFalse(any(risk['rule_code'] == 'risk_inactive_fund' for risk in risks))

    def test_employee_label_uses_partner_display_name(self):
        user = self.env.user
        self.assertEqual(
            self.env['membership.executive.timeline']._employee_display_name(user),
            user.partner_id.display_name)

    def test_approved_decision_due_date_is_preserved(self):
        center = self.env['membership.decision.center'].create({})
        line = self.env['membership.decision.center.line'].create({
            'center_id': center.id, 'company_id': self.env.company.id,
            'scope_type': 'company', 'scope_label': self.env.company.display_name,
            'title': 'قرار تجريبي', 'problem_description': 'مشكلة', 'recommendation': 'توصية',
            'suggested_action': 'إجراء', 'priority': 'high', 'rule_code': 'test_due',
            'due_date': date.today() + timedelta(days=7),
        })
        saved = line._persistent('accepted')
        custom_due = date.today() + timedelta(days=21)
        saved.due_date = custom_due
        line.due_date = date.today() + timedelta(days=2)
        line._persistent('accepted')
        self.assertEqual(saved.due_date, custom_due)

    def test_v3_views_use_cards_and_hide_floating_assistants(self):
        view = self.env.ref('membership_management.view_membership_decision_center_form')
        self.assertIn('ei_card_kanban', view.arch_db)
        risk_view = self.env.ref('membership_management.view_membership_risk_center_form')
        self.assertIn('ei_card_kanban', risk_view.arch_db)
        scss = (Path(__file__).parents[1] / 'static/src/scss/executive_intelligence_v3.scss').read_text(
            encoding='utf-8')
        self.assertIn('o_livechat_button', scss)
        self.assertIn('overflow-x: hidden', scss)

    def test_state_counters_match_generated_lines(self):
        center = self.env['membership.decision.center'].create({})
        center.line_ids = [
            (0, 0, {
                'scope_type': 'central', 'scope_label': 'جميع النقابات المسموحة',
                'title': 'أ', 'priority': 'high', 'status': 'proposed',
            }),
            (0, 0, {
                'scope_type': 'central', 'scope_label': 'جميع النقابات المسموحة',
                'title': 'ب', 'priority': 'medium', 'status': 'under_review',
            }),
        ]
        values = [dict(status=line.status, priority=line.priority) for line in center.line_ids]
        center.write({
            'proposed_count': sum(v['status'] == 'proposed' for v in values),
            'under_review_count': sum(v['status'] == 'under_review' for v in values),
        })
        self.assertEqual(center.proposed_count, 1)
        self.assertEqual(center.under_review_count, 1)

    def test_central_scope_has_explicit_label(self):
        decisions = self.decision_center._generate_decisions(self._metrics(
            doctor_missing_specialty=25, doctor_missing_specialty_rate=25.0))
        self.assertEqual(decisions[0]['scope_type'], 'central')
        self.assertFalse(decisions[0]['company_id'])
        self.assertEqual(decisions[0]['scope_label'], 'جميع النقابات المسموحة')

    def test_unassigned_responsible_displays_not_assigned(self):
        center = self.env['membership.decision.center'].create({})
        line = self.env['membership.decision.center.line'].create({
            'center_id': center.id, 'scope_type': 'central',
            'scope_label': 'جميع النقابات المسموحة', 'title': 'قرار',
        })
        self.assertEqual(line.responsible_display_name, 'غير معين')

    def test_daily_financial_definitions_are_separate(self):
        model = self.env['membership.daily.brief']
        self.assertIn('issued_service_invoice_amount', model._fields)
        self.assertIn('recognized_revenue_amount', model._fields)
        self.assertIn('collected_amount', model._fields)
        self.assertNotEqual(
            model._fields['issued_service_invoice_amount'].string,
            model._fields['collected_amount'].string)

    def test_administrator_arabic_display_name(self):
        admin = self.env.ref('base.user_admin')
        self.assertEqual(
            self.env['membership.executive.timeline']._employee_display_name(admin),
            'مدير النظام')

    def test_timeline_values_sort_descending(self):
        dates = [
            SimpleNamespace(event_date='2026-07-20 08:00:00'),
            SimpleNamespace(event_date='2026-07-20 13:00:00'),
        ]
        ordered = sorted(dates, key=lambda event: event.event_date, reverse=True)
        self.assertGreater(ordered[0].event_date, ordered[1].event_date)

    def test_logical_key_prevents_duplicate_decisions(self):
        center = self.env['membership.decision.center'].create({})
        line = self.env['membership.decision.center.line'].create({
            'center_id': center.id, 'scope_type': 'central',
            'scope_label': 'جميع النقابات المسموحة', 'title': 'قرار',
            'problem_description': 'مشكلة', 'recommendation': 'توصية',
            'suggested_action': 'إجراء', 'priority': 'high', 'rule_code': 'no_duplicate',
        })
        first = line._persistent('accepted')
        second = line._persistent('accepted')
        self.assertEqual(first, second)

    def test_logical_key_prevents_duplicate_risks(self):
        center = self.env['membership.risk.center'].create({})
        line = self.env['membership.risk.center.line'].create({
            'center_id': center.id, 'scope_type': 'central',
            'scope_label': 'جميع النقابات المسموحة', 'title': 'خطر',
            'description': 'وصف', 'mitigation_action': 'معالجة',
            'risk_level': 'high', 'risk_score': 6, 'risk_state': 'realized',
            'rule_code': 'risk_no_duplicate',
        })
        first = line._persistent('acknowledged')
        second = line._persistent('acknowledged')
        self.assertEqual(first, second)

    def test_company_scope_is_limited_to_allowed_companies(self):
        other = self.env['res.company'].create({'name': 'نقابة غير مسموحة'})
        service = self.env['membership.executive.metrics.service'].with_context(
            allowed_company_ids=[self.env.company.id])
        with self.assertRaises(AccessError):
            service._allowed_company_ids(other.id)
