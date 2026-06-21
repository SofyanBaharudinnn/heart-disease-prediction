# pyrefly: ignore [missing-import]
from django.test import TestCase, Client
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.urls import reverse
import os
import shutil

class RegistrationAccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        
    def test_standard_registration_creates_standard_user(self):
        """Verify that standard registration always creates a standard user (is_staff=False)."""
        register_url = reverse('register')
        post_data = {
            'username': 'standard_test_user',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
        }
        response = self.client.post(register_url, post_data)
        
        # Check if redirection occurred (meaning registration succeeded)
        self.assertEqual(response.status_code, 302)
        
        # Verify user was created and is not staff/admin
        user = User.objects.get(username='standard_test_user')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_registration_without_numbers_fails(self):
        """Verify that registration fails if the password does not contain any numbers."""
        register_url = reverse('register')
        post_data = {
            'username': 'no_number_user',
            'password1': 'onlyletters',
            'password2': 'onlyletters',
        }
        response = self.client.post(register_url, post_data)
        
        # Should not redirect (should remain on register page with error)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='no_number_user').exists())


# pyrefly: ignore [missing-import]
from django.test import override_settings
# pyrefly: ignore [missing-import]
from django.core.cache import cache

class RateLimitMiddlewareTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    @override_settings(DEBUG=False)
    def test_predict_rate_limiting_triggered(self):
        """Verify that making more than 10 requests to /predict/ triggers HTTP 429."""
        predict_url = reverse('predict')
        
        # Make 10 requests, which is the limit
        for i in range(10):
            response = self.client.get(predict_url)
            # Should be OK (either 200 or 302/redirect, but not 429)
            self.assertNotEqual(response.status_code, 429)
            
        # The 11th request must trigger rate limiting (HTTP 429)
        response = self.client.get(predict_url)
        self.assertEqual(response.status_code, 429)
        self.assertIn('text/html', response['Content-Type'])
        self.assertIn('Batas Permintaan Terlampaui', response.content.decode('utf-8'))

    @override_settings(DEBUG=True)
    def test_rate_limiting_skipped_in_debug_mode(self):
        """Verify that rate limiting is completely skipped when DEBUG is True."""
        predict_url = reverse('predict')
        
        # Make 12 requests (exceeding the limit of 10)
        for i in range(12):
            response = self.client.get(predict_url)
            self.assertNotEqual(response.status_code, 429)


from heart_disease.models import ContactMessage

class ManageInquiriesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@example.com',
            password='password123'
        )
        self.admin_user.is_staff = True
        self.admin_user.save()
        
        self.regular_user = User.objects.create_user(
            username='regular_test',
            email='user@example.com',
            password='password123'
        )
        
        self.inquiry = ContactMessage.objects.create(
            name='Test Sender',
            email='sender@example.com',
            subject='Testing Subject',
            message='Testing Message Body'
        )

    def test_anonymous_and_regular_user_cannot_access_manage_or_modify(self):
        # Manage inquiries page
        response = self.client.get(reverse('manage_inquiries'))
        self.assertEqual(response.status_code, 302) # redirects to login
        
        self.client.login(username='regular_test', password='password123')
        response = self.client.get(reverse('manage_inquiries'))
        self.assertEqual(response.status_code, 302) # redirects to login because not is_staff
        
        # Edit inquiry POST
        response = self.client.post(reverse('edit_inquiry', args=[self.inquiry.id]), {
            'name': 'Malicious Edit'
        })
        self.assertEqual(response.status_code, 302)
        
        # Delete inquiry POST
        response = self.client.post(reverse('delete_inquiry', args=[self.inquiry.id]))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_edit_inquiry(self):
        self.client.login(username='admin_test', password='password123')
        edit_url = reverse('edit_inquiry', args=[self.inquiry.id])
        
        # Invalid payload (missing required)
        response = self.client.post(edit_url, {
            'name': 'Updated Name',
            'email': '',
            'subject': 'Updated Subject',
            'message': 'Updated Message'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        
        # Valid payload
        response = self.client.post(edit_url, {
            'name': 'Updated Name',
            'email': 'updated@example.com',
            'phone': '08123456789',
            'company': 'Updated Company',
            'subject': 'Updated Subject',
            'message': 'Updated Message'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Verify changes in DB
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.name, 'Updated Name')
        self.assertEqual(self.inquiry.email, 'updated@example.com')
        self.assertEqual(self.inquiry.phone, '08123456789')
        self.assertEqual(self.inquiry.company, 'Updated Company')
        self.assertEqual(self.inquiry.subject, 'Updated Subject')
        self.assertEqual(self.inquiry.message, 'Updated Message')

    def test_admin_can_delete_inquiry(self):
        self.client.login(username='admin_test', password='password123')
        delete_url = reverse('delete_inquiry', args=[self.inquiry.id])
        
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302) # redirects to manage_inquiries
        
        # Verify deleted in DB
        self.assertFalse(ContactMessage.objects.filter(id=self.inquiry.id).exists())


import pickle
from django.core.files.uploadedfile import SimpleUploadedFile
from heart_disease.models import ModelMetrics

class ModelIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@example.com',
            password='password123'
        )
        self.admin_user.is_staff = True
        self.admin_user.save()
        
        self.regular_user = User.objects.create_user(
            username='regular_test',
            email='user@example.com',
            password='password123'
        )
        
    def test_anonymous_and_regular_user_cannot_access_integration(self):
        # View page
        response = self.client.get(reverse('model_integration'))
        self.assertEqual(response.status_code, 302)
        
        # Upload POST
        response = self.client.post(reverse('upload_model'))
        self.assertEqual(response.status_code, 302)
        
        # Delete POST
        response = self.client.post(reverse('delete_model_metrics', args=[1]))
        self.assertEqual(response.status_code, 302)
        
        # Logged in as regular user
        self.client.login(username='regular_test', password='password123')
        
        response = self.client.get(reverse('model_integration'))
        self.assertEqual(response.status_code, 302)
        
        response = self.client.post(reverse('upload_model'))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access_integration_page(self):
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('model_integration'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'heart_disease/model_integration.html')

    def test_upload_invalid_file_extension(self):
        self.client.login(username='admin_test', password='password123')
        
        # Uploading txt file instead of pkl
        model_file = SimpleUploadedFile("model.txt", b"dummy model", content_type="text/plain")
        scaler_file = SimpleUploadedFile("scaler.txt", b"dummy scaler", content_type="text/plain")
        
        response = self.client.post(reverse('upload_model'), {
            'model_file': model_file,
            'scaler_file': scaler_file,
            'accuracy': 85.0,
            'precision': 84.0,
            'recall': 83.0,
            'f1_score': 82.0,
            'roc_auc': 81.0,
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify no ModelMetrics was created
        self.assertFalse(ModelMetrics.objects.exists())

    def test_upload_valid_model_and_metrics(self):
        self.client.login(username='admin_test', password='password123')
        
        # Create dummy pkl content
        model_data = pickle.dumps("dummy_model")
        scaler_data = pickle.dumps("dummy_scaler")
        
        model_file = SimpleUploadedFile("random_forest_model.pkl", model_data, content_type="application/octet-stream")
        scaler_file = SimpleUploadedFile("scaler.pkl", scaler_data, content_type="application/octet-stream")
        
        # Back up existing files in media/models/ if any to avoid deleting them during cleanup
        from heart_disease.ml_model import MODEL_PATH, SCALER_PATH
        model_backup = MODEL_PATH + '.bak'
        scaler_backup = SCALER_PATH + '.bak'
        
        model_exists = os.path.exists(MODEL_PATH)
        scaler_exists = os.path.exists(SCALER_PATH)
        
        if model_exists:
            shutil.copy2(MODEL_PATH, model_backup)
        if scaler_exists:
            shutil.copy2(SCALER_PATH, scaler_backup)
            
        try:
            response = self.client.post(reverse('upload_model'), {
                'model_file': model_file,
                'scaler_file': scaler_file,
                'accuracy': 85.5,
                'precision': 84.4,
                'recall': 83.3,
                'f1_score': 82.2,
                'roc_auc': 81.1,
            })
            self.assertEqual(response.status_code, 302)
            
            # Verify file was written to disk
            self.assertTrue(os.path.exists(MODEL_PATH))
            self.assertTrue(os.path.exists(SCALER_PATH))
            
            # Verify metric entry in DB
            metric = ModelMetrics.objects.first()
            self.assertIsNotNone(metric)
            self.assertAlmostEqual(metric.accuracy, 0.855)
            self.assertAlmostEqual(metric.precision, 0.844)
            self.assertAlmostEqual(metric.recall, 0.833)
            self.assertAlmostEqual(metric.f1_score, 0.822)
            self.assertAlmostEqual(metric.roc_auc, 0.811)
            
            # Test delete model metrics
            delete_url = reverse('delete_model_metrics', args=[metric.id])
            delete_response = self.client.post(delete_url)
            self.assertEqual(delete_response.status_code, 302)
            
            # Verify metric deleted in DB and files deleted from disk
            self.assertFalse(ModelMetrics.objects.filter(id=metric.id).exists())
            self.assertFalse(os.path.exists(MODEL_PATH))
            self.assertFalse(os.path.exists(SCALER_PATH))
            
        finally:
            # Restore backups if any
            if model_exists:
                shutil.copy2(model_backup, MODEL_PATH)
                os.remove(model_backup)
            if scaler_exists:
                shutil.copy2(scaler_backup, SCALER_PATH)
                os.remove(scaler_backup)



