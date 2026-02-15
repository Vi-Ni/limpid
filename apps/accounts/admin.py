from django.contrib import admin

from .models import RiskQuizResponse, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "province", "preferred_language", "risk_profile_score", "onboarding_completed")
    list_filter = ("province", "preferred_language", "onboarding_completed")
    search_fields = ("user__email",)


@admin.register(RiskQuizResponse)
class RiskQuizResponseAdmin(admin.ModelAdmin):
    list_display = ("user", "question_key", "answer_value")
    list_filter = ("question_key",)
    search_fields = ("user__email",)
