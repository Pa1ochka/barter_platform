from django.db import models
from django.contrib.auth.models import User


class Ad(models.Model):
    CATEGORY_CHOICES = [
        ('electronics', 'Электроника'),
        ('clothing', 'Одежда'),
        ('books', 'Книги'),
        ('sports', 'Спорт'),
        ('other', 'Другое'),
    ]

    CONDITION_CHOICES = [
        ('new', 'Новое'),
        ('used', 'Б/у'),
        ('like_new', 'Как новое'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ads')
    title = models.CharField(max_length=200)
    description = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # Добавляем поле для активных объявлений

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'condition']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def get_proposal_count(self):
        """Возвращает количество предложений обмена для объявления."""
        return self.received_proposals.count()


class ExchangeProposal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принято'),
        ('rejected', 'Отклонено'),
    ]

    ad_sender = models.ForeignKey(Ad, related_name='sent_proposals', on_delete=models.CASCADE)
    ad_receiver = models.ForeignKey(Ad, related_name='received_proposals', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_proposals')
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Обмен: {self.ad_sender.title} -> {self.ad_receiver.title}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}..."