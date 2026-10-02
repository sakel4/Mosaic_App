from smtplib import SMTPException
from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from .progress_email import ProgressEmailView


@override_settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}, DEFAULT_FROM_EMAIL="reports@example.test")
class ProgressEmailTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.user = SimpleNamespace(pk=1, is_authenticated=True, first_name="Maya", last_name="Rivers", email="maya@example.test")

    def send(self, content=b"%PDF-1.4\n%%EOF", email="parent@example.test", filename="report.pdf", authenticated=True):
        request = APIRequestFactory().post("/api/users/progress/email/", {
            "email": email, "pdf": SimpleUploadedFile(filename, content, content_type="application/pdf"),
        }, format="multipart")
        if authenticated:
            force_authenticate(request, user=self.user)
        return ProgressEmailView.as_view()(request)

    def test_sends_pdf_to_recipient_with_account_name_in_subject(self):
        self.assertEqual(self.send().status_code, 200)
        message = mail.outbox[-1]
        self.assertEqual(message.subject, "Maya Rivers progression")
        self.assertEqual(message.to, ["parent@example.test"])
        attachment = message.attachments[0]
        self.assertEqual(attachment.filename, "progression.pdf")
        self.assertEqual(attachment.content, b"%PDF-1.4\n%%EOF")
        self.assertEqual(attachment.mimetype, "application/pdf")

    def test_requires_authentication(self):
        self.assertEqual(self.send(authenticated=False).status_code, 401)

    def test_rejects_invalid_email_and_non_pdf(self):
        self.assertEqual(self.send(email="bad-email").status_code, 400)
        self.assertEqual(self.send(content=b"not a pdf").status_code, 400)
        self.assertEqual(self.send(filename="report.txt").status_code, 400)

    @override_settings(MAX_PROGRESS_PDF_BYTES=10)
    def test_rejects_oversized_upload(self):
        self.assertEqual(self.send().status_code, 400)

    def test_reports_email_delivery_failure(self):
        with patch("user.progress_email.EmailMessage.send", side_effect=SMTPException("offline")):
            self.assertEqual(self.send().status_code, 503)

    def test_limits_email_requests(self):
        for _ in range(5):
            self.assertEqual(self.send().status_code, 200)
        self.assertEqual(self.send().status_code, 429)
