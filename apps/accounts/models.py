from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    PROVINCE_CHOICES = [
        ("AB", _("Alberta")),
        ("BC", _("British Columbia")),
        ("MB", _("Manitoba")),
        ("NB", _("New Brunswick")),
        ("NL", _("Newfoundland and Labrador")),
        ("NS", _("Nova Scotia")),
        ("NT", _("Northwest Territories")),
        ("NU", _("Nunavut")),
        ("ON", _("Ontario")),
        ("PE", _("Prince Edward Island")),
        ("QC", _("Quebec")),
        ("SK", _("Saskatchewan")),
        ("YT", _("Yukon")),
    ]

    LANGUAGE_CHOICES = [
        ("fr", _("French")),
        ("en", _("English")),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    province = models.CharField(
        max_length=2,
        choices=PROVINCE_CHOICES,
        blank=True,
        default="",
    )
    preferred_language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="fr",
    )
    risk_profile_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=_("Risk score from 1 (conservative) to 10 (aggressive)."),
    )
    onboarding_completed = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self):
        return f"Profile of {self.user.email}"

    @property
    def risk_profile_label(self):
        if self.risk_profile_score is None:
            return ""
        if self.risk_profile_score <= 3:
            return _("Conservative")
        if self.risk_profile_score <= 6:
            return _("Moderate")
        return _("Growth")


class RiskQuizResponse(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_quiz_responses",
    )
    question_key = models.CharField(max_length=50)
    answer_value = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = _("risk quiz response")
        verbose_name_plural = _("risk quiz responses")
        unique_together = [("user", "question_key")]

    def __str__(self):
        return f"{self.user.email} — {self.question_key}: {self.answer_value}"
