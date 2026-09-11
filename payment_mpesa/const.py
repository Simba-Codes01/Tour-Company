SANDBOX_API_URL = 'https://sandbox.safaricom.co.ke'
PRODUCTION_API_URL = 'https://api.safaricom.co.ke'

# M-Pesa STK Push only settles in KES; the transaction amount (which may be in
# any currency the shop sells in, e.g. USD) is converted at request time.
MPESA_CURRENCY = 'KES'

DEFAULT_PAYMENT_METHOD_CODES = {
    'mpesa',
}

# Daraja ResultCode: 0 means success, anything else is a failure/cancellation.
# See https://developer.safaricom.co.ke/Documentation
RESULT_CODE_SUCCESS = 0
