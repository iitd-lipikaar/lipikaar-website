import os
import shutil
import uuid
import json
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib import messages
from django.utils.translation import ngettext
from django_celery_results.admin import TaskResult, GroupResult
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponseRedirect
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from ocr.models import CustomUser, Upload, Detection
from ocr.cache import (
    create_folder_in_cache,
    download_from_cloud_storage_to_cache,
    zip_folder_in_cache,
    remove_folder_from_cache
)
from ocr.utils import (
    get_filename,
    try_parse_json_str,
    get_extension,
    get_path_safe_string,
    normalize_detections_text,
)
from ocr.cloud_storage import (upload_to_cloud_storage_from_cache)
from ocr_app.settings import BACKEND_BASE_URL, DEBUG


# Updating admin site 
admin.site.site_title = "Lipikar Administration"
admin.site.site_header = "Lipikar Administration"
admin.site.index_title = "Admin Home"
admin.site.unregister(Group)
admin.site.unregister(TaskResult)
admin.site.unregister(GroupResult)

admin.site.unregister(BlacklistedToken)
admin.site.unregister(OutstandingToken)


class IsAdminFilter(SimpleListFilter):
    title = gettext_lazy('Is Admin')
    parameter_name = 'is_admin'

    def lookups(self, request, model_admin):
        return (
            ('1', gettext_lazy('Yes')),
            ('0', gettext_lazy('No')),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == '1':
            return queryset.filter(is_superuser=True)
        elif value == '0':
            return queryset.filter(is_superuser=False)


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    change_form_template = 'admin/auth/user_change_form.html'
    change_list_template = 'admin/change_list.html'
    add_form_template = 'admin/auth/user_add_form.html'
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['filter_names'] = [
            ["can_login__exact", "Can Login"],
            ["can_compute__exact", "Can Compute"],
            ["is_admin", "Is Admin"],
        ]
        extra_context['filter_values'] = [
            ["1", "True"],
            ["0", "False"],
        ]
        return super().changelist_view(request, extra_context=extra_context)

    def is_admin(self, obj):
        return obj.is_superuser
    is_admin.boolean = True
    is_admin.short_description = "Is Admin"

    def edit_button(self, obj):
        url = reverse('admin:ocr_customuser_change', args=[obj.pk])
        # return format_html('<a href="{}"><i class="fas fa-edit"></i></a>', url)
        return format_html('<a href="{}">Edit</a>', url)
    edit_button.short_description = ""

    def change_password_button(self, obj):
        url = "Hi"
        return format_html('<a href="{}">Change Password</a>', url)
        # return format_html('<a class="button" href="{}">Change Password</a>',
        #                    reverse('admin:auth_user_password_change', args=[obj.id]))
    change_password_button.short_description = 'Change Password'

    fieldsets = (
        (('Info'), {'fields': ('full_name','organization','username','email','phone_number',)}),
        # (('Authentication'), {'fields': ('change_password_button', )}),
        (('Change Permissions'), {'fields': ('can_login', 'can_compute')}),
        (('Compute Limits'), {'fields': ('credits', 'credits_refresh_policy')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'full_name', 'username', 'password1', 'password2', 'phone_number', 'organization', 'can_login', 'can_compute'),
            },
        ),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return ('full_name', 'email', 'username','organization','phone_number',)
        else:
            return ()
    
    list_display = ('email', 'username', 'full_name', 'can_login', 'can_compute', 'is_admin', 'edit_button', )
    list_filter = (IsAdminFilter, 'can_login', 'can_compute', )

    # @admin.action(description="Give Login Permission to selected users")
    def give_login_permission(self, request, queryset):
        num_users = len(queryset.all())
        queryset.update(can_login=True)

        return self.message_user(
            request,
            ngettext(
                f"Login Permission given to %d user.",
                f"Login Permission given to %d users.",
                num_users,
            )
            % num_users,
            messages.SUCCESS,
        )

    # @admin.action(description="Take Login Permission from selected users")
    def take_login_permission(self, request, queryset):
        num_users = len(queryset.all())
        queryset.update(can_login=False)
        queryset.update(can_compute=False)

        return self.message_user(
            request,
            ngettext(
                f"Login Permission taken from %d user.",
                f"Login Permission taken from %d users.",
                num_users,
            )
            % num_users,
            messages.SUCCESS,
        )

    # @admin.action(description="Give Compute Permission to selected users")
    def give_compute_permission(self, request, queryset):
        num_users = len(queryset.all())
        queryset.update(can_login=True)
        queryset.update(can_compute=True)

        return self.message_user(
            request,
            ngettext(
                f"Compute Permission given to %d user.",
                f"Compute Permission given to %d users.",
                num_users,
            )
            % num_users,
            messages.SUCCESS,
        )

    # @admin.action(description="Take Compute Permission from selected users")
    def take_compute_permission(self, request, queryset):
        num_users = len(queryset.all())
        queryset.update(can_compute=False)

        return self.message_user(
            request,
            ngettext(
                f"Compute Permission taken from %d user.",
                f"Compute Permission taken from %d users.",
                num_users,
            )
            % num_users,
            messages.SUCCESS,
        )

    actions = [
        give_login_permission,
        take_login_permission,
        give_compute_permission,
        take_compute_permission,
    ]


class UploadAdmin(admin.ModelAdmin):
    model = Upload
    readonly_fields = ('user', 'created_at', 'filename','detection_ids','processing_status', 'upload_type' ,'is_cancelled')
    list_display = ('user', 'created_at', 'filename')
    list_display_links = None
    
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False # Changing is not allowed even in Debug Mode

    def change_view(self, request, object_id, form_url='', extra_context=None):
        opts = self.model._meta
        url = reverse('admin:{app}_{model}_changelist'.format(
            app=opts.app_label,
            model=opts.model_name,
        ))
        return HttpResponseRedirect(url)

    # @admin.action(description="Download selected uploads and detections")
    def download_selected_uploads_and_detections(self, request, queryset):
        # Zip file structure
            # Upload id + Upload filename (without extension)
                # Images: folder containing all the details
                # uploadDetails.json: json of the upload from the DB
                # detections.json: json of an array of all the detections from the db
        
        folder_name = str(uuid.uuid4()) # Generate a unique name for the folder, that will later be zipped
        folder_path = create_folder_in_cache(folder_name) # Create the folder in the cache

        upload_objects = queryset.all() # Get all the uploads in the queryset
        for upload_object in upload_objects:
            # Set up the directory structure for this upload
            upload_cache_folder_name = f"{upload_object.id} - {get_path_safe_string(get_filename(upload_object.filename))}"
            upload_cache_folder_path = os.path.join(folder_name, upload_cache_folder_name)
            create_folder_in_cache(upload_cache_folder_path)

            upload_cache_images_folder_name = os.path.join(upload_cache_folder_path, "images")
            create_folder_in_cache(upload_cache_images_folder_name)

            upload_cache_upload_details_json_file_path = os.path.join(folder_path, upload_cache_folder_name, "uploadDetails.json")
            upload_cache_detections_json_file_path = os.path.join(folder_path, upload_cache_folder_name, "detections.json")

            # If the selected upload has not been processed successfully, respond with an error.
            upload_processing_status = try_parse_json_str(upload_object.processing_status)
            if not 'statusCode' in upload_processing_status or upload_processing_status['statusCode'] not in [5, 7]:
                return self.message_user(
                    request,
                    "One or more selected uploads has not been processed successfully.",
                    messages.ERROR
                )

            # construct the upload details from the upload object
            upload_details = {
                'user': upload_object.user.id,
                'created_at': str(upload_object.created_at),
                'filename': upload_object.filename,
                'detection_ids': upload_object.detection_ids,
                'processing_status': upload_processing_status,
                'upload_type': upload_object.upload_type,
            }

            # write the upload details to the json file
            upload_details_json = json.dumps(upload_details, indent=4)
            with open(upload_cache_upload_details_json_file_path, "w+") as outfile:
                outfile.write(upload_details_json)

            detection_ids = try_parse_json_str(upload_object.detection_ids, "list") # Get all the detections for the upload
            all_detection_details = [] # To store all the detections for this upload
            for i, detection_id in enumerate(detection_ids):
                try:
                    detection_object = Detection.objects.get(id=detection_id)
                except Exception as e:
                    print(e)
                    continue                

                # copy the image into the images folder
                download_from_cloud_storage_to_cache(
                    os.path.join("detection_images", detection_object.image_filename),
                    os.path.join(upload_cache_images_folder_name, f"Page-{i+1}" + get_extension(detection_object.image_filename))
                )

                # construct the detection details from the detection object and add them to the list
                all_detection_details.append({
                    'user': detection_object.user.id,
                    'upload': detection_object.upload.id,
                    'image_filename': f"Page-{i+1}" + get_extension(detection_object.image_filename),
                    'document_parser': detection_object.document_parser,
                    'parsing_postprocessor': detection_object.parsing_postprocessor,
                    'text_recognizer': detection_object.text_recognizer,
                    'original_detections': try_parse_json_str(detection_object.original_detections, "list"),
                    'detections': try_parse_json_str(detection_object.detections, "list"),
                })
            

            # write the detection details into the json file
            all_detection_details_json = json.dumps(all_detection_details, indent=4, ensure_ascii=False)
            with open(upload_cache_detections_json_file_path, "w+") as outfile:
                outfile.write(all_detection_details_json)
        
        zip_file_path = zip_folder_in_cache(folder_name) # Zip this folder inside the cache
        zip_file_name = os.path.basename(zip_file_path)
        upload_to_cloud_storage_from_cache(zip_file_name, "zipped") # Upload the zip file to cloud storage

        remove_folder_from_cache(folder_name) # Delete the folder from the cache

        zip_file_link = f"{BACKEND_BASE_URL}/media/zipped/{zip_file_name}" # Generate a link to the zip file

        return self.message_user(
            request,
            ngettext(
                f"%d upload and its detections have been zipped. Link: {zip_file_link}",
                f"%d uploads and their detections have been zipped. Link: {zip_file_link}",
                len(upload_objects),
            )
            % len(upload_objects),
            messages.SUCCESS,
        )

    actions = [download_selected_uploads_and_detections]


class DetectionAdmin(admin.ModelAdmin):
    model = Detection
    readonly_fields = ('user', 'upload', 'image_filename','document_parser','parsing_postprocessor', 'text_recognizer', 'original_detections', 'detections')
    list_display = ('user', 'upload','document_parser','parsing_postprocessor', 'text_recognizer')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Upload, UploadAdmin)

# if DEBUG:
#     admin.site.register(Detection, DetectionAdmin)
