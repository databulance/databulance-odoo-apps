# -*- coding: utf-8 -*-
{
    'name': 'YooKassa Payment Widget',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'YooKassa embedded checkout widget for Odoo 19',
    'author': 'Databulance',
    'website': 'https://databulance.com',
    'support': 'support@databulance.com',
    'license': 'LGPL-3',
    'depends': ['payment', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_provider_data.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/payment_yookassa_templates.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
