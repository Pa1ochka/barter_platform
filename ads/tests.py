from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from ads.models import Ad, ExchangeProposal, Notification
from ads.forms import AdForm, ExchangeProposalForm
from ads.views import ad_list, ad_create, ad_edit, ad_delete, exchange_proposal_create, exchange_proposal_update, exchange_proposal_list
from ads.api_views import AdViewSet, ExchangeProposalViewSet
from django.contrib import messages
from django.test.utils import override_settings


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

    def test_get_proposal_count(self):
        user2 = User.objects.create_user(username='user2', password='testpass123')
        ad2 = Ad.objects.create(user=user2, title='Ad 2', category='books', condition='used', is_active=True)
        ExchangeProposal.objects.create(ad_sender=ad2, ad_receiver=self.ad, sender=user2, comment='Test')
        self.assertEqual(self.ad.get_proposal_count(), 1)

    def test_can_be_proposed(self):
        self.assertTrue(self.ad.can_be_proposed())
        self.ad.is_active = False
        self.ad.save()
        self.assertFalse(self.ad.can_be_proposed())


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

    def test_exchange_proposal_form_inactive_ad(self):
        self.ad.is_active = False
        self.ad.save()
        form_data = {
            'ad_sender': self.ad.id,
            'comment': 'Test comment'
        }
        form = ExchangeProposalForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('ad_sender', form.errors)
        self.assertEqual(form.errors['ad_sender'],
                         ['Select a valid choice. That choice is not one of the available choices.'])


class AdViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
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

    def test_ad_list_view_search(self):
        response = self.client.get(reverse('ad_list'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Ad')
        response = self.client.get(reverse('ad_list'), {'q': 'Nonexistent'})
        self.assertNotContains(response, 'Test Ad')

    def test_ad_list_view_filter(self):
        response = self.client.get(reverse('ad_list'), {'category': 'electronics', 'condition': 'new'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Ad')
        response = self.client.get(reverse('ad_list'), {'category': 'books'})
        self.assertNotContains(response, 'Test Ad')

    def test_ad_detail_view(self):
        response = self.client.get(reverse('ad_detail', args=[self.ad.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/ad_detail.html')
        self.assertContains(response, 'Test Ad')

    def test_ad_detail_view_inactive(self):
        self.ad.is_active = False
        self.ad.save()
        response = self.client.get(reverse('ad_detail', args=[self.ad.id]))
        self.assertEqual(response.status_code, 404)

    def test_ad_create_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ad_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/ad_form.html')

    def test_ad_create_view_valid(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('ad_create'),
            {
                'title': 'Новое объявление',
                'description': 'Описание',
                'category': 'electronics',
                'condition': 'new'
            }
        )
        self.assertRedirects(response, reverse('ad_list'))
        self.assertTrue(Ad.objects.filter(title='Новое объявление').exists())

    def test_ad_create_view_invalid(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('ad_create'),
            {
                'title': 'Test',  # Слишком короткое
                'description': 'Описание',
                'category': 'electronics',
                'condition': 'new'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/ad_form.html')
        self.assertContains(response, 'Название должно быть длиннее 5 символов.')

    def test_ad_edit_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ad_edit', args=[self.ad.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/ad_form.html')

    def test_ad_edit_view_valid(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('ad_edit', args=[self.ad.id]),
            {
                'title': 'Обновлённое объявление',
                'description': 'Новое описание',
                'category': 'electronics',
                'condition': 'new'
            }
        )
        self.assertRedirects(response, reverse('ad_detail', args=[self.ad.id]))
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.title, 'Обновлённое объявление')

    def test_ad_edit_view_unauthorized(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(
            reverse('ad_edit', args=[self.ad.id]),
            {'title': 'Изменённое объявление'}
        )
        self.assertRedirects(response, reverse('ad_list'))
        self.assertEqual(
            list(messages.get_messages(response.wsgi_request))[0].message,
            'Это не ваше объявление!'
        )

    def test_ad_delete_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ad_delete', args=[self.ad.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/ad_delete.html')

    def test_ad_delete_view_valid(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('ad_delete', args=[self.ad.id]))
        self.assertRedirects(response, reverse('ad_list'))
        self.ad.refresh_from_db()
        self.assertFalse(self.ad.is_active)

    def test_ad_delete_view_unauthorized(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(reverse('ad_delete', args=[self.ad.id]))
        self.assertRedirects(response, reverse('ad_list'))
        self.assertEqual(
            list(messages.get_messages(response.wsgi_request))[0].message,
            'Это не ваше объявление!'
        )


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

    def test_exchange_proposal_create_view_get(self):
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('exchange_proposal_create', args=[self.ad2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/exchange_proposal_form.html')

    def test_exchange_proposal_create_view_valid(self):
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(
            reverse('exchange_proposal_create', args=[self.ad2.id]),
            {
                'ad_sender': self.ad1.id,
                'comment': 'Предлагаю обмен'
            }
        )
        self.assertRedirects(response, reverse('exchange_proposal_list'))
        self.assertTrue(ExchangeProposal.objects.filter(comment='Предлагаю обмен').exists())

    def test_exchange_proposal_create_view_invalid(self):
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(
            reverse('exchange_proposal_create', args=[self.ad2.id]),
            {
                'ad_sender': '',  # Пустое поле
                'comment': 'Предлагаю обмен'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/exchange_proposal_form.html')
        self.assertContains(response, 'This field is required.')

    def test_exchange_proposal_create_view_invalid_user(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(
            reverse('exchange_proposal_create', args=[self.ad2.id]),
            {
                'ad_sender': self.ad1.id,
                'comment': 'Предлагаю обмен'
            }
        )
        self.assertRedirects(response, reverse('ad_list'))
        self.assertEqual(
            list(messages.get_messages(response.wsgi_request))[0].message,
            'Нельзя предлагать обмен на своё объявление.'
        )

    def test_exchange_proposal_create_view_inactive_ad(self):
        self.ad2.is_active = False
        self.ad2.save()
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('exchange_proposal_create', args=[self.ad2.id]))
        self.assertRedirects(response, reverse('ad_list'))
        self.assertEqual(
            list(messages.get_messages(response.wsgi_request))[0].message,
            'Это объявление неактивно.'
        )

    def test_exchange_proposal_list_view(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(reverse('exchange_proposal_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/exchange_proposal_list.html')
        self.assertContains(response, 'Test proposal')

    def test_exchange_proposal_update_view_get(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(reverse('exchange_proposal_update', args=[self.proposal.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ads/exchange_proposal_update.html')

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

    def test_exchange_proposal_reject(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(
            reverse('exchange_proposal_update', args=[self.proposal.id]),
            {'status': 'rejected'}
        )
        self.assertRedirects(response, reverse('exchange_proposal_list'))
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, 'rejected')
        self.assertEqual(Notification.objects.filter(user=self.user1).count(), 1, "Уведомление для отправителя")

    def test_exchange_proposal_update_unauthorized(self):
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(
            reverse('exchange_proposal_update', args=[self.proposal.id]),
            {'status': 'accepted'}
        )
        self.assertRedirects(response, reverse('exchange_proposal_list'))
        self.assertEqual(
            list(messages.get_messages(response.wsgi_request))[0].message,
            'Вы не можете изменить это предложение.'
        )

    def test_exchange_proposal_update_invalid_status(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(
            reverse('exchange_proposal_update', args=[self.proposal.id]),
            {'status': 'invalid'}
        )
        self.assertRedirects(response, reverse('exchange_proposal_list'))
        self.assertEqual(
            list(messages.get_messages(response.wsgi_request))[0].message,
            'Неверный статус.'
        )


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

    def test_mark_notifications_read_unauthenticated(self):
        response = self.client.post(reverse('mark_notifications_read'))
        self.assertEqual(response.status_code, 302)  # Редирект на логин


class AdAPIViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.ad = Ad.objects.create(
            user=self.user,
            title='Test Ad',
            description='This is a test ad',
            category='electronics',
            condition='new',
            is_active=True
        )

    def test_ad_list_api(self):
        response = self.client.get(reverse('ad-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Test Ad')

    def test_ad_list_api_inactive(self):
        self.ad.is_active = False
        self.ad.save()
        response = self.client.get(reverse('ad-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_ad_create_api_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('ad-list'),
            {
                'title': 'API Ad',
                'description': 'Created via API',
                'category': 'books',
                'condition': 'used'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Ad.objects.filter(title='API Ad').exists())

    def test_ad_create_api_unauthenticated(self):
        response = self.client.post(
            reverse('ad-list'),
            {
                'title': 'Test Ad',
                'description': 'Test Description',
                'category': 'electronics',
                'condition': 'new',
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ad_update_api_authorized(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.put(
            reverse('ad-detail', args=[self.ad.id]),
            {
                'title': 'Updated Ad',
                'description': 'Updated via API',
                'category': 'electronics',
                'condition': 'new'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.title, 'Updated Ad')

    def test_ad_update_api_unauthorized(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.put(
            reverse('ad-detail', args=[self.ad.id]),
            {
                'title': 'Updated Ad',
                'description': 'Updated via API',
                'category': 'electronics',
                'condition': 'new'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ad_delete_api_authorized(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.delete(reverse('ad-detail', args=[self.ad.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        ad = Ad.objects.get(id=self.ad.id)
        self.assertFalse(ad.is_active)

    def test_ad_delete_api_unauthorized(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.delete(reverse('ad-detail', args=[self.ad.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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

    def test_proposal_list_api(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(reverse('exchangeproposal-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['comment'], 'Test proposal')

    def test_proposal_list_api_empty(self):
        self.client.login(username='user1', password='testpass123')
        self.proposal.delete()
        response = self.client.get(reverse('exchangeproposal-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_proposal_create_api_authenticated(self):
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(
            reverse('exchangeproposal-list'),
            {
                'ad_sender': self.ad1.id,
                'ad_receiver': self.ad2.id,
                'comment': 'API proposal'
            },
            format='json'
        )
        print(f"Response status: {response.status_code}, Response data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ExchangeProposal.objects.filter(comment='API proposal').exists())

    def test_proposal_create_api_unauthenticated(self):
        response = self.client.post(
            reverse('exchangeproposal-list'),
            {
                'ad_sender': self.ad1.id,
                'ad_receiver': self.ad2.id,
                'comment': 'API proposal'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_proposal_accept_api(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(
            reverse('exchangeproposal-accept', args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, 'accepted')
        self.assertFalse(Ad.objects.get(id=self.ad1.id).is_active)
        self.assertFalse(Ad.objects.get(id=self.ad2.id).is_active)
        self.assertEqual(Notification.objects.filter(user=self.user1).count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.user2).count(), 1)

    def test_proposal_reject_api(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(
            reverse('exchangeproposal-reject', args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, 'rejected')
        self.assertEqual(Notification.objects.filter(user=self.user1).count(), 1)

    def test_proposal_accept_api_unauthorized(self):
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(
            reverse('exchangeproposal-accept', args=[self.proposal.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UrlTests(TestCase):
    def test_ad_list_url(self):
        resolver = resolve('/ads/')
        self.assertEqual(resolver.func, ad_list)

    def test_ad_create_url(self):
        resolver = resolve('/ads/create/')
        self.assertEqual(resolver.func, ad_create)

    def test_ad_edit_url(self):
        resolver = resolve('/ads/1/edit/')
        self.assertEqual(resolver.func, ad_edit)

    def test_ad_delete_url(self):
        resolver = resolve('/ads/1/delete/')
        self.assertEqual(resolver.func, ad_delete)

    def test_exchange_proposal_create_url(self):
        resolver = resolve('/ads/1/propose/')
        self.assertEqual(resolver.func, exchange_proposal_create)

    def test_exchange_proposal_list_url(self):
        resolver = resolve('/proposals/')
        self.assertEqual(resolver.func, exchange_proposal_list)

    def test_exchange_proposal_update_url(self):
        resolver = resolve('/proposals/1/update/')
        self.assertEqual(resolver.func, exchange_proposal_update)
