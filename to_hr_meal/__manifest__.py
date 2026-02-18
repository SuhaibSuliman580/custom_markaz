{
    'name': "Meal Orders",
    'name_vi_VN': "Suất ăn",

    'summary': """Manage Meal Orders for your employees""",
    'summary_vi_VN': """Quản lý đơn đặt hàng bữa ăn cho nhân viên của bạn""",

    'description': """
Demo video: `Meal Orders <https://youtu.be/LOjwriZpmtk>`_


What it does
============
This module helps you manage mass meal orders for your employees. It also lets you know in detail the cost of the meals for your employees over time.

Key Features
============

* Create HR meal types according to criteria such as time (lunch, dinner,...) or price to classify and attach a warning to alert the person in charge of when to order a meal.
* Meal orderers can create meal orders for employees, departments, and guests of the company when needed.
* Meal managers can approve or decline meal orders to finalize the number of meals that will notify the supplier or the person in charge of the kitchen.
* Statistics and analysis of meals by many criteria such as employees, departments, meal types, booking time, and kitchen,... to serve different management purposes of meal managers and business administrators.

Editions Supported
==================
1. Community Edition
2. Enterprise Edition

    """,
    'description_vi_VN': """
Demo video: `Suất ăn <https://youtu.be/LOjwriZpmtk>`_

Mô tả
=====
Mô-đun này giúp bạn tạo và quản lý lệnh đặt suất ăn của nhân viên trên số lượng lớn. Mô-đun này cũng cho phép bạn nắm được chi tiết chi phí bữa ăn cho nhân viên theo thời gian.

Tính năng nổi bật
=================

* Tạo kiểu suất ăn theo các tiêu chí như thời gian (bữa trưa, bữa tối,...) hay mức giá để phân loại, kèm theo cảnh báo nhằm lưu ý cho người đặt về thời gian đặt bữa.
* Người đặt suất ăn có thể tạo đơn đặt suất ăn cho nhân viên, phòng ban, khách của công ty khi có nhu cầu.
* Người quản lý bữa ăn phê duyệt hoặc từ chối các đơn đặt suất ăn để chốt số lượng suất ăn sẽ chuyển đến nhà cung cấp hoặc nhà bếp.
* Thống kê và phân tích bữa ăn theo nhiều tiêu chí như nhân viên, phòng ban, kiểu suất ăn, thời gian đặt, nhà bếp,... phục vụ các mục đích quản lý khác nhau phù hợp với vai trò người quản lý suất ăn và nhà quản trị doanh nghiệp.

Ấn bản được hỗ trợ
==================
1. Ấn bản Community
2. Ấn bản Enterprise

    """,

    'author': "T.V.T Marine Automation (aka TVTMA),Viindoo",
    'website': "https://viindoo.com/intro/hr-meal",
    'live_test_url': "https://v17demo-int.viindoo.com",
    'live_test_url_vi_VN': "https://v17demo-vn.viindoo.com",
    'demo_video_url': "https://youtu.be/LOjwriZpmtk",
    'support': 'apps.support@viindoo.com',
    'category': 'Human Resources/Meal',
    'version': '1.0.1',

    # any module necessary for this one to work correctly
    'depends': ['hr_holidays', 'to_base', 'viin_hr'],

    # always loaded
    'data': [
        'data/ir_sequence_data.xml',
        'data/hr_kitchen_data.xml',
        'data/hr_meal_type_data.xml',
        'security/meal_security.xml',
        'security/ir.model.access.csv',
        'views/root_menu.xml',
        'views/hr_kitchen_views.xml',
        'views/hr_meal_type_views.xml',
        'views/hr_meal_order_views.xml',
        'views/hr_meal_order_line_views.xml',
        'views/hr_meal_orders_analysis.xml',
        'views/hr_employee_views.xml',
        'views/res_config_setting_view.xml'
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'application': True,
    'sequence': 119,
    'price': 45.9,
    'subscription_price': 3.31,
    'currency': 'EUR',
    'license': 'OPL-1',
}
