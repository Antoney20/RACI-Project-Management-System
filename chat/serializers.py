from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ChatGroup, GroupMembership, Conversation, Message,
    MessageReadReceipt, MessageAttachment, MessageReaction,
    MessageForward, UserTypingStatus, MessageMention, PinnedMessage
)

User = get_user_model()


# ============================================================================
# USER SERIALIZERS
# ============================================================================

class UserMinimalSerializer(serializers.ModelSerializer):
    """Lightweight user info for nested relations"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'department', 'profile_image']


# ============================================================================
# GROUP SERIALIZERS
# ============================================================================

class GroupMembershipSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = GroupMembership
        fields = '__all__'


class ChatGroupListSerializer(serializers.ModelSerializer):
    """Lightweight for list views"""
    member_count = serializers.IntegerField(source='get_member_count', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatGroup
        fields = ['id', 'name', 'image', 'group_type', 'member_count', 
                  'last_message', 'unread_count', 'updated_at']
    
    def get_last_message(self, obj):
        last_msg = obj.get_last_message()
        if last_msg:
            return {
                'id': last_msg.id,
                'text': last_msg.text,
                'sender': last_msg.sender.username if last_msg.sender else None,
                'created_at': last_msg.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        user = self.context.get('request').user
        return obj.messages.filter(
            is_deleted=False
        ).exclude(
            read_receipts__user=user
        ).exclude(sender=user).count()


class ChatGroupDetailSerializer(serializers.ModelSerializer):
    created_by = UserMinimalSerializer(read_only=True)
    admins = UserMinimalSerializer(many=True, read_only=True)
    memberships = GroupMembershipSerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(source='get_member_count', read_only=True)
    
    class Meta:
        model = ChatGroup
        fields = '__all__'


class ChatGroupCreateSerializer(serializers.ModelSerializer):
    admin_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    member_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=True)
    
    class Meta:
        model = ChatGroup
        fields = ['name', 'description', 'group_type', 'image', 'allow_member_invites', 
                  'only_admins_can_message', 'admin_ids', 'member_ids']
    
    def create(self, validated_data):
        admin_ids = validated_data.pop('admin_ids', [])
        member_ids = validated_data.pop('member_ids', [])
        
        user = self.context['request'].user
        validated_data['created_by'] = user
        
        group = ChatGroup.objects.create(**validated_data)
        
        # Add creator as admin and member
        group.admins.add(user)
        GroupMembership.objects.create(group=group, user=user, role='admin')
        
        # Add other admins
        for admin_id in admin_ids:
            admin_user = User.objects.get(id=admin_id)
            group.admins.add(admin_user)
            GroupMembership.objects.get_or_create(
                group=group, user=admin_user, 
                defaults={'role': 'admin', 'invited_by': user}
            )
        
        # Add members
        for member_id in member_ids:
            if member_id != user.id:
                member_user = User.objects.get(id=member_id)
                GroupMembership.objects.get_or_create(
                    group=group, user=member_user,
                    defaults={'role': 'member', 'invited_by': user}
                )
        
        return group


# ============================================================================
# CONVERSATION SERIALIZERS
# ============================================================================

class ConversationSerializer(serializers.ModelSerializer):
    participant_1 = UserMinimalSerializer(read_only=True)
    participant_2 = UserMinimalSerializer(read_only=True)
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = '__all__'
    
    def get_other_participant(self, obj):
        user = self.context.get('request').user
        other = obj.get_other_participant(user)
        return UserMinimalSerializer(other).data
    
    def get_last_message(self, obj):
        last_msg = obj.get_last_message()
        if last_msg:
            return MessageListSerializer(last_msg).data
        return None
    
    def get_unread_count(self, obj):
        user = self.context.get('request').user
        return obj.get_unread_count(user)


# ============================================================================
# MESSAGE SERIALIZERS
# ============================================================================

class MessageAttachmentSerializer(serializers.ModelSerializer):
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    
    class Meta:
        model = MessageAttachment
        fields = '__all__'


class MessageReactionSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = MessageReaction
        fields = '__all__'


class MessageMentionSerializer(serializers.ModelSerializer):
    mentioned_user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = MessageMention
        fields = '__all__'


class MessageListSerializer(serializers.ModelSerializer):
    """Lightweight for list views"""
    sender = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'text', 'message_type', 'created_at', 
                  'read_status', 'is_edited', 'reply_to']


class MessageDetailSerializer(serializers.ModelSerializer):
    sender = UserMinimalSerializer(read_only=True)
    receiver = UserMinimalSerializer(read_only=True)
    reply_to = MessageListSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    mentions = MessageMentionSerializer(many=True, read_only=True)
    read_by_users = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = '__all__'
    
    def get_read_by_users(self, obj):
        if obj.is_group_message():
            users = obj.get_read_by_users()
            return UserMinimalSerializer(users, many=True).data
        return []


class MessageCreateSerializer(serializers.ModelSerializer):
    attachment_files = serializers.ListField(
        child=serializers.FileField(), 
        write_only=True, 
        required=False
    )
    mention_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Message
        fields = ['text', 'message_type', 'group', 'conversation', 'receiver', 
                  'reply_to', 'attachment_files', 'mention_user_ids']
    
    def create(self, validated_data):
        attachment_files = validated_data.pop('attachment_files', [])
        mention_user_ids = validated_data.pop('mention_user_ids', [])
        
        validated_data['sender'] = self.context['request'].user
        message = Message.objects.create(**validated_data)
        
        # Handle attachments
        for file in attachment_files:
            MessageAttachment.objects.create(
                message=message,
                file=file,
                filename=file.name,
                file_size=file.size,
                mime_type=file.content_type,
                attachment_type=self._get_attachment_type(file.content_type)
            )
        
        # Handle mentions
        for user_id in mention_user_ids:
            MessageMention.objects.create(
                message=message,
                mentioned_user_id=user_id
            )
        
        return message
    
    def _get_attachment_type(self, mime_type):
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type == 'application/pdf':
            return 'pdf'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        else:
            return 'document'


class PinnedMessageSerializer(serializers.ModelSerializer):
    message = MessageDetailSerializer(read_only=True)
    pinned_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = PinnedMessage
        fields = '__all__'


class MessageForwardSerializer(serializers.ModelSerializer):
    original_message = MessageListSerializer(read_only=True)
    forwarded_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = MessageForward
        fields = '__all__'


class UserTypingStatusSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = UserTypingStatus
        fields = '__all__'


class MessageReadReceiptSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = MessageReadReceipt
        fields = '__all__'