{
    'name': 'Membership Management',
    'version': '17.0.1.0.0',
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
    ],
    'data': [
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/product_data.xml',
        'data/cron_data.xml',
        'data/mail_template_data.xml',
        'views/membership_application_views.xml',
        'views/membership_period_views.xml',
        'views/res_partner_views.xml',
        'views/medical_specialty_views.xml',
        'views/menu_views.xml',
        'views/portal_templates.xml',

        'report/membership_card_report.xml',
        'report/membership_card_template.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
}
