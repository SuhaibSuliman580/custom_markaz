from datetime import datetime, timedelta
from types import SimpleNamespace

from odoo.tests.common import TransactionCase


class TestMembershipCommandCenter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.center_model = cls.env['membership.command.center']

    def test_branch_evaluation_is_ratio_based(self):
        self.assertEqual(
            self.center_model._evaluate_branch_performance(
                95.0, 2.0, False, doctor_count=50, has_operational_data=True,
            ),
            'excellent',
        )
        self.assertEqual(
            self.center_model._evaluate_branch_performance(
                70.0, 20.0, True, doctor_count=50, has_operational_data=True,
            ),
            'follow_up',
        )
        self.assertEqual(
            self.center_model._evaluate_branch_performance(
                40.0, 50.0, True, doctor_count=50, has_operational_data=True,
            ),
            'struggling',
        )

    def test_empty_branch_has_insufficient_data(self):
        self.assertEqual(
            self.center_model._evaluate_branch_performance(
                0.0, 0.0, False, doctor_count=0, has_operational_data=False,
            ),
            'insufficient_data',
        )

    def test_two_doctors_one_complete_is_fifty_percent(self):
        self.assertEqual(self.center_model._bounded_percentage(1, 2), 50.0)

    def test_empty_company_completion_is_zero(self):
        self.assertEqual(self.center_model._bounded_percentage(0, 0), 0.0)

    def test_percentage_never_exceeds_one_hundred(self):
        self.assertEqual(self.center_model._bounded_percentage(5, 2), 100.0)
        self.assertEqual(self.center_model._bounded_percentage(-1, 2), 0.0)

    def test_health_score_is_bounded(self):
        score = self.center_model._compute_health_score(
            100.0, 0, 0, 0.0, 0.0, 0, 0, 0, 0, 0,
        )
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_missing_activity_does_not_award_full_points(self):
        details = self.center_model._health_score_details(
            64.0, 0, 0, 0.0, 0.0, 0, 0, 0, 0, 0,
            has_data_quality=True, has_transactions=False, has_financial=False,
            has_tasks=False, has_alerts=True,
        )
        self.assertLess(details['health_score'], 89.0)
        self.assertEqual(details['transaction_score'], 0.0)
        self.assertEqual(details['financial_score'], 0.0)
        self.assertEqual(details['task_score'], 0.0)
        self.assertEqual(details['evaluation_confidence'], 'low')

    def test_health_components_are_bounded(self):
        details = self.center_model._health_score_details(
            150.0, 10, 0, 100.0, 200.0, 0, 0, 10, 0, 0,
            has_data_quality=True, has_transactions=True, has_financial=True,
            has_tasks=True, has_alerts=True,
        )
        for field_name, maximum in (
            ('data_quality_score', 30.0), ('transaction_score', 25.0),
            ('financial_score', 20.0), ('task_score', 15.0), ('alert_score', 10.0),
        ):
            self.assertGreaterEqual(details[field_name], 0.0)
            self.assertLessEqual(details[field_name], maximum)
        self.assertLessEqual(details['health_score'], 100.0)

    def test_zero_count_alerts_are_not_returned(self):
        commands = self.center_model._prepare_alert_lines(
            self.env['membership.service.request'],
            self.env['account.move'],
            self.env['mail.activity'],
            doctors=self.env['res.partner'],
        )
        self.assertFalse(commands)

    def test_branch_doctors_plus_unassigned_equal_total(self):
        self.assertTrue(self.center_model._doctor_counts_reconcile(5754, 5752, 2))
        self.assertFalse(self.center_model._doctor_counts_reconcile(5754, 2, 0))

    def test_empty_branch_has_no_health_score(self):
        values = self.center_model._empty_branch_score_values()
        self.assertFalse(values['branch_health_score'])
        self.assertFalse(values['has_health_score'])
        self.assertEqual(values['performance_state'], 'insufficient_data')

    def test_collection_rate_uses_amounts_and_is_bounded(self):
        invoices = [
            SimpleNamespace(amount_total=100.0, amount_residual=25.0),
            SimpleNamespace(amount_total=50.0, amount_residual=0.0),
        ]
        due, collected, rate = self.center_model._collection_amounts(invoices)
        self.assertEqual(due, 150.0)
        self.assertEqual(collected, 125.0)
        self.assertAlmostEqual(rate, 83.333333, places=5)
        _due, _collected, capped = self.center_model._collection_amounts([
            SimpleNamespace(amount_total=100.0, amount_residual=-20.0),
        ])
        self.assertEqual(capped, 100.0)

    def test_financial_amounts_are_distinct_and_due_date_drives_overdue(self):
        reference = datetime(2026, 7, 20).date()
        period = [
            SimpleNamespace(amount_residual=40.0, invoice_date_due=reference + timedelta(days=2)),
        ]
        outstanding = period + [
            SimpleNamespace(amount_residual=75.0, invoice_date_due=reference - timedelta(days=1)),
            SimpleNamespace(amount_residual=25.0, invoice_date_due=reference),
        ]
        unpaid_period, total_outstanding, overdue = self.center_model._financial_amounts(
            period, outstanding, reference,
        )
        self.assertEqual(unpaid_period, 40.0)
        self.assertEqual(total_outstanding, 140.0)
        self.assertEqual(overdue, 75.0)

    def test_average_duration_excludes_open_and_invalid_requests(self):
        start = datetime(2026, 1, 1, 8, 0, 0)
        requests = [
            SimpleNamespace(started_date=start, completed_date=start + timedelta(hours=2)),
            SimpleNamespace(started_date=start, completed_date=False),
            SimpleNamespace(started_date=start, completed_date=start - timedelta(minutes=1)),
        ]
        self.assertEqual(self.center_model._valid_completion_hours(requests), [2.0])

    def test_doctor_action_uses_same_scope_domain_as_kpi(self):
        center = self.center_model.create({})
        expected = self.center_model._doctor_scope_domain(
            self.env.companies.ids, include_unassigned=True,
        )
        self.assertEqual(center.action_open_doctors()['domain'], expected)

    def test_company_filter_rejects_unallowed_company(self):
        foreign = self.env['res.company'].create({'name': 'شركة غير مسموحة'})
        with self.assertRaises(Exception):
            self.center_model._allowed_company_ids(foreign)

    def test_quality_domain_uses_existing_doctor_fields(self):
        domains = self.center_model._doctor_quality_domains(self.env.companies.ids)
        self.assertIn(('is_doctor', '=', True), domains['base'])
        self.assertIn(('national_id', '=', False), domains['incomplete'])

    def test_quality_metrics_use_separate_elements_and_percent_sign(self):
        arch = self.env.ref(
            'membership_management.view_membership_command_center_form'
        ).arch_db
        self.assertIn('cc_metric_count', arch)
        self.assertIn('cc_metric_rate', arch)
        self.assertIn('cc_percent_sign', arch)
        self.assertIn('%', arch)
        self.assertNotIn('doctor_complete_display', arch)
