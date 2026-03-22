{
    'name': 'Syndicate Revenue Distribution',
    'version': '17.0.1.0.0',
    'summary': 'Revenue distribution by percentages for syndicates',
    'category': 'Accounting',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/fund_box_views.xml',
        'views/product_template_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}