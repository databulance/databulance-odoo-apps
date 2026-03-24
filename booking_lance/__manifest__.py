{
    'name': 'BookingLance',
    'version': '19.0.1.0.0',
    'summary': 'Plug-and-play booking system for consulting, education, and professional services',
    'description': """
BookingLance — Professional Booking Suite for Odoo 19
=====================================================
A fully-featured, white-label booking module designed for
consulting firms, tutoring centers, clinics, and any service
business that needs a clean client-facing booking portal.

Features
--------
* Per-staff weekly schedules with automated slot generation
* 30-day ahead slot generation via cron (configurable)
* Manual slot add / block override
* Buffer time between sessions
* Waitlist with auto-notification
* Recurring bookings
* Cancellation and rescheduling policies
* Email confirmations, reminders, cancellation notices
* iCal attachment on every confirmation
* Webhook events: created, confirmed, cancelled, rescheduled
* White-label: brand name, color, logo per website
* Multi-website support
* i18n ready (translatable)
* REST API: 6 endpoints for external integrations
* Odoo Calendar integration
* Client portal: /booking, /my/bookings
    """,
    'author': 'Databulance',
    'website': 'https://databulance.com',
    'license': 'LGPL-3',
    'category': 'Services/Booking',
    'depends': [
        'base',
        'mail',
        'portal',
        'calendar',
        'website',
        'hr',
    ],
    'data': [
        'security/booking_lance_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/mail_template_data.xml',
        'views/config_views.xml',
        'views/service_views.xml',
        'views/staff_views.xml',
        'views/slot_views.xml',
        'views/booking_views.xml',
        'views/waitlist_views.xml',
        'views/webhook_views.xml',
        'views/portal_templates.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'booking_lance/static/src/css/portal.css',
            'booking_lance/static/src/js/booking_wizard.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
