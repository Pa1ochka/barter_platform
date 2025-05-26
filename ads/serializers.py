from rest_framework import serializers
from .models import Ad, ExchangeProposal


class AdSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    category = serializers.ChoiceField(choices=Ad.CATEGORY_CHOICES)
    condition = serializers.ChoiceField(choices=Ad.CONDITION_CHOICES)
    proposal_count = serializers.SerializerMethodField()

    class Meta:
        model = Ad
        fields = ['id', 'user', 'title', 'description', 'image_url', 'category', 'condition', 'is_active', 'proposal_count', 'created_at']
        read_only_fields = ['id', 'user', 'created_at', 'proposal_count']

    def get_proposal_count(self, obj):
        print(f"Object type: {type(obj)}, Object: {obj}")
        if isinstance(obj, dict):
            return 0
        return obj.get_proposal_count()


class ExchangeProposalSerializer(serializers.ModelSerializer):
    ad_sender = serializers.PrimaryKeyRelatedField(queryset=Ad.objects.filter(is_active=True))
    ad_receiver = serializers.PrimaryKeyRelatedField(queryset=Ad.objects.filter(is_active=True))
    status = serializers.ChoiceField(choices=ExchangeProposal.STATUS_CHOICES, default='pending')

    class Meta:
        model = ExchangeProposal
        fields = ['id', 'ad_sender', 'ad_receiver', 'comment', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        if not data.get('status'):
            data['status'] = 'pending'
        return data