{
    'name': 'Payroll',
    'name_vi_VN': 'Bảng lương',
    'category': 'Human Resources/Payroll',
    'version': '1.5.0',
    'author': 'T.V.T Marine Automation (aka TVTMA),Viindoo',
    'website': "https://viindoo.com/intro/payroll",
    'live_test_url': "https://v17demo-int.viindoo.com",
    'live_test_url_vi_VN': "https://v17demo-vn.viindoo.com",
    'demo_video_url': "https://youtu.be/ZA8yvssRO4Q",
    'support': 'apps.support@viindoo.com',
    'summary': 'Manage employee payroll',
    'summary_vi_VN': 'Quản lý hồ sơ lương nhân viên của bạn',
    'description': """
Demo video: `Payroll <https://youtu.be/ZA8yvssRO4Q>`_


Problems
========

* Payroll work in enterprises often takes a lot of time due to:

  * A large number of employees.
  * Apply many different salary modes, different calculation formulas for different positions.
  * To synthesize data for monthly salary calculation, enterprises need to spend a lot of personnel to monitor and analyse data from departments and workshops, etc.
  * Enterprises work in flexible shifts: the working form of each employee is different in the number of breaks, the number of overtime shifts, commissions, discounts, etc. making salary calculation complicated, confusing for the payroll department.

* The enduring time to analyze and calculate salary leads to the consequence of updating the general data of the enterprise, affecting the financial, production and business planning.
* It's difficult to analyze the detail of costs related to salary by department, by project or by some other purpose.
* The accuracy of the data depends a lot on the carefulness and presentation skills of the payroll personnel.
* To build salary cost analysis reports for each department, each purpose over a long period of time is quite time-consuming, and it is not easy to get updated data right when the need arises.

Solution
========

This module is developed to resolve the above points. So, it can be integrated with the data of several modules such as Attendances, Time Off, Contract, HR Payroll Accounting, etc. to calculate salary scientifically and transparently.

Key Features
============

This module allows:

#. Manage salary cycle, salary structures, salary rules, employee advantages; Provide the set of basic salary rules and employee advantage templates for salary computation.
#. Manage Personal Tax Rules.
#. Manage the salary information on the employee contract:

   * Allow to set up Salary Computation Mode, Personal Tax Policy, Tax Rule on contract types to apply with employee contracts.
   * Allow to set up Payroll contribution registers (Social insurance, Health insurance, Unemployment insurance, Labor union) on employee contracts.
   * Alloy to set up Wages & Allowances on employee contracts.

#. Create Payslip and Payslips Batches

   * With just a few clicks, users can create individual payslips for each employee, Payslips Batches for all employees in the company. The information about the contract, salary structure, working time, vacation time, insurance contributions, income tax, etc. are automatically updated on the payslip to serve as a basis for salary calculation.
   * Attach a Payslip to an existing Payslips Batches.
   * Employee's payslips will be calculated based on the Work Entries with types: Calendar, Timeoff, Overtime, Attedance, ...

#. Integrate with other modules to get data into Payslip and Payslips Batches:

   * Attendances module `(to_hr_payroll_attendance) <https://viindoo.com/apps/app/17.0/to_hr_payroll_attendance>`_: get employees' attendance data automatically.
   * Overtime module `(viin_hr_overtime_payroll) <https://viindoo.com/apps/app/17.0/viin_hr_overtime_payroll>`_: get employees' overtime data.
   * Work From Home Timesheet module (viin_hr_payroll_timesheet_wfh): Control working without being present at the company such as working from home, going on a business trip, ...
   * Expense module (to_hr_expense_payroll): Get expense data for reimbursement into payslips.
   * HR Meal module `(to_hr_payroll_meal) <https://viindoo.com/apps/app/17.0/to_hr_payroll_meal>`_: get employees' meal data.
   * Etc.

#. Integrate with the `Payroll Accounting module <https://viindoo.com/apps/app/17.0/to_hr_payroll_account>`_ to create payroll accounting journal entries.

#. Provide reports with visualized, multi-dimensional information:

   * Salary Analysis Report: Allow to view the report with the criteria included in the salary table and it is designed with the Pivot interface. This allows users to filter, group, or design their own report tables.
   * Payroll Contribution History: Users can look up and manage employee contributions.
   * Payslip Personal Income Tax Analysis: Multi-dimensional analysis with calculated values ​​such as Tax amount, Tax computation base, Taxable income, etc.

#. In case an employee has more than one contract and these contracts are in a different status *New* or *Cancelled* in the same salary cycle, the system will automatically calculate based on the matching contracts when creating payslips batches or payslips.

Known Issues
============
#. There is a restriction on negative days with the salary cycle. You can replace it by setting the positive day and the negative month.
#. Warning: To avoid conflicts in the process of using Payroll application, you must uninstall Odoo's Payroll if you are using it.

Editions Supported
==================
1. Community Edition

    """,
    'description_vi_VN': """
Demo video: `Bảng lương <https://youtu.be/ZA8yvssRO4Q>`_

Vấn đề
======

* Công tác tiền lương trong doanh nghiệp thường tốn rất nhiều thời gian do:

  * Số lượng nhân viên lớn.
  * Áp dụng nhiều chế độ tiền lương khác nhau, công thức tính toán khác nhau cho các đối tượng khác nhau.
  * Để tổng hợp số liệu phục vụ cho công tác tính toán tiền lương hàng tháng, doanh nghiệp cần tốn khá nhiều nhân sự để theo dõi, tổng hợp số liệu từ các phòng ban, phân xưởng, v.v.
  * Doanh nghiệp làm việc ca kíp linh động, hình thức làm việc của mỗi nhân viên khác nhau: số buổi nghỉ, số ca làm thêm giờ, hoa hồng, chiết khấu, v.v. làm cho việc tính tiền lương trở nên phức tạp, dễ gây nhầm lẫn cho bộ phận quản lý lương.

* Thời gian tổng hợp và tính toán lương kéo dài dẫn đến hệ lụy về việc cập nhật số liệu chung của doanh nghiệp, ảnh hưởng đến việc hoạch định kế hoạch tài chính, sản xuất, kinh doanh.
* Việc phân tích chi phí liên quan đến tiền lương khó để chi tiết theo từng bộ phận, từng dự án hoặc theo một số mục đích khác.
* Độ chính xác của dữ liệu phụ thuộc khá nhiều vào sự cẩn trọng và kỹ năng trình bày của nhân sự làm lương.
* Để xây dựng các báo cáo phân tích chi phí lương cho từng bộ phận, từng mục đích với một khoảng thời gian dài khá tốn thời gian và để có được số liệu cập nhật ngay khi có nhu cầu không hề dễ dàng.

Giải pháp
=========

Mô đun này được phát triển để giải quyết các bài toán bên trên của doanh nghiệp, có thể tích hợp và sử dụng dữ liệu của một số mô-đun như Quản lý Vào/Ra, Quản lý Ngày nghỉ, Quản lý hợp đồng, Kế toán lương, v.v. để tính lương một cách khoa học và minh bạch.

Tính năng cơ bản
================

Mô đun này cho phép:

#. Quản lý các chu kỳ tính lương, cấu trúc lương, quy tắc lương, chế độ đãi ngộ/phúc lợi cho nhân viên; Cung cấp sẵn một bộ các quy tắc lương cơ bản, chế độ đãi ngộ cơ bản phục vụ cho việc tính lương.
#. Quản lý các quy tắc tính thuế TNCN theo luật định.
#. Quản lý các thông tin để tính lương trên hợp đồng nhân viên:

   * Cho phép thiết lập các chế độ tính lương, chế độ tính thuế TNCN, quy tắc thuế TNCN trên từng kiểu hợp đồng và áp dụng với hợp đồng của từng nhân viên.
   * Cho phép ghi nhận các khoản đăng ký đóng góp từ lương (Bảo hiểm xã hội, Bảo hiểm y tế, Bảo hiểm thất nghiệp, Phí công đoàn,...) trên hợp đồng nhân viên.
   * Cho phép ghi nhận các khoản phụ cấp/phúc lợi cho từng nhân viên.

#. Cho phép tạo Phiếu lương và Bảng lương.

   * Chỉ với một vài nhấp chuột, người dùng có thể tạo Phiếu lương riêng lẻ cho từng nhân viên, Bảng lương cho toàn bộ nhân viên trong công ty. Các thông tin về hợp đồng, cấu trúc lương, thời gian làm việc, thời gian nghỉ, các khoản đóng góp về bảo hiểm, thuế thu nhập, v.v. đều được tự động cập nhật vào phiếu lương để làm căn cứ tính lương.
   * Gắn một Phiếu lương đến một Bảng lương có sẵn.
   * Phiếu lương của nhân viên sẽ được tính toán dựa trên Nhật ký công việc với các kiểu sau: Lịch làm việc, Nghỉ, Tăng ca, Chấm vào/ra, ...

#. Tích hợp với các mô-đun khác để lấy dữ liệu tự động vào bảng lương & phiếu lương:

   * Mô-đun Quản lý Vào/Ra `(to_hr_payroll_attendance) <https://viindoo.com/vi/apps/app/17.0/to_hr_payroll_attendance>`_: Lấy dữ liệu về chấm công điểm danh vào/ra.
   * Mô-đun Tăng ca `(viin_hr_overtime_payroll) <https://viindoo.com/vi/apps/app/17.0/viin_hr_overtime_payroll>`_: Lấy dữ liệu về tăng ca.
   * Mô-đun Chấm công làm việc (viin_hr_payroll_timesheet_wfh): Kiểm soát làm việc mà không cần có mặt tại công ty như làm việc tại nhà, đi công tác,...
   * Module Chi tiêu (to_hr_expense_payroll): Lấy dữ liệu về chi tiêu để bồi hoàn vào phiếu lương.
   * Mô-đun Suất ăn `(to_hr_payroll_meal) <https://viindoo.com/vi/apps/app/17.0/to_hr_payroll_meal>`_: Lấy dữ liệu về đặt suất ăn ca.
   * v.v.

#. Tích hợp với mô-đun Kế toán lương `(to_hr_payroll_account) <https://viindoo.com/vi/apps/app/17.0/to_hr_payroll_account>`_ để tạo các bút toán kế toán lương.

#. Cung cấp các báo cáo với thông tin trực quan, đa chiều:

   * Báo cáo Phân tích Lương: Cho phép xem các chỉ tiêu có trong bảng lương và được thiết kế với giao diện Pivot, giúp người dùng có thể lọc, nhóm, hay tự mình thiết lập bảng Báo cáo với chỉ tiêu mà người dùng muốn theo dõi.
   * Báo cáo Lịch sử đóng góp từ lương: Người dùng có thể tra cứu, quản lý những khoản đóng góp từ lương của nhân viên.
   * Phân tích Thuế thu nhập cá nhân: Phân tích đa chiều với các giá trị tính toán như Giá trị thuế, Cơ sở tính thuế, Thu nhập bị tính thuế,...

#. Trong chu kỳ tính lương, trường hợp nhân viên có nhiều hơn một hợp đồng và các hợp đồng này ở trạng thái khác Mới và Hủy:

   * Khi tạo Bảng lương, hệ thống sẽ tự động tính toán dựa trên các hợp đồng phù hợp.

Các hạn chế đã biết
===================
#. Với chu kỳ lương, có một hạn chế về ngày âm. Bạn có thể thay thế nó bằng cách thiết lập ngày dương và tháng âm.

#. Cảnh báo: Để tránh xung đột trong quá trình sử dụng ứng dụng Bảng lương, bạn phải gỡ cài đặt Bảng lương của Odoo nếu đang sử dụng.

Ấn bản được hỗ trợ
==================
1. Ấn bản Community

    """,
    'depends': [
        'to_base',
        'viin_hr',
        'viin_hr_contract',
        'to_hr_employee_relative',
        'viin_hr_work_entry_contract',
        'viin_hr_work_entry_holidays',
    ],
    'assets': {
        'web.assets_backend': ["/to_hr_payroll/static/src/scss/*"]
    },
    'data': [
        'views/hr_payroll_report.xml',
        'data/mail_template_data.xml',
        'data/hr_contribution_category_data.xml',
        'data/hr_payroll_data.xml',
        'data/scheduler_data.xml',
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'views/root_menu.xml',
        'views/hr_contract_type_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_salary_cycle_views.xml',
        'views/hr_advantage_template_views.xml',
        'views/hr_department_views.xml',
        'views/hr_job_view.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_payroll_structure_type_views.xml',
        'views/hr_payroll_structure_views.xml',
        'views/hr_contribution_category.xml',
        'views/hr_salary_rule_category_views.xml',
        'views/hr_department_register_partner_views.xml',
        'views/hr_contribution_register_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_line_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_holidays_summary_employee_views.xml',
        'wizard/abstract_hr_payroll_contrib_action_view.xml',
        'wizard/hr_payroll_contrib_action_change_base_view.xml',
        'wizard/hr_payroll_contrib_action_change_rates_view.xml',
        'wizard/hr_payroll_contrib_action_done_view.xml',
        'wizard/hr_payroll_contrib_action_resume_view.xml',
        'wizard/hr_payroll_contrib_action_edit_date_start_views.xml',
        'wizard/hr_payroll_contrib_action_edit_date_end_views.xml',
        'wizard/hr_payroll_contrib_action_suspend_view.xml',
        'wizard/update_contract_advantage_views.xml',
        'views/hr_payroll_contribution_register.xml',
        'views/hr_payroll_contribution_type.xml',
        'views/hr_payroll_contribution_history.xml',
        'views/hr_payroll_analysis.xml',
        'views/personal_tax_rule_views.xml',
        'wizard/hr_payroll_contribution_register_report_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_contributionregister_templates.xml',
        'views/report_payslip_templates.xml',
        'views/report_payslipdetails_templates.xml',
        'views/report_payslipbatch_templates.xml',
        'views/hr_payroll_contribution_analysis.xml',
        'views/resource_calendar_leave_views.xml',
        'report/hr_contract_history_views.xml',
        'report/payslip_personal_income_tax_analysis.xml',
    ],
    'demo': [
        'data/user_demo.xml',
        'data/personal_tax_rule_demo.xml',
        'data/hr_contract_demo.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'price': 45,
    'subscription_price': 12.6,
    'currency': 'EUR',
    'license': 'OPL-1',
}
