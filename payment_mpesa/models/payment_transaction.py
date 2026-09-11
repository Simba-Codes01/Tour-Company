import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_mpesa import const

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    mpesa_checkout_request_id = fields.Char(string="M-Pesa CheckoutRequestID", copy=False)

    def _send_payment_request(self):
        """Override of `payment` to trigger an M-Pesa STK Push for the transaction."""
        if self.provider_code != 'mpesa':
            return super()._send_payment_request()

        if not self.partner_phone:
            self._set_error(_("A phone number is required to pay with M-Pesa."))
            return

        try:
            response = self.provider_id._mpesa_send_stk_push(self)
        except ValidationError as e:
            self._set_error(str(e))
            return

        checkout_request_id = response.get('CheckoutRequestID')
        if not checkout_request_id:
            self._set_error(_(
                "M-Pesa did not return a CheckoutRequestID: %s", response.get('errorMessage', response)))
            return

        self.mpesa_checkout_request_id = checkout_request_id
        self._set_pending(state_message=_(
            "An M-Pesa STK Push prompt was sent to %s. Enter your M-Pesa PIN on your phone to "
            "complete the payment.", self.partner_phone))

    def _extract_amount_data(self, payment_data):
        if self.provider_code != 'mpesa':
            return super()._extract_amount_data(payment_data)
        amount = payment_data.get('amount')
        if amount is None:
            return None
        return {'amount': amount, 'currency_code': const.MPESA_CURRENCY}

    def _apply_updates(self, payment_data):
        if self.provider_code != 'mpesa':
            return super()._apply_updates(payment_data)

        result_code = payment_data.get('result_code')
        if result_code == const.RESULT_CODE_SUCCESS:
            receipt = payment_data.get('receipt')
            if receipt:
                self.provider_reference = receipt
            self._set_done()
        else:
            _logger.warning(
                "M-Pesa transaction %s failed/cancelled with ResultCode %s: %s",
                self.reference, result_code, payment_data.get('result_desc'))
            self._set_canceled() if result_code == 1032 else self._set_error(
                payment_data.get('result_desc') or _("The M-Pesa payment could not be completed."))

    @staticmethod
    def _mpesa_parse_callback_metadata(callback_metadata):
        """Flatten Daraja's `CallbackMetadata.Item` list-of-dicts into a plain dict."""
        items = (callback_metadata or {}).get('Item', [])
        return {item['Name']: item.get('Value') for item in items if 'Name' in item}
