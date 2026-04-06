{
    'name': 'Syndicate Revenue Distribution Reports',
    'version': '17.0.1.0.0',
    'summary': 'Reports for syndicate revenue distribution',
    'category': 'Accounting',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'product',
        'syndicate_revenue_distribution',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/revenue_distribution_report_views.xml',
    ],
    'installable': True,
    'application': False,
}