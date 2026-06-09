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

    def test_social_login_callback_new_user_is_standard(self):
        """Verify that new registration via social login callback always sets is_staff = False."""
        callback_url = reverse('social_login_callback', kwargs={'provider': 'google'})
        post_data = {
            'email': 'new_social_user@example.com',
            'name': 'New Social User',
            'role': 'Admin', # even if the form submitted 'Admin' (e.g. from malicious post manipulation)
        }
        
        response = self.client.post(callback_url, post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify user was created
        user = User.objects.get(email='new_social_user@example.com')
        # is_staff must be False regardless of role POSTed
        self.assertFalse(user.is_staff)

    def test_social_login_callback_existing_admin_retains_privileges(self):
        """Verify that an existing admin logs in via social callback and retains is_staff = True."""
        # Create an existing admin user
        admin_user = User.objects.create_user(
            username='google_existing_admin',
            email='existing_admin@example.com',
            password='somepassword'
        )
        admin_user.is_staff = True
        admin_user.save()
        
        callback_url = reverse('social_login_callback', kwargs={'provider': 'google'})
        post_data = {
            'email': 'existing_admin@example.com',
            'name': 'Existing Admin',
            'role': 'User', # even if the form POSTs 'User'
        }
        
        response = self.client.post(callback_url, post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify user is logged in and is_staff is still True
        admin_user.refresh_from_db()
        self.assertTrue(admin_user.is_staff)

    def test_social_login_callback_existing_user_retains_standard(self):
        """Verify that an existing standard user logs in via social callback and retains is_staff = False."""
        standard_user = User.objects.create_user(
            username='google_existing_user',
            email='existing_user@example.com',
            password='somepassword'
        )
        standard_user.is_staff = False
        standard_user.save()
        
        callback_url = reverse('social_login_callback', kwargs={'provider': 'google'})
        post_data = {
            'email': 'existing_user@example.com',
            'name': 'Existing User',
            'role': 'Admin', # even if the form POSTs 'Admin'
        }
        
        response = self.client.post(callback_url, post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify user is logged in and is_staff is still False
        standard_user.refresh_from_db()
        self.assertFalse(standard_user.is_staff)


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

