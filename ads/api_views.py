from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from ads.models import Ad, ExchangeProposal, Notification
from ads.serializers import AdSerializer, ExchangeProposalSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class AdViewSet(viewsets.ModelViewSet):
    queryset = Ad.objects.filter(is_active=True)
    serializer_class = AdSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('q')
        category = self.request.query_params.get('category')
        condition = self.request.query_params.get('condition')

        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
        if category:
            queryset = queryset.filter(category=category)
        if condition:
            queryset = queryset.filter(condition=condition)

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def proposals(self, request, pk=None):
        ad = self.get_object()
        proposals = ad.received_proposals.filter(status='pending')
        serializer = ExchangeProposalSerializer(proposals, many=True)
        return Response(serializer.data)


class ExchangeProposalViewSet(viewsets.ModelViewSet):
    queryset = ExchangeProposal.objects.all()
    serializer_class = ExchangeProposalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExchangeProposal.objects.filter(
            Q(sender=self.request.user) | Q(ad_receiver__user=self.request.user)
        ).order_by('-created_at')

    def perform_create(self, serializer):
        ad_receiver = Ad.objects.get(pk=self.request.data.get('ad_receiver'))
        ad_sender = Ad.objects.get(pk=self.request.data.get('ad_sender'))
        if ad_receiver.user == self.request.user or ad_receiver.is_active is False:
            raise serializer.ValidationError("Нельзя предложить обмен на своё или неактивное объявление.")
        serializer.save(sender=self.request.user, ad_receiver=ad_receiver, ad_sender=ad_sender)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def accept(self, request, pk=None):
        proposal = self.get_object()
        if proposal.ad_receiver.user != request.user:
            return Response({"error": "Это не ваше предложение."}, status=403)
        proposal.status = 'accepted'
        proposal.save()
        Notification.objects.create(
            user=proposal.sender,
            message=f'Ваше предложение на "{proposal.ad_receiver.title}" принято.'
        )
        return Response({"status": "Предложение принято."})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        proposal = self.get_object()
        if proposal.ad_receiver.user != request.user:
            return Response({"error": "Это не ваше предложение."}, status=403)
        proposal.status = 'rejected'
        proposal.save()
        Notification.objects.create(
            user=proposal.sender,
            message=f'Ваше предложение на "{proposal.ad_receiver.title}" отклонено.'
        )
        return Response({"status": "Предложение отклонено."})