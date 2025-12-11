from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid

from django.contrib.auth import get_user_model

User = get_user_model()

class ChatGroup(models.Model):
    """
    Represents a group chat with multiple participants
    """
    GROUP_TYPES = (
        ('private', 'Private Group'),
        ('project', 'Project Group'),
         ('public', 'Public Group'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    group_type = models.CharField(max_length=20, choices=GROUP_TYPES, default='private')
    
    # Group image
    image = models.ImageField(
        upload_to='chat/group_images/%Y/%m/%d/',
        blank=True,
        null=True
    )
    
    # Admin and members
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    admins = models.ManyToManyField(User, related_name='admin_groups', blank=True)
    members = models.ManyToManyField(User, through='GroupMembership', related_name='member_groups')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    allow_member_invites = models.BooleanField(default=True)
    only_admins_can_message = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'chat_groups'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
            models.Index(fields=['group_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_member_count(self):
        return self.members.count()
    
    def is_admin(self, user):
        return self.admins.filter(id=user.id).exists()
    
    def is_member(self, user):
        return self.members.filter(id=user.id).exists()
    
    def get_last_message(self):
        return self.messages.filter(is_deleted=False).order_by('-created_at').first()


class GroupMembership(models.Model):
    """
    Through model for group membership with additional metadata
    """
    ROLES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('moderator', 'Moderator'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=20, choices=ROLES, default='member')
    
    # Metadata
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_members')
    
    # Notification settings
    muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_group_memberships'
        unique_together = ('group', 'user')
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['group', 'user']),
            models.Index(fields=['user', '-joined_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.group.name}"
    

class Conversation(models.Model):
    """
    Represents a one-on-one conversation between two users
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p1')
    participant_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p2')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Settings
    is_archived_p1 = models.BooleanField(default=False)
    is_archived_p2 = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'chat_conversations'
        unique_together = ('participant_1', 'participant_2')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
            models.Index(fields=['participant_1', 'participant_2']),
        ]
    
    def __str__(self):
        return f"{self.participant_1.username} <-> {self.participant_2.username}"
    
    def get_other_participant(self, user):
        return self.participant_2 if self.participant_1 == user else self.participant_1
    
    def get_last_message(self):
        return self.messages.filter(is_deleted=False).order_by('-created_at').first()
    
    def get_unread_count(self, user):
        return self.messages.filter(
            receiver=user,
            read_status='unread',
            is_deleted=False
        ).count()


class Message(models.Model):
    """
    Core message model - handles both group and individual messages
    """
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Video')
    )
    
    READ_STATUS = (
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_messages')
    
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_messages')
    
    # Message content
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    text = models.TextField(blank=True, null=True)
    
    # Reply functionality
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    read_status = models.CharField(max_length=20, choices=READ_STATUS, default='sent')
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['receiver', 'read_status']),
            models.Index(fields=['is_deleted', '-created_at']),
        ]
    
    def __str__(self):
        target = self.group.name if self.group else f"{self.sender.username} -> {self.receiver.username}"
        return f"{self.sender.username} in {target}: {self.text[:30]}"
    
    def is_group_message(self):
        return self.group is not None
    
    def mark_as_read(self, user=None):
        if self.is_group_message():
            # For group messages, create read receipt
            MessageReadReceipt.objects.get_or_create(
                message=self,
                user=user or self.receiver
            )
        else:
            # For individual messages, update status
            if user and user == self.receiver:
                self.read_status = 'read'
                self.save(update_fields=['read_status'])
    
    def get_read_by_users(self):
        """For group messages, get users who have read this message"""
        if self.is_group_message():
            return User.objects.filter(read_receipts__message=self)
        return []
    
    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])


class MessageReadReceipt(models.Model):
    """
    Tracks read status for group messages
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_receipts')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_message_read_receipts'
        unique_together = ('message', 'user')
        ordering = ['-read_at']
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', '-read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} read message {self.message.id}"


class MessageAttachment(models.Model):
    """
    Handles all file attachments: images, documents, PDFs, etc.
    """
    ATTACHMENT_TYPES = (
        ('image', 'Image'),
        ('document', 'Document'),
        ('pdf', 'PDF'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES)
    file = models.FileField(upload_to='chat/attachments/%Y/%m/%d/')
    
    # Metadata
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    
    # Image-specific fields
    thumbnail = models.ImageField(upload_to='chat/thumbnails/%Y/%m/%d/', blank=True, null=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_message_attachments'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['message', 'attachment_type']),
            models.Index(fields=['-uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.attachment_type}: {self.filename}"
    
    def is_image(self):
        return self.attachment_type == 'image'
    
    def is_document(self):
        return self.attachment_type in ['document', 'pdf']
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MessageReaction(models.Model):
    """
    Emoji reactions to messages (like WhatsApp/Slack)
    """
    REACTION_CHOICES = (
        ('👍', 'Thumbs Up'),
        ('❤️', 'Heart'),
        ('😂', 'Laugh'),
        ('😮', 'Wow'),
        ('😢', 'Sad'),
        ('😡', 'Angry'),
        ('🎉', 'Party'),
        ('👏', 'Clap'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_message_reactions'
        unique_together = ('message', 'user', 'emoji')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['message', 'emoji']),
        ]
    
    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to message"


class MessageForward(models.Model):
    """
    Tracks message forwarding history
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='forwards')
    forwarded_message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='forwarded_from')
    forwarded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forwarded_messages')
    forwarded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_message_forwards'
        ordering = ['-forwarded_at']
        indexes = [
            models.Index(fields=['original_message', '-forwarded_at']),
            models.Index(fields=['forwarded_by', '-forwarded_at']),
        ]
    
    def __str__(self):
        return f"{self.forwarded_by.username} forwarded message {self.original_message.id}"


class UserTypingStatus(models.Model):
    """
    Real-time typing indicators
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='typing_statuses')
    
    # Either group OR conversation
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='typing_users')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True, related_name='typing_users')
    
    started_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_typing_status'
        indexes = [
            models.Index(fields=['group', '-started_at']),
            models.Index(fields=['conversation', '-started_at']),
        ]
    
    def __str__(self):
        target = self.group.name if self.group else "conversation"
        return f"{self.user.username} typing in {target}"
    
    def is_active(self, timeout_seconds=10):
        """Check if typing status is still active"""
        return (timezone.now() - self.started_at).seconds < timeout_seconds


class MessageMention(models.Model):
    """
    Track @mentions in messages
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='mentions')
    mentioned_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentions')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'chat_message_mentions'
        unique_together = ('message', 'mentioned_user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mentioned_user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"@{self.mentioned_user.username} in message {self.message.id}"


class PinnedMessage(models.Model):
    """
    Pin important messages in groups
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='pins')
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='pinned_messages')
    pinned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pinned_messages')
    pinned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_pinned_messages'
        unique_together = ('message', 'group')
        ordering = ['-pinned_at']
        indexes = [
            models.Index(fields=['group', '-pinned_at']),
        ]
    
    def __str__(self):
        return f"Pinned: {self.message.text[:30]}"