{
    'name': "Employee Relatives",
    'name_vi_VN': 'Người thân của nhân viên',
    'summary': """
Store employee's relatives information""",
    'summary_vi_VN': """
Lưu trữ thông tin người thân của nhân viên""",
    'description': """
Demo video: `Employee Relatives <https://youtu.be/WyJYDgH46Nc>`_


What it does
============

Are you having difficulty in finding employees' relatives in ERP software? This module will solve your problem with the following features:

#. Store employees' relative information for emergencies.
#. The employees' relative information will be in the Employee app once the module is installed.

Key Features
============
* Easy input relatives' information in the standard employee form. This information is only maintained and visible by users having the HR Officer role.
* Search for employees who have relatives or not.
* On the Contact app, allow to filter out who are the relatives of the company's employees.


Supported Editions
==================
1. Community Edition
2. Enterprise Edition

    """,
    'description_vi_VN': """
Demo video: `Người thân của nhân viên <https://youtu.be/WyJYDgH46Nc>`_


Mô tả
=====

Bạn đang khó khăn trong việc tìm người thân của nhân viên trong phần mềm doanh nghiệp? Với module này của chúng tôi, vấn đề của bạn sẽ được giải quyết. Giải pháp mà module này cung cấp là:

#. Lưu trữ thông tin gia đình và người thân của nhân viên cho các tình huống khẩn cấp.
#. Thông tin người thân nhân viên sẽ nằm trong ứng dụng Nhân viên sau khi hoàn tất cài đặt.

Tính năng nổi bật
=================
* Dễ dàng nhập thông tin người thân trong mẫu nhân viên tiêu chuẩn. Thông tin này chỉ được duy trì và hiển thị bởi người dùng có vai trò Nhân viên Nhân sự.
* Tìm kiếm nhân viên có người thân hay không.
* Trên giao diện liên hệ, cho phép lọc để tìm ra ai là người thân của nhân viên công ty.

Ấn bản được hỗ trợ
==================
1. Ấn bản Community
2. Ấn bản Enterprise

    """,
    'author': "T.V.T Marine Automation (aka TVTMA),Viindoo",
    'website': 'https://viindoo.com/apps/app/17.0/to_hr_employee_relative',
    'live_test_url': "https://v17demo-int.viindoo.com",
    'live_test_url_vi_VN': "https://v17demo-vn.viindoo.com",
    'demo_video_url': "https://youtu.be/WyJYDgH46Nc",
    'support': 'apps.support@viindoo.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/Viindoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/hr_employee_views.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'price': 9.9,
    'currency': 'EUR',
    'license': 'OPL-1',
}
