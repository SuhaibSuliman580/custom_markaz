# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Advance POS Multi Branch-Unit Operation Setup',
    'version': '17.0.0.0',
    'category': 'Point Of Sale',
    'summary': 'POS Advance Multiple Branch advance Multi Branch for POS multi branch sequence branch address on pos report branch logo on pos report sale branch Purchase branch Invoicing branch logo on Accounting Report logo Multi branch sequence branch logo on pos',
    "description": """
    	This odoo app helps user to cerate and set multiple branch management for all applications like POS, Sales, Purchase Inventory and Invoicing, selected branch will appear on related documents and report will printe with branch header and footer.
    
    """,
    'author': "BrowseInfo",
    "website" : "https://www.browseinfo.com",
    'price': 50,
    'currency': "EUR",
    'depends': ['base', 'point_of_sale','bi_branch_pos','bi_advance_branch'],
    "data": ['views/pos_view.xml',],
    'assets': {
        'point_of_sale._assets_pos': [
            'bi_advance_branch_pos/static/src/xml/**/*',
        ],
    },
    "auto_install": False,
    'installable': True,
    'live_test_url':'https://youtu.be/NZ5y2uu7rw4',
    "images":['static/description/Banner.gif'],
    'license': 'LGPL-3',
}
