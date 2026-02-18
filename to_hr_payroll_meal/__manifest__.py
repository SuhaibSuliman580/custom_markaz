{
    'name': 'HR Meal Order & Payroll Integration',
    'name_vi_VN': "Tích hợp Đặt suất ăn và Bảng lương",
    'category': 'Human Resources/Payroll',
    'version': '0.1.1',
    'author': "T.V.T Marine Automation (aka TVTMA),Viindoo",
    'maintainer': 'T.V.T Marine Automation (aka TVTMA)',
    'website': "https://viindoo.com/apps/app/17.0/to_hr_payroll_meal",
    'live_test_url': "https://v17demo-int.viindoo.com",
    'live_test_url_vi_VN': "https://v17demo-vn.viindoo.com",
    'demo_video_url': "https://youtu.be/mIWGVVf81kQ",
    'support': "apps.support@viindoo.com",
    'summary': """
Deduct Meal Order price in Employee Payslip""",
    'summary_vi_VN': """
Khấu trừ tiền đặt suất ăn vào phiếu lương nhân viên """,

    'description': """
Demo video: `HR Meal Order & Payroll Integration <https://youtu.be/mIWGVVf81kQ>`_

What it does
============

This module is a bridge module to integrate the HR Meal app (to_hr_meal) https://viindoo.com/apps/app/17.0/to_hr_meal and the Payroll app (to_hr_payroll) https://viindoo.com/apps/app/17.0/to_hr_payroll to deduct the meal price from the employee's payslip.

Key Features
============

#. Allow entering the price the employee must pay for the meal and calculate the difference between the price paid by the company and the price paid by the employee on the meal order slip.
#. Add the salary rule *Deduct the meal order* to compute the meal order amount to be deducted from the employee.
#. Automatically recognize meal orders and compute employee meal orders price on payslips.

Business Value
==============

* **Streamlined Deduction Process**: Simplifies the management of meal expenses by automating the deduction process directly in employee payslips.
* **Accuracy and Transparency**: Ensures precise calculation of meal order deductions, providing clear documentation for both employees and HR teams.
* **Efficiency**: Reduces administrative workload by automating the integration of meal orders and payroll, saving time and minimizing errors.
* **Policy Compliance**: Ensures alignment with company policies regarding meal subsidies and employee contributions.
* **Cost Analysis**: Offers a clear view of meal expenses at an individual and organizational level, supporting better financial management and decision-making.

Who Should Use This Module
==========================

This module is ideal for:

* Companies offering subsidized meal plans for employees and needing an efficient way to manage deductions.
* HR and payroll teams aiming to automate and streamline meal order deductions in payroll processes.
* Organizations looking for precise and transparent integration between meal management and payroll.
* Businesses wanting to enhance the employee experience by providing clear documentation of meal-related deductions.
* Enterprises requiring detailed tracking of meal expenses for compliance and cost control.

Editions Supported
==================
1. Community Edition

    """,

    'description_vi_VN': """
Demo video: `Tích hợp Đặt suất ăn và Bảng lương <https://youtu.be/mIWGVVf81kQ>`_

Ứng dụng này làm gì
===================

Mô-đun này là mô-đun cầu nối nhằm tích hợp phần mềm Quản lý suất ăn (to_hr_meal) https://viindoo.com/vi/apps/app/16.0/to_hr_meal và Phần mềm tính lương (to_hr_payroll) https://viindoo.com/vi/apps/app/16.0/to_hr_payroll để khấu trừ giá đặt suất ăn vào phiếu lương của nhân viên.

Tính năng chính
===================

#. Cho phép nhập giá nhân viên phải trả cho bữa ăn và tính toán sự chênh lệnh giữa giá phải trả của công ty và giá phải trả của nhân viên trên phiếu đặt suất ăn.
#. Bổ sung thêm quy tắc lương *Khấu trừ tiền đặt suất ăn* để tính toán số tiền đặt suất ăn cần khấu trừ của nhân viên.
#. Tự động nhận diện các phiếu đặt suất ăn và tính toán số tiền đặt suất ăn của nhân viên trên phiếu lương.

Giá trị Kinh doanh
==================

* **Tối ưu hóa quy trình khấu trừ**: Đơn giản hóa việc quản lý chi phí suất ăn bằng cách tự động khấu trừ trực tiếp vào phiếu lương của nhân viên.
* **Chính xác và Minh bạch**: Đảm bảo tính toán chính xác số tiền khấu trừ suất ăn, cung cấp tài liệu rõ ràng cho cả nhân viên và phòng Nhân sự.
* **Hiệu quả**: Giảm khối lượng công việc hành chính bằng cách tự động tích hợp dữ liệu đặt suất ăn vào quy trình bảng lương, tiết kiệm thời gian và giảm thiểu lỗi.
* **Tuân thủ chính sách**: Đảm bảo phù hợp với chính sách của công ty liên quan đến trợ cấp suất ăn và đóng góp của nhân viên.
* **Phân tích chi phí**: Cung cấp cái nhìn rõ ràng về chi phí suất ăn ở cấp độ cá nhân và tổ chức, hỗ trợ quản lý tài chính và ra quyết định tốt hơn.

Ai Nên Sử Dụng Mô-đun Này?
==========================

Mô-đun này phù hợp với:

* Các công ty cung cấp kế hoạch trợ cấp suất ăn cho nhân viên và cần một cách hiệu quả để quản lý việc khấu trừ.
* Các phòng Nhân sự và bảng lương muốn tự động hóa và tối ưu hóa quy trình khấu trừ tiền đặt suất ăn.
* Các tổ chức cần tích hợp chính xác và minh bạch giữa quản lý suất ăn và bảng lương.
* Doanh nghiệp muốn cải thiện trải nghiệm của nhân viên bằng cách cung cấp tài liệu rõ ràng về các khoản khấu trừ liên quan đến suất ăn.
* Các công ty cần theo dõi chi tiết chi phí suất ăn để đảm bảo tuân thủ và kiểm soát chi phí.

Phiên bản được hỗ trợ
=====================
1. Ấn bản cộng đồng

    """,

    'depends': ['to_hr_payroll', 'to_hr_meal'],
    'data': [
        'data/hr_contribution_category_data.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
    'price': 18.9,
    'currency': 'EUR',
    'license': 'OPL-1',
}
