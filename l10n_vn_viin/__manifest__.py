{
    'name': 'Vietnam Chart of Accounts - Circular 200 and 133',
    'name_vi_VN': 'Hệ thống Tài khoản theo thông tư 200 và 133',
    'old_technical_name': 'l10n_vn_common',

    'summary': 'Vietnam Chart of Accounts according to Circular #200/2014/TT-BTC and #133/2016/TT-BTC by the Ministry of Finance',
    'summary_vi_VN': 'Hoạch đồ kế toán Việt Nam theo thông tư 200/2014/TT-BTC và 133/2016/TT-BTC',

    'description': """
Demo video: `Vietnam Chart of Accounts - Circular 200 and 133 <https://youtu.be/5S7xbN5Ok_Y>`_

What it does
============
This module allows:

* The l10n_vn_viin module gets fully compliant with Circular No. 200/2014/TT-BTC and Circular No. 133/2016/TT-BTC issued by the Ministry of Finance.
* More common taxes (VAT on imported goods, VAT Exemption, etc.).
* Full Chart of Accounts according to Circular No. 200 and Circular No. 133.
* New account tag data has been added to use similarly to parent view accounts. For example, the accountant can group all accounts 111xxx by using the account tag 111.
* Add analytic tags.
* Allow to print the Journal Entries in PDF.
* Print Payment Receipts in PDF according to the following templates released under Circular No. 200/2014/TT-BTC and the Circular No. 133/2016/TT-BTC of the Ministry of Finance.

  * Template 01-TT: for receiving payments.
  * Template 02-TT: for sending payments.

Supported Editions
==================
1. Community Edition
2. Enterprise Edition

""",

    'description_vi_VN': """
Demo video: `Hệ thống Tài khoản theo thông tư 200 và 133 <https://youtu.be/5S7xbN5Ok_Y>`_

Ứng dụng này làm gì
===================
Mô đun này cho phép:

* Mô-đun l10n_vn_viin tuân thủ Thông tư số 200/2014/TT-BTC và thông tư 133/2016/TT-BTC của Bộ Tài chính.
* Bổ sung một số loại thuế (không thuộc đối tượng chịu thuế GTGT, thuế GTGT hàng nhập khẩu).
* Hệ thống tài khoản kế toán đầy đủ theo thông tư 200 và 133.
* Thêm các thẻ kế toán để sử dụng theo cách tương tự với các tài khoản kiểu cha. Ví dụ: kế toán hiện có thể nhóm tất cả các tài khoản 111xxx bằng tài khoản thẻ 111.
* Thêm các thẻ kế toán quản trị.
* Cho phép in phiếu kế toán theo định dạng PDF.
* Cung cấp phiên bản Pdf Phiếu Thu/Chi, Giấy báo Nợ/Có tuân thủ Thông tư số 200 và Thông tư 133 của Bộ Tài chính Việt Nam.

  * Mẫu số 01-TT: Các thanh toán nhận.
  * Mẫu số  02-TT: Các thanh toán gửi.

Ấn bản được hỗ trợ
==================
1. Ấn bản Community
2. Ấn bản Enterprise

""",

    'author': 'Viindoo',
    'website': 'https://viindoo.com/apps/app/17.0/l10n_vn_viin',
    'live_test_url': "https://v17demo-int.viindoo.com",
    'live_test_url_vi_VN': "https://v17demo-vn.viindoo.com",
    'demo_video_url': "https://youtu.be/5S7xbN5Ok_Y",
    'support': 'apps.support@viindoo.com',
    'countries': ['vn'],
    'category': 'Accounting/Localizations/Account Charts',
    'version': '0.2.3',
    'depends': [
        'l10n_vn',
        'viin_account',
    ],
    'data': [
        'data/account_account_tag_data.xml',
        'data/account_tax_report_line_data.xml',
        'data/report_paperformat_data.xml',
        'views/root_menu.xml',
        'views/ir_actions_report_views.xml',
        'views/report_accounting_external_header_left_layout.xml',
        'views/report_accounting_external_footer_layout.xml',
        'views/report_accounting_external_layout_standard.xml',
        'views/report_accounting_circular_external_layout_standard.xml',
        'views/report_common_templates.xml',
        'views/report_accounting_circular_desc_layout.xml',
        'views/account_payment_views.xml',
        'views/report_account_move.xml',
        'views/report_account_payment.xml',
        'views/report.xml',
    ],
    'images': [
        'static/description/main_screenshot.png'
        ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': ['l10n_vn'],
    'price': 27,
    'currency': 'EUR',
    'license': 'OPL-1',
}
