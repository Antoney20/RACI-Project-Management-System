from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Max
from django.shortcuts import get_object_or_404
from .models import (
    ChatGroup, GroupMembership, Conversation, Message,
    MessageReadReceipt, MessageAttachment, MessageReaction,
    MessageForward, UserTypingStatus, MessageMention, PinnedMessage
)
from .serializers import (
    ChatGroupListSerializer, ChatGroupDetailSerializer, ChatGroupCreateSerializer,
    ConversationSerializer, MessageListSerializer, MessageDetailSerializer,
    MessageCreateSerializer, MessageAttachmentSerializer, MessageReactionSerializer,
    PinnedMessageSerializer, MessageForwardSerializer, UserTypingStatusSerializer,
    MessageReadReceiptSerializer, GroupMembershipSerializer
)


class ChatGroupViewSet(viewsets.ModelViewSet):
    """Chat group management"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return ChatGroup.objects.filter(
            members=user, is_active=True
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatGroupListSerializer
        elif self.action == 'create':
            return ChatGroupCreateSerializer
        return ChatGroupDetailSerializer
    
    @action(detail=True, methods=['post'])
    def add_members(self, request, pk=None):
        """Add members to group"""
        group = self.get_object()
        
        if not group.is_admin(request.user):
            return Response(
                {'error': 'Only admins can add members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        member_ids = request.data.get('member_ids', [])
        added = []
        
        for member_id in member_ids:
            membership, created = GroupMembership.objects.get_or_create(
                group=group, user_id=member_id,
                defaults={'invited_by': request.user}
            )
            if created:
                added.append(member_id)
        
        return Response({'added': added, 'count': len(added)})
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Remove member from group"""
        group = self.get_object()
        
        if not group.is_admin(request.user):
            return Response(
                {'error': 'Only admins can remove members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        member_id = request.data.get('member_id')
        GroupMembership.objects.filter(group=group, user_id=member_id).delete()
        
        return Response({'removed': member_id})
    
    @action(detail=True, methods=['post'])
    def make_admin(self, request, pk=None):
        """Promote member to admin"""
        group = self.get_object()
        
        if not group.is_admin(request.user):
            return Response(
                {'error': 'Only admins can promote members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        member_id = request.data.get('member_id')
        membership = get_object_or_404(GroupMembership, group=group, user_id=member_id)
        membership.role = 'admin'
        membership.save()
        
        group.admins.add(membership.user)
        
        return Response({'success': True})
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all group members"""
        group = self.get_object()
        memberships = group.memberships.all()
        serializer = GroupMembershipSerializer(memberships, many=True)
        return Response(serializer.data)


class ConversationViewSet(viewsets.ModelViewSet):
    """One-on-one conversations"""
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer
    
    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(participant_1=user) | Q(participant_2=user)
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time')
    
    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        """Get or create conversation with another user"""
        other_user_id = request.data.get('user_id')
        
        if not other_user_id:
            return Response(
                {'error': 'user_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # Try to find existing conversation
        conversation = Conversation.objects.filter(
            Q(participant_1=user, participant_2_id=other_user_id) |
            Q(participant_1_id=other_user_id, participant_2=user)
        ).first()
        
        if not conversation:
            # Create new conversation (ensure consistent ordering)
            if user.id < other_user_id:
                conversation = Conversation.objects.create(
                    participant_1=user,
                    participant_2_id=other_user_id
                )
            else:
                conversation = Conversation.objects.create(
                    participant_1_id=other_user_id,
                    participant_2=user
                )
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive conversation"""
        conversation = self.get_object()
        user = request.user
        
        if conversation.participant_1 == user:
            conversation.is_archived_p1 = True
        else:
            conversation.is_archived_p2 = True
        
        conversation.save()
        return Response({'archived': True})


class MessageViewSet(viewsets.ModelViewSet):
    """Message CRUD operations"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Filter by group or conversation
        group_id = self.request.query_params.get('group')
        conversation_id = self.request.query_params.get('conversation')
        
        queryset = Message.objects.filter(is_deleted=False)
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        elif conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        else:
            # Return messages from user's conversations and groups
            queryset = queryset.filter(
                Q(conversation__participant_1=user) |
                Q(conversation__participant_2=user) |
                Q(group__members=user)
            )
        
        return queryset.select_related(
            'sender', 'receiver', 'reply_to'
        ).prefetch_related(
            'attachments', 'reactions', 'mentions'
        ).order_by('created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MessageListSerializer
        elif self.action == 'create':
            return MessageCreateSerializer
        return MessageDetailSerializer
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        message.mark_as_read(request.user)
        return Response({'read': True})
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Add reaction to message"""
        message = self.get_object()
        emoji = request.data.get('emoji')
        
        if not emoji:
            return Response(
                {'error': 'emoji required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            emoji=emoji
        )
        
        serializer = MessageReactionSerializer(reaction)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def remove_reaction(self, request, pk=None):
        """Remove reaction from message"""
        message = self.get_object()
        emoji = request.query_params.get('emoji')
        
        MessageReaction.objects.filter(
            message=message,
            user=request.user,
            emoji=emoji
        ).delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def forward(self, request, pk=None):
        """Forward message to group or conversation"""
        original_message = self.get_object()
        
        group_id = request.data.get('group_id')
        conversation_id = request.data.get('conversation_id')
        
        if not group_id and not conversation_id:
            return Response(
                {'error': 'group_id or conversation_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create forwarded message
        forwarded_message = Message.objects.create(
            sender=request.user,
            text=original_message.text,
            message_type=original_message.message_type,
            group_id=group_id,
            conversation_id=conversation_id,
            receiver_id=request.data.get('receiver_id')
        )
        
        # Track forward
        MessageForward.objects.create(
            original_message=original_message,
            forwarded_message=forwarded_message,
            forwarded_by=request.user
        )
        
        serializer = MessageDetailSerializer(forwarded_message)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def edit(self, request, pk=None):
        """Edit message text"""
        message = self.get_object()
        
        if message.sender != request.user:
            return Response(
                {'error': 'Can only edit own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_text = request.data.get('text')
        if new_text:
            message.text = new_text
            message.is_edited = True
            message.save()
        
        serializer = MessageDetailSerializer(message)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete message"""
        message = self.get_object()
        
        if message.sender != request.user:
            return Response(
                {'error': 'Can only delete own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PinnedMessageViewSet(viewsets.ModelViewSet):
    """Pinned messages in groups"""
    permission_classes = [IsAuthenticated]
    serializer_class = PinnedMessageSerializer
    
    def get_queryset(self):
        group_id = self.request.query_params.get('group')
        queryset = PinnedMessage.objects.all()
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        return queryset.select_related('message', 'pinned_by', 'group')
    
    def create(self, request, *args, **kwargs):
        """Pin a message"""
        message_id = request.data.get('message_id')
        group_id = request.data.get('group_id')
        
        message = get_object_or_404(Message, id=message_id, group_id=group_id)
        group = message.group
        
        if not group.is_admin(request.user):
            return Response(
                {'error': 'Only admins can pin messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pinned, created = PinnedMessage.objects.get_or_create(
            message=message,
            group=group,
            defaults={'pinned_by': request.user}
        )
        
        serializer = self.get_serializer(pinned)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TypingStatusViewSet(viewsets.ModelViewSet):
    """Typing indicators"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserTypingStatusSerializer
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        group_id = self.request.query_params.get('group')
        conversation_id = self.request.query_params.get('conversation')
        
        queryset = UserTypingStatus.objects.all()
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        elif conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        return queryset.select_related('user')
    
    def create(self, request, *args, **kwargs):
        """Set user as typing"""
        group_id = request.data.get('group_id')
        conversation_id = request.data.get('conversation_id')
        
        typing_status, created = UserTypingStatus.objects.update_or_create(
            user=request.user,
            group_id=group_id,
            conversation_id=conversation_id
        )
        
        serializer = self.get_serializer(typing_status)
        return Response(serializer.data)