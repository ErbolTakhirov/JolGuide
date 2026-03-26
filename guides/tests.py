from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User, GuideProfile
from guides.models import GuideVerificationRequest, GuideReport


class GuideVerificationTests(TestCase):
    def setUp(self):
        # Create guide user
        self.guide_user = User.objects.create_user(
            email='guide@test.com', username='guide1', password='pw', role='guide'
        )
        self.guide_profile = GuideProfile.objects.create(
            user=self.guide_user, name='Test Guide', city='Bishkek', is_verified=False
        )
        
        # Create tourist user
        self.tourist_user = User.objects.create_user(
            email='tourist@test.com', username='tourist1', password='pw', role='tourist'
        )

        # Valid image data for testing
        self.img_data = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'

    def test_guide_can_submit_verification(self):
        """Guide can submit verification request via POST."""
        self.client.force_login(self.guide_user)
        url = reverse('guides:verification_submit')
        
        id_image = SimpleUploadedFile("id.gif", self.img_data, content_type="image/gif")
        selfie_image = SimpleUploadedFile("selfie.gif", self.img_data, content_type="image/gif")

        data = {
            'legal_name': 'Ivan Ivanov',
            'display_name': 'Ivan',
            'phone': '+996555112233',
            'city': 'Bishkek',
            'languages': 'ru, en',
            'bio': 'Test bio',
            'service_types': 'Test services',
            'risk_level': 'low',
            'id_document_image': id_image,
            'selfie_image': selfie_image,
            'agreed_to_safety_rules': True,
        }

        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('guides:verification_status'))

        # Check DB
        vr = GuideVerificationRequest.objects.get(guide=self.guide_profile)
        self.assertEqual(vr.status, GuideVerificationRequest.Status.SUBMITTED)
        self.assertEqual(vr.legal_name, 'Ivan Ivanov')

    def test_admin_approval_syncs_is_verified(self):
        """When admin approves the request, GuideProfile.is_verified becomes True."""
        vr = GuideVerificationRequest.objects.create(
            guide=self.guide_profile,
            legal_name='Test Name',
            display_name='Test',
            status=GuideVerificationRequest.Status.SUBMITTED,
        )

        self.assertFalse(self.guide_profile.is_verified)

        # Simulate admin approving the request
        vr.status = GuideVerificationRequest.Status.APPROVED_LIMITED
        vr.save()

        # Check profile
        self.guide_profile.refresh_from_db()
        self.assertTrue(self.guide_profile.is_verified)

        # Simulate suspension
        vr.status = GuideVerificationRequest.Status.SUSPENDED
        vr.save()
        self.guide_profile.refresh_from_db()
        self.assertFalse(self.guide_profile.is_verified)

    def test_tourist_can_report_guide(self):
        """Tourist can submit a report against a guide."""
        self.client.force_login(self.tourist_user)
        url = reverse('guides:report_guide', args=[self.guide_profile.pk])
        
        data = {'reason': 'Unprofessional behavior'}
        response = self.client.post(url, data)
        
        self.assertRedirects(response, reverse('guides:detail', args=[self.guide_profile.pk]))
        
        report = GuideReport.objects.get(guide=self.guide_profile)
        self.assertEqual(report.reason, 'Unprofessional behavior')
        self.assertEqual(report.reported_by, self.tourist_user)

    def test_tourist_cannot_submit_verification(self):
        """Tourist should not be allowed to submit verification."""
        self.client.force_login(self.tourist_user)
        url = reverse('guides:verification_submit')
        
        response = self.client.get(url)
        # Should redirect to home with error message
        self.assertRedirects(response, reverse('home'))
