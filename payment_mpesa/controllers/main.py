import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MpesaController(http.Controller):
    _callback_url = '/payment/mpesa/callback'

    @http.route(_callback_url, type='http', methods=['POST'], auth='public', csrf=False, save_session=False)
    def mpesa_callback(self):
        """Handle Safaricom Daraja's asynchronous STK Push result callback.

        Daraja identifies the payment by `CheckoutRequestID`, not by the reference we generated,
        so the transaction is looked up via the `mpesa_checkout_request_id` field stored when the
        STK Push was sent (see `payment.transaction._send_payment_request`).
        """
        data = request.get_json_data()
        _logger.info("M-Pesa callback received:\n%s", pprint.pformat(data))

        callback = (data or {}).get('Body', {}).get('stkCallback', {})
        checkout_request_id = callback.get('CheckoutRequestID')
        tx_sudo = request.env['payment.transaction'].sudo().search(
            [('mpesa_checkout_request_id', '=', checkout_request_id), ('provider_code', '=', 'mpesa')], limit=1)

        if not tx_sudo:
            _logger.warning("M-Pesa callback for unknown CheckoutRequestID %s", checkout_request_id)
            return request.make_json_response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        metadata = tx_sudo._mpesa_parse_callback_metadata(callback.get('CallbackMetadata'))
        payment_data = {
            'reference': tx_sudo.reference,
            'result_code': callback.get('ResultCode'),
            'result_desc': callback.get('ResultDesc'),
            'receipt': metadata.get('MpesaReceiptNumber'),
            'amount': metadata.get('Amount'),
        }
        tx_sudo._process('mpesa', payment_data)

        # Acknowledge receipt so Safaricom stops retrying the callback.
        return request.make_json_response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
