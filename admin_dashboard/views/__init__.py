"""
views/__init__.py

Re-exports every view function so that urls.py can keep importing
from `admin_dashboard.views` without any changes.

Usage in urls.py stays exactly the same:
    from . import views
    path("", views.admin_dashboard, name="admin_dashboard")
"""

from .utils import logout_view                                  # noqa: F401
from .dashboard import admin_dashboard                          # noqa: F401

from .formations import (                                       # noqa: F401
    formations,
    export_formations_excel,
)

from .students import (                                         # noqa: F401
    students,
    student_detail,
    student_qr_code,
    export_students_excel,
)

from .employees import (                                        # noqa: F401
    employees,
    employee_detail,
    export_employees_excel,
)

from .finance import (                                          # noqa: F401
    finance,
    export_finance_excel,
)

from .timetable import (                                        # noqa: F401
    timetable,
    export_timetable_excel,
)

from .attendance import (                                       # noqa: F401
    attendance_sessions,
    open_attendance,
    attendance_checkin,
    close_attendance,
    export_attendance_excel,
)

from .misc import (                                             
    rooms,
    export_rooms_excel,
    notifications,
    mark_all_notifications_read,
    mark_notification_read,
    export_notifications_excel,
    registration_requests,
    export_registration_requests_excel,
    contact_messages,
    export_contact_messages_excel,
    settings,
    statistics_report,
)
from .users import users
from .assistant import assistant