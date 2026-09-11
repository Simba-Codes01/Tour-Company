import base64
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_mpesa import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('mpesa', "M-Pesa")], ondelete={'mpesa': 'set default'})

    mpesa_environment = fields.Selection(
        [('sandbox', "Sandbox"), ('production', "Production")],
        string="M-Pesa Environment", default='sandbox', required_if_provider='mpesa')
    mpesa_shortcode = fields.Char(
        string="Business Shortcode", required_if_provider='mpesa',
        help="The Paybill or Till number registered with Safaricom Daraja.")
    mpesa_passkey = fields.Char(string="Passkey", required_if_provider='mpesa', groups='base.group_system')
    mpesa_consumer_key = fields.Char(string="Consumer Key", required_if_provider='mpesa', groups='base.group_system')
    mpesa_consumer_secret = fields.Char(
        string="Consumer Secret", required_if_provider='mpesa', groups='base.group_system')
    mpesa_callback_base_url = fields.Char(
        string="Callback Base URL", groups='base.group_system',
        help="Publicly reachable HTTPS base URL Safaricom will POST the payment result to "
             "(e.g. an ngrok tunnel URL in development). Defaults to this database's own base URL, "
             "which only works once this server is reachable from the internet.")

    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'mpesa').update({
            'support_manual_capture': 'none',
            'support_refund': 'none',
            'support_tokenization': False,
        })

    def _get_default_payment_method_codes(self):
        self.ensure_one()
        if self.code != 'mpesa':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    @api.constrains('state')
    def _check_mpesa_credentials_are_set_before_enabling(self):
        for provider in self.filtered(lambda p: p.code == 'mpesa' and p.state != 'disabled'):
            missing = [
                f for f in ('mpesa_shortcode', 'mpesa_passkey', 'mpesa_consumer_key', 'mpesa_consumer_secret')
                if not provider[f]
            ]
            if missing:
                raise ValidationError(_(
                    "Fill in all M-Pesa Daraja credentials before enabling this provider."))

    def _mpesa_get_callback_url(self):
        self.ensure_one()
        base_url = self.mpesa_callback_base_url or self.get_base_url()
        return f'{base_url.rstrip("/")}/payment/mpesa/callback'

    def _mpesa_get_access_token(self):
        """Fetch (or reuse) an OAuth access token from Daraja for STK push requests."""
        self.ensure_one()
        response = self._send_api_request('GET', 'oauth/v1/generate?grant_type=client_credentials', is_oauth_request=True)
        access_token = response.get('access_token')
        if not access_token:
            raise ValidationError(_("M-Pesa: could not obtain an access token from Daraja."))
        return access_token

    def _mpesa_generate_password(self, timestamp):
        self.ensure_one()
        raw = f'{self.mpesa_shortcode}{self.mpesa_passkey}{timestamp}'
        return base64.b64encode(raw.encode()).decode()

    def _build_request_url(self, endpoint, *, is_oauth_request=False, **kwargs):
        if self.code != 'mpesa':
            return super()._build_request_url(endpoint, is_oauth_request=is_oauth_request, **kwargs)
        base_url = const.SANDBOX_API_URL if self.mpesa_environment == 'sandbox' else const.PRODUCTION_API_URL
        return f'{base_url}/{endpoint}'

    def _build_request_auth(self, *, is_oauth_request=False, **kwargs):
        if self.code != 'mpesa':
            return super()._build_request_auth(is_oauth_request=is_oauth_request, **kwargs)
        if is_oauth_request:
            return (self.mpesa_consumer_key, self.mpesa_consumer_secret)
        return tuple()

    def _build_request_headers(self, method, endpoint, payload, *, is_oauth_request=False, access_token=None, **kwargs):
        if self.code != 'mpesa':
            return super()._build_request_headers(
                method, endpoint, payload, is_oauth_request=is_oauth_request, **kwargs)
        if is_oauth_request:
            return None
        return {'Authorization': f'Bearer {access_token}'}

    def _mpesa_send_stk_push(self, transaction):
        """Trigger an STK Push prompt on the customer's phone for the given transaction."""
        self.ensure_one()
        access_token = self._mpesa_get_access_token()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        amount_kes = int(round(transaction.currency_id._convert(
            transaction.amount, self.env.ref('base.KES'), self.company_id, fields.Date.today())))
        phone = transaction.partner_phone or ''
        payload = {
            'BusinessShortCode': self.mpesa_shortcode,
            'Password': self._mpesa_generate_password(timestamp),
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': max(amount_kes, 1),
            'PartyA': phone,
            'PartyB': self.mpesa_shortcode,
            'PhoneNumber': phone,
            'CallBackURL': self._mpesa_get_callback_url(),
            'AccountReference': transaction.reference,
            'TransactionDesc': transaction.reference,
        }
        return self._send_api_request(
            'POST', 'mpesa/stkpush/v1/processrequest', json=payload, access_token=access_token)
