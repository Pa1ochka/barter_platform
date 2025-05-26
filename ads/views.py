from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Ad, ExchangeProposal, Notification
from .forms import AdForm, ExchangeProposalForm


# Константы для сообщений
SUCCESS_MESSAGES = {
    'ad_created': 'Ваше объявление успешно размещено!',
    'ad_updated': 'Объявление обновлено.',
    'ad_deleted': 'Объявление удалено.',
    'proposal_sent': 'Предложение обмена отправлено.',
    'proposal_updated': 'Статус предложения изменен.',
    'notifications_read': 'Уведомления отмечены как прочитанные.',
}

ERROR_MESSAGES = {
    'not_owner': 'Это не ваше объявление!',
    'own_ad': 'Нельзя предлагать обмен на своё объявление.',
    'no_ads': 'Сначала создайте объявление для обмена.',
    'invalid_proposal': 'Вы не можете изменить это предложение.',
}


def add_notifications_to_context(context, user):
    """Добавляет непрочитанные уведомления в контекст для шаблонов."""
    if user.is_authenticated:
        context['unread_notifications'] = user.notifications.filter(is_read=False).order_by('-created_at')[:5]
    return context


@login_required
def ad_create(request):
    if request.method == 'POST':
        form = AdForm(request.POST)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.user = request.user
            ad.save()
            messages.success(request, SUCCESS_MESSAGES['ad_created'])
            return redirect('ad_list')
        messages.error(request, 'Ошибка в форме. Проверьте поля и попробуйте снова.')
    else:
        form = AdForm()

    context = {'form': form}
    return render(request, 'ads/ad_form.html', add_notifications_to_context(context, request.user))


@login_required
def ad_edit(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    if ad.user != request.user:
        messages.error(request, ERROR_MESSAGES['not_owner'])
        return redirect('ad_list')
    if request.method == 'POST':
        form = AdForm(request.POST, instance=ad)
        if form.is_valid():
            form.save()
            messages.success(request, SUCCESS_MESSAGES['ad_updated'])
            return redirect('ad_list')
        messages.error(request, 'Исправьте ошибки в форме.')
    else:
        form = AdForm(instance=ad)
    context = {'form': form, 'title': 'Редактировать объявление'}
    return render(request, 'ads/ad_form.html', add_notifications_to_context(context, request.user))


@login_required
def ad_delete(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    if ad.user != request.user:
        messages.error(request, ERROR_MESSAGES['not_owner'])
        return redirect('ad_list')
    if request.method == 'POST':
        ad.is_active = False  # Мягкое удаление
        ad.save()
        messages.success(request, SUCCESS_MESSAGES['ad_deleted'])
        return redirect('ad_list')
    context = {'ad': ad}
    return render(request, 'ads/ad_delete.html', add_notifications_to_context(context, request.user))


def ad_list(request):
    ads = Ad.objects.filter(is_active=True).order_by('-created_at')

    query = request.GET.get('q')
    category = request.GET.get('category')
    condition = request.GET.get('condition')
    if query:
        ads = ads.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category:
        ads = ads.filter(category=category)
    if condition:
        ads = ads.filter(condition=condition)

    paginator = Paginator(ads, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query or '',
        'category': category or '',
        'condition': condition or '',
        'categories': Ad.CATEGORY_CHOICES,
        'conditions': Ad.CONDITION_CHOICES,
    }
    return render(request, 'ads/ad_list.html', add_notifications_to_context(context, request.user))


def ad_detail(request, pk):
    ad = get_object_or_404(Ad, pk=pk, is_active=True)
    context = {'ad': ad, 'proposal_count': ad.get_proposal_count()}
    return render(request, 'ads/ad_detail.html', add_notifications_to_context(context, request.user))


@login_required
def exchange_proposal_create(request, ad_receiver_id):
    ad_receiver = get_object_or_404(Ad, pk=ad_receiver_id, is_active=True)
    if request.user == ad_receiver.user:
        messages.error(request, ERROR_MESSAGES['own_ad'])
        return redirect('ad_list')

    # Проверяем активные объявления
    user_ads = Ad.objects.filter(user=request.user, is_active=True)
    ads_count = user_ads.count()
    print(f"User={request.user.username}, Ads count={ads_count}, Ad titles={[ad.title for ad in user_ads]}")
    if ads_count == 0:
        messages.error(request, 'Нет активных объявлений для обмена. Создайте новое объявление или проверьте статус существующих.')
        return redirect('ad_create')

    # Очищаем старые сообщения
    messages.get_messages(request)

    if request.method == 'POST':
        form = ExchangeProposalForm(request.POST, user=request.user)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.ad_receiver = ad_receiver
            proposal.sender = request.user
            proposal.save()
            messages.success(request, SUCCESS_MESSAGES['proposal_sent'])
            Notification.objects.create(
                user=ad_receiver.user,
                message=f'Новое предложение обмена на "{ad_receiver.title}" от {request.user.username}.'
            )
            return redirect('exchange_proposal_list')
        messages.error(request, 'Ошибка в форме предложения.')
    else:
        form = ExchangeProposalForm(user=request.user)
        print(f"Form initialized for GET: Fields={form.fields['ad_sender'].queryset.count()}")

    context = {'form': form, 'ad_receiver': ad_receiver, 'has_ads': ads_count > 0}
    print("Rendering form template")
    return render(request, 'ads/exchange_proposal_form.html', add_notifications_to_context(context, request.user))


@login_required
def exchange_proposal_list(request):
    sent_proposals = ExchangeProposal.objects.filter(sender=request.user)
    received_proposals = ExchangeProposal.objects.filter(ad_receiver__user=request.user)

    context = {
        'sent_proposals': sent_proposals,
        'received_proposals': received_proposals,
    }
    return render(request, 'ads/exchange_proposal_list.html', add_notifications_to_context(context, request.user))


@login_required
def exchange_proposal_update(request, pk):
    proposal = get_object_or_404(ExchangeProposal, pk=pk)
    if proposal.ad_receiver.user != request.user:
        messages.error(request, ERROR_MESSAGES['invalid_proposal'])
        return redirect('exchange_proposal_list')

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['accepted', 'rejected']:
            proposal.status = status
            proposal.save()

            if status == 'accepted':
                # Помечаем оба объявления как неактивные
                proposal.ad_sender.is_active = False
                proposal.ad_sender.save()
                proposal.ad_receiver.is_active = False
                proposal.ad_receiver.save()

                # Уведомления для обоих пользователей
                Notification.objects.create(
                    user=proposal.sender,
                    message=f'Ваше предложение на "{proposal.ad_receiver.title}" принято. Вы получили "'
                            f'{proposal.ad_receiver.title}" от {proposal.ad_receiver.user.username}.'
                )
                Notification.objects.create(
                    user=proposal.ad_receiver.user,
                    message=f'Вы приняли предложение от {proposal.sender.username}. Вы получили "{proposal.ad_sender.title}".'
                )
            else:
                # Уведомление только для отправителя при отклонении
                Notification.objects.create(
                    user=proposal.sender,
                    message=f'Ваше предложение на "{proposal.ad_receiver.title}" отклонено.'
                )

            messages.success(request, SUCCESS_MESSAGES['proposal_updated'])
            return redirect('exchange_proposal_list')
        messages.error(request, 'Неверный статус.')

    context = {'proposal': proposal}
    return render(request, 'ads/exchange_proposal_update.html', add_notifications_to_context(context, request.user))


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Регистрация прошла успешно! Войдите в аккаунт.')
            return redirect('login')
        messages.error(request, 'Ошибка регистрации. Проверьте данные.')
    else:
        form = UserCreationForm()
    context = {'form': form}
    return render(request, 'registration/register.html', add_notifications_to_context(context, request.user))


@login_required
def mark_notifications_read(request):
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, SUCCESS_MESSAGES['notifications_read'])
    return redirect('ad_list')