import json
import logging
import re
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core import signing
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)
WHATSAPP_INVOICE_SIGNER_SALT = 'saas.whatsapp.invoice'


def normalize_whatsapp_number(value):
    digits = re.sub(r'\D+', '', value or '')
    if not digits:
        return ''
    if len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    if len(digits) == 13 and digits.startswith('910'):
        digits = f'91{digits[3:]}'
    if len(digits) == 10:
        return f'91{digits}'
    return digits


def _money(value):
    return f'Rs {value / 100:.2f}'


def _request_json(*, url, payload=None, headers=None, method='POST'):
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    request = Request(url, data=data, headers=headers or {}, method=method)
    with urlopen(request, timeout=12) as response:
        response.read()


def _template_component(values):
    return {
        'type': 'body',
        'parameters': [{'type': 'text', 'text': str(value or '-')} for value in values],
    }


def _send_fast2sms_simple_template(*, to, values, api_key, phone_number_id, media_url='', document_filename=''):
    message_id = settings.WHATSAPP_PAYMENT_SUCCESS_MESSAGE_ID
    if not message_id:
        return None
    query = urlencode({
        'message_id': message_id,
        'phone_number_id': phone_number_id,
        'numbers': to,
        'variables_values': '|'.join(str(value or '-') for value in values),
        **({'media_url': media_url} if media_url else {}),
        **({'document_filename': document_filename} if document_filename else {}),
    })
    _request_json(
        url=f'https://www.fast2sms.com/dev/whatsapp?{query}',
        headers={'Authorization': api_key},
        method='GET',
    )
    return True


def send_template_message(*, to, template_name, values, media_url='', document_filename=''):
    if not settings.WHATSAPP_NOTIFICATIONS_ENABLED:
        logger.info('WhatsApp template skipped because notifications are disabled.')
        return False
    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    recipient = normalize_whatsapp_number(to)
    provider = settings.WHATSAPP_PROVIDER.lower()
    api_key = settings.WHATSAPP_FAST2SMS_API_KEY if provider == 'fast2sms' else settings.WHATSAPP_CLOUD_API_TOKEN
    if not phone_number_id or not api_key or not recipient:
        logger.info('WhatsApp template skipped because configuration or recipient is missing.')
        return False

    try:
        if provider == 'fast2sms':
            sent = _send_fast2sms_simple_template(
                to=recipient,
                values=values,
                api_key=api_key,
                phone_number_id=phone_number_id,
                media_url=media_url,
                document_filename=document_filename,
            )
            if sent is not None:
                return sent
    except HTTPError as exc:
        logger.warning('Fast2SMS simple template failed: %s %s', exc.code, exc.read().decode('utf-8', errors='replace'))
        return False
    except URLError as exc:
        logger.warning('Fast2SMS simple template failed: %s', exc)
        return False

    components = [_template_component(values)]
    if media_url:
        components.insert(0, {
            'type': 'header',
            'parameters': [{
                'type': 'document',
                'document': {
                    'link': media_url,
                    'filename': document_filename or 'invoice.pdf',
                },
            }],
        })
    payload = {
        'messaging_product': 'whatsapp',
        'to': recipient,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': settings.WHATSAPP_TEMPLATE_LANGUAGE},
            'components': components,
        },
    }
    if provider == 'fast2sms':
        url = f'https://www.fast2sms.com/dev/whatsapp/{settings.WHATSAPP_FAST2SMS_VERSION}/{phone_number_id}/messages'
        authorization = api_key
    else:
        url = f'https://graph.facebook.com/v20.0/{phone_number_id}/messages'
        authorization = f'Bearer {api_key}'
    try:
        _request_json(url=url, payload=payload, headers={
            'Authorization': authorization,
            'Content-Type': 'application/json',
        })
        return True
    except HTTPError as exc:
        logger.warning('WhatsApp template failed: %s %s', exc.code, exc.read().decode('utf-8', errors='replace'))
    except URLError as exc:
        logger.warning('WhatsApp template failed: %s', exc)
    return False


def notify_payment_success(*, order):
    tenant = order.tenant
    owner = tenant.owner
    workspace_url = tenant.public_url.rstrip('/')
    period_start = order.paid_at or order.created_at
    period_end = period_start + timedelta(days=30)
    profile_url = f'{workspace_url}/accounts/profile/'
    token = signing.dumps({'order_id': order.pk}, salt=WHATSAPP_INVOICE_SIGNER_SALT)
    invoice_url = workspace_url + reverse('saas_whatsapp_invoice_pdf', kwargs={'token': token})
    invoice_filename = f'vistaflo-invoice-{order.provider_payment or order.pk}.pdf'
    return send_template_message(
        to=owner.phone,
        template_name=settings.WHATSAPP_PAYMENT_SUCCESS_TEMPLATE,
        media_url=invoice_url,
        document_filename=invoice_filename,
        values=[
            owner.get_full_name() or owner.username,
            'Vistaflo',
            tenant.name,
            workspace_url,
            order.plan.name,
            '1 month',
            period_start.strftime('%d %b %Y'),
            period_end.strftime('%d %b %Y'),
            _money(order.amount),
            order.provider_payment or '-',
            profile_url,
            'Vistaflo',
        ],
    )
