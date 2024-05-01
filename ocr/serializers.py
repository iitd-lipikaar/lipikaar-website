from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.state import token_backend
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied

from ocr.models import (
    CustomUser,
    Upload,
    Detection,
)


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'password', 'email', 'can_login', 'can_compute', 'full_name',
        'phone_number','organization')
        read_only_fields = ('id',)

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            can_login=validated_data.get('can_login', False),
            can_compute=validated_data.get('can_compute', False),
            full_name=validated_data.get('full_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            organization=validated_data.get('organization', ''),
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        username = attrs['username']
        password = attrs['password']
        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid login credentials.")

        if not user.can_login:
            raise PermissionDenied('User does not have login permission.')

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['user'] = {
            'id': user.id,
            'username':user.username,
            'email':user.email,
            'fullName':user.full_name,
            'phoneNumber':user.phone_number,
            'canLogin':user.can_login,
            'canCompute':user.can_compute,
            'credits': user.credits,
        }

        return token


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        refresh_token_str = attrs['refresh']
        refresh_token = RefreshToken(refresh_token_str)
        decoded_payload = token_backend.decode(refresh_token_str, verify=True)
        user_id = decoded_payload['user_id']

        try:
            user = CustomUser.objects.get(id=user_id)
        except Exception as e:
            print(e)
            raise serializers.ValidationError('Invalid refresh token')

        if not user.can_login:
            raise PermissionDenied('User does not have login permission.')

        access_token = refresh_token.access_token

        access_token['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'fullName': user.full_name,
            'phoneNumber': user.phone_number,
            'canLogin': user.can_login,
            'canCompute': user.can_compute,
            'credits': user.credits,
        }

        data['access'] = str(access_token)

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        decoded_payload = token_backend.decode(token, verify=True)
        user_uid=decoded_payload['user_id']

        # Add custom claims
        token['user'] = {
            'id': user.id,
            'username':user.username,
            'email':user.email,
            'fullName':user.full_name,
            'phoneNumber':user.phone_number,
            'canLogin':user.can_login,
            'canCompute':user.can_compute,
            'canOK':user.can_compute,
        }

        return token


class ResetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    currentPassword = serializers.CharField()
    newPassword = serializers.CharField()

    def validate(self, data):
        # Check if username is provided
        if not data.get('username'):
            raise serializers.ValidationError('Username is required')

        # Check if currentPassword is provided
        if not data.get('currentPassword'):
            raise serializers.ValidationError('Current password is required')

        # Check if newPassword is provided
        if not data.get('newPassword'):
            raise serializers.ValidationError('New password is required')

        return data


class UploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = "__all__"


class DetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detection
        fields = ('id', 'image_filename', 'original_detections', 'detections', 'document_parser', 'parsing_postprocessor', 'text_recognizer')


class DetectionFilenameOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Detection
        fields = ('id', 'image_filename')


class DeleteUploadSerializer(serializers.Serializer):
    uploadIds = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )


class CustomOCRSerializer(serializers.Serializer):
    detectionId = serializers.CharField()
    xMin = serializers.CharField()
    yMin = serializers.CharField()
    xMax = serializers.CharField()
    yMax = serializers.CharField()

    def validate(self, data):
        if not data.get('detectionId'):
            raise serializers.ValidationError('detectionId is required.')

        if not data.get('xMin'):
            raise serializers.ValidationError('xMin is required.')

        if not data.get('yMin'):
            raise serializers.ValidationError('yMin is required.')

        if not data.get('xMax'):
            raise serializers.ValidationError('xMax is required.')

        if not data.get('yMax'):
            raise serializers.ValidationError('yMax is required.')

        return data


class MergeUploadsSerializer(serializers.Serializer):
    filename = serializers.CharField()
    uploadIds = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

    def validate(self, data):
        filename = data.get('filename')
        filename = filename.replace('_', '')
        filename = filename.replace('-', '')
        filename = filename.replace(' ', '')

        if not filename.isalnum():
            raise serializers.ValidationError('filename can only have letters, numbers, hyphens, spaces, or underscores.')

        upload_ids = data.get('uploadIds')
        if len(upload_ids) < 2:
            raise serializers.ValidationError('Provide at least two uploads to merge.')

        return data


class UploadChangeFilenameSerializer(serializers.Serializer):
    filename = serializers.CharField()

    def validate(self, data):
        filename = data.get('filename')
        filename = filename.replace('_', '')
        filename = filename.replace('-', '')
        filename = filename.replace(' ', '')

        if not filename.isalnum():
            raise serializers.ValidationError('filename can only have letters, numbers, hyphens, spaces, or underscores.')

        if len(data.keys()) > 1:
            raise serializers.ValidationError('Only filename update is supported.')

        return data


class IdSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)


class UploadIdSerializer(serializers.Serializer):
    uploadId = serializers.IntegerField(required=True)


class UploadIdsSerializer(serializers.Serializer):
    uploadIds = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

    
class PDFGenerationInputSerializer(serializers.Serializer):
    uploadId = serializers.IntegerField(required=True)
    pageNumbers = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False
    )
    pdfGenerationMode = serializers.ChoiceField(
        choices=('overlayedText', 'transparentText'),
        required=True
    )


class TransliterateInputSerializer(serializers.Serializer):
    sourceTexts = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )
    sourceLanguage = serializers.CharField()
    targetLanguage = serializers.CharField()
