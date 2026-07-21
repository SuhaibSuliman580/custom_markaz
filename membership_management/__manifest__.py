{
    'name': 'Membership Management',
    'version': '17.0.3.4.0',
    'category': 'Membership',
    'summary': 'Manage doctor membership lifecycle with applications, invoicing, and portal.',
    'description': """
Membership Management Module
=============================
Manage the full lifecycle of doctor memberships:
- Membership application submission and review
- Invoice generation on approval
- Activation only after payment
- Annual membership periods with renewal
- Doctor portal for self-service
- Membership card generation (QR + PDF)
    """,
    'author': 'Custom',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'portal',
        'mail',
        'product',
        'odoo_invoice_service_template_17',
        'syndicate_revenue_distribution',
    ],
    'data': [
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/service_request_sequence.xml',
        'data/product_data.xml',
        'data/config_parameters.xml',
        'data/cron_data.xml',
        'data/mail_template_data.xml',
        'views/membership_application_views.xml',
        'views/membership_period_views.xml',
        'views/membership_service_type_views.xml',
        'views/membership_service_request_views.xml',
        'views/membership_registration_workspace_views.xml',
        'views/membership_financial_workspace_views.xml',
        'views/doctor_360_views.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'views/medical_specialty_views.xml',
        'views/res_config_settings_views.xml',
        'views/membership_renewal_wizard_views.xml',
        'views/medical_unv_views.xml',
        'views/membership_profile_update_views.xml',
        'views/membership_cashier_dashboard_views.xml',
        'views/command_center_views.xml',
        'views/executive_intelligence_v3_views.xml',
        'views/menu_views.xml',
        'views/executive_intelligence_menu.xml',
        'views/portal_templates.xml',

        'report/membership_card_report.xml',
        'report/membership_card_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'membership_management/static/src/scss/command_center.scss',
            'membership_management/static/src/scss/command_center_v2.scss',
            'membership_management/static/src/scss/executive_intelligence_v3.scss',
            'membership_management/static/src/scss/profile_required_fields.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,

    'post_init_hook': 'post_init_hook',
}
