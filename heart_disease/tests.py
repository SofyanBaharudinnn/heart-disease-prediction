# pyrefly: ignore [missing-import]
from django.test import TestCase, Client
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.urls import reverse

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


