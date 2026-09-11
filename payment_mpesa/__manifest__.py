{
    'name': 'Payment Provider: M-Pesa (Daraja STK Push)',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Kenya M-Pesa mobile money payments via the Safaricom Daraja API',
    'description': """
M-Pesa Payment Provider
========================
Adds M-Pesa (Safaricom Daraja STK Push) as an online payment method.

Going live requires:
- A Safaricom-approved production shortcode (Paybill/Till) and passkey.
- A publicly reachable HTTPS domain for the payment callback - Daraja cannot
  reach a plain localhost server, so local testing needs a tunnel (e.g. ngrok)
  whose URL is registered as this provider's Callback Base URL and whitelisted
  in the Safaricom developer portal.

Until then, install this module freely - the provider is seeded disabled so
it has no effect on checkout until configured and enabled.
""",
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
