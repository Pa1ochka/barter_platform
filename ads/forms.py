from django import forms
from django.core.exceptions import ValidationError
from .models import Ad, ExchangeProposal


class AdForm(forms.ModelForm):
    class Meta:
        model = Ad
        fields = ['title', 'description', 'image_url', 'category', 'condition']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название объявления'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'Опишите товар'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Ссылка на изображение'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_title(self):
        title = self.cleaned_data['title']
        if len(title) < 5:
            raise ValidationError("Название должно быть длиннее 5 символов.")
        return title


class ExchangeProposalForm(forms.ModelForm):
    ad_sender = forms.ModelChoiceField(
        queryset=Ad.objects.none(),
        label="Выберите ваше объявление",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Добавьте комментарий'}),
        required=False,
        label="Комментарий"
    )

    class Meta:
        model = ExchangeProposal
        fields = ['ad_sender', 'comment']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['ad_sender'].queryset = Ad.objects.filter(user=user, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        ad_sender = cleaned_data.get('ad_sender')
        if ad_sender and not ad_sender.can_be_proposed():
            raise ValidationError("Выбрано неактивное объявление.")
        return cleaned_data