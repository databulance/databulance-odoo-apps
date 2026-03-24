# -*- coding: utf-8 -*-
{
    'name': 'YooKassa Widget Pro',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': '54-FZ receipts and post-payment onboarding',
    'author': 'Databulance',
    'website': 'https://databulance.com',
    'support': 'support@databulance.com',
    'license': 'OPL-1',
    'price': 249.00,
    'currency': 'EUR',
    'depends': ['payment_yookassa_widget', 'mail', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/payment_provider_pro_views.xml',
        'views/payment_transaction_pro_views.xml',
        'views/payment_yookassa_pro_templates.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
