from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from ads.models import Ad, ExchangeProposal, Notification
from ads.forms import AdForm, ExchangeProposalForm


class AdModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.ad = Ad.objects.create(
            user=self.user,
            title='Test Ad',
            description='This is a test ad',
            category='electronics',
            condition='new',
            is_active=True
        )
        Ad.objects.filter(id=self.ad.id).update(created_at=timezone.now() - timedelta(minutes=5))
        self.ad.refresh_from_db()

    def test_ad_str(self):
        self.assertEqual(str(self.ad), 'Test Ad (Электроника)')

    def test_ad_ordering(self):
        ad2 = Ad.objects.create(
            user=self.user,
            title='Test Ad 2',
            description='Another test ad',
            category='books',
            condition='used',
            is_active=True
        )
        Ad.objects.filter(id=ad2.id).update(created_at=timezone.now())
        ad2.refresh_from_db()
        ads = Ad.objects.filter(is_active=True)
        self.assertEqual(ads[0], ad2, "Новейшее объявление должно быть первым")
        self.assertGreater(ads[0].created_at, ads[1].created_at)

    def test_ad_inactive(self):
        self.ad.is_active = False
        self.ad.save()
        ads = Ad.objects.filter(is_active=True)
        self.assertFalse(ads.filter(id=self.ad.id).exists())


class ExchangeProposalModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.ad1 = Ad.objects.create(
            user=self.user1,
            title='Ad 1',
            description='First ad',
            category='electronics',
            condition='new',
            is_active=True
        )
        self.ad2 = Ad.objects.create(
            user=self.user2,
            title='Ad 2',
            description='Second ad',
            category='books',
            condition='used',
            is_active=True
        )
        self.proposal = ExchangeProposal.objects.create(
            ad_sender=self.ad1,
            ad_receiver=self.ad2,
            sender=self.user1,
            comment='Test proposal',
            status='pending'
        )

    def test_proposal_str(self):
        self.assertEqual(str(self.proposal), f"Обмен: {self.ad1.title} -> {self.ad2.title}")

    def test_proposal_status_default(self):
        self.assertEqual(self.proposal.status, 'pending')


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.notification = Notification.objects.create(
            user=self.user,
            message='Test notification'
        )

    def test_notification_str(self):
        self.assertEqual(str(self.notification), f"{self.user.username}: Test notification...")

    def test_notification_default_is_read(self):
        self.assertFalse(self.notification.is_read)


class AdFormTest(TestCase):
    def test_ad_form_valid(self):
        form_data = {
            'title': 'Test Ad Long Title',
            'description': 'This is a test ad',
            'image_url': 'https://example.com/image.jpg',
            'category': 'electronics',
            'condition': 'new'
        }
        form = AdForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_ad_form_invalid_title(self):
        form_data = {
            'title': 'Test',  # Слишком короткое
            'description': 'This is a test ad',
            'category': 'electronics',
            'condition': 'new'
        }
        form = AdForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)


class ExchangeProposalFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.ad = Ad.objects.create(
            user=self.user,
            title='Test Ad',
            description='This is a test ad',
            category='electronics',
            condition='new',
            is_active=True
        )

    def test_exchange_proposal_form_valid(self):
        form_data = {
            'ad_sender': self.ad.id,
            'comment': 'Test comment'
        }
        form = ExchangeProposalForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_exchange_proposal_form_no_ads(self):
        form = ExchangeProposalForm(user=User.objects.create_user(username='newuser', password='testpass123'))
        self.assertFalse(form.fields['ad_sender'].queryset.exists())


class AdViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.ad = Ad.objects.create(
            user=self.user,
            title='Test Ad',
            description='This is a test ad',
            category='electronics',
            condition='new',
            is_active=True
        )

    def test_ad_list_view(self):
        response = self.client.get(reverse('ad_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/ad_list.html')
        self.assertContains(response, 'Test Ad')

    def test_ad_detail_view_inactive(self):
        self.ad.is_active = False
        self.ad.save()
        response = self.client.get(reverse('ad_detail', args=[self.ad.id]))
        self.assertEqual(response.status_code, 404)


class ExchangeProposalViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.ad1 = Ad.objects.create(
            user=self.user1,
            title='Ad 1',
            description='First ad',
            category='electronics',
            condition='new',
            is_active=True
        )
        self.ad2 = Ad.objects.create(
            user=self.user2,
            title='Ad 2',
            description='Second ad',
            category='books',
            condition='used',
            is_active=True
        )
        self.proposal = ExchangeProposal.objects.create(
            ad_sender=self.ad1,
            ad_receiver=self.ad2,
            sender=self.user1,
            comment='Test proposal',
            status='pending'
        )

    def test_exchange_proposal_create_view_invalid(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(reverse('exchange_proposal_create', args=[self.ad2.id]), {})
        self.assertRedirects(response, reverse('ad_list'))

    def test_exchange_proposal_accept(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(
            reverse('exchange_proposal_update', args=[self.proposal.id]),
            {'status': 'accepted'}
        )
        self.assertRedirects(response, reverse('exchange_proposal_list'))
        self.proposal.refresh_from_db()
        self.ad1.refresh_from_db()
        self.ad2.refresh_from_db()
        self.assertEqual(self.proposal.status, 'accepted')
        self.assertFalse(self.ad1.is_active, "Объявление отправителя должно быть неактивным")
        self.assertFalse(self.ad2.is_active, "Объявление получателя должно быть неактивным")
        self.assertEqual(Notification.objects.filter(user=self.user1).count(), 1, "Уведомление для отправителя")
        self.assertEqual(Notification.objects.filter(user=self.user2).count(), 1, "Уведомление для получателя")

class NotificationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.notification = Notification.objects.create(
            user=self.user,
            message='Test notification'
        )

    def test_mark_notifications_read(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('mark_notifications_read'))
        self.assertRedirects(response, reverse('ad_list'))
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)


class AdAPIViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.ad = Ad.objects.create(
            user=self.user,
            title='Test Ad',
            description='This is a test ad',
            category='electronics',
            condition='new',
            is_active=True
        )

    def test_ad_list_api_inactive(self):
        self.ad.is_active = False
        self.ad.save()
        response = self.client.get(reverse('ad-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class ExchangeProposalAPIViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.ad1 = Ad.objects.create(
            user=self.user1,
            title='Ad 1',
            description='First ad',
            category='electronics',
            condition='new',
            is_active=True
        )
        self.ad2 = Ad.objects.create(
            user=self.user2,
            title='Ad 2',
            description='Second ad',
            category='books',
            condition='used',
            is_active=True
        )
        self.proposal = ExchangeProposal.objects.create(
            ad_sender=self.ad1,
            ad_receiver=self.ad2,
            sender=self.user1,
            comment='Test proposal',
            status='pending'
        )

    def test_proposal_list_api_empty(self):
        self.client.login(username='user1', password='testpass123')
        self.proposal.delete()
        response = self.client.get(reverse('exchangeproposal-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)