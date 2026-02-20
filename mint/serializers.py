from rest_framework import serializers

from mint.models import (  Sprint
)

from django.contrib.auth import get_user_model


User = get_user_model()

class UserMinimalSerializer(serializers.ModelSerializer):
    """Lightweight user info for nested relations"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'department',  'position', 'profile_image']


class SprintSerializer(serializers.ModelSerializer):
    """Sprint/Timeline serializer"""
    created_by = UserMinimalSerializer(read_only=True)
    project_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Sprint
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_project_count(self, obj):
        return obj.projects.count()
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
