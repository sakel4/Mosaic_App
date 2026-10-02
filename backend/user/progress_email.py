import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage
from rest_framework import permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class ProgressEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    pdf = serializers.FileField()

    def validate_pdf(self, pdf):
        if pdf.size > settings.MAX_PROGRESS_PDF_BYTES:
            raise serializers.ValidationError("The PDF must be no larger than 10 MB.")
        if not pdf.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Upload a .pdf file.")
        header = pdf.read(5)
        pdf.seek(0)
        if header != b"%PDF-":
            raise serializers.ValidationError("The uploaded file is not a PDF.")
        return pdf


class ProgressEmailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    throttle_scope = "progress_email"

    def post(self, request):
        serializer = ProgressEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient = serializer.validated_data["email"]
        pdf = serializer.validated_data["pdf"]
        # Derive the subject from the authenticated account, never from the upload.
        name = " ".join(f"{request.user.first_name} {request.user.last_name}".split())
        name = name or request.user.email
        message = EmailMessage(
            subject=f"{name} progression",
            body=f"Please find {name}'s progression report attached.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        message.attach("progression.pdf", pdf.read(), "application/pdf")
        try:
            sent = message.send()
        except (SMTPException, OSError, ImproperlyConfigured):
            logger.exception("Progress report email could not be sent")
            return Response({"detail": "The email could not be sent. Please try again later."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if sent != 1:
            return Response({"detail": "The email could not be sent. Please try again later."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"detail": "Progress report submitted to the email backend.", "email": recipient})
