from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.accounts.models import RiskQuizResponse, UserProfile

User = get_user_model()


class UserProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_create_profile(self):
        profile = UserProfile.objects.create(user=self.user, province="QC", preferred_language="fr")
        assert profile.province == "QC"
        assert profile.preferred_language == "fr"
        assert profile.onboarding_completed is False
        assert profile.risk_profile_score is None

    def test_str(self):
        profile = UserProfile.objects.create(user=self.user)
        assert str(profile) == "Profile of test@example.com"

    def test_risk_profile_label_none(self):
        profile = UserProfile.objects.create(user=self.user)
        assert profile.risk_profile_label == ""

    @override_settings(LANGUAGE_CODE="en")
    def test_risk_profile_label_conservative(self):
        profile = UserProfile.objects.create(user=self.user, risk_profile_score=2)
        assert str(profile.risk_profile_label) == "Conservative"

    @override_settings(LANGUAGE_CODE="en")
    def test_risk_profile_label_moderate(self):
        profile = UserProfile.objects.create(user=self.user, risk_profile_score=5)
        assert str(profile.risk_profile_label) == "Moderate"

    @override_settings(LANGUAGE_CODE="en")
    def test_risk_profile_label_growth(self):
        profile = UserProfile.objects.create(user=self.user, risk_profile_score=8)
        assert str(profile.risk_profile_label) == "Growth"


class RiskQuizResponseTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_create_response(self):
        response = RiskQuizResponse.objects.create(user=self.user, question_key="risk_comfort", answer_value=3)
        assert response.question_key == "risk_comfort"
        assert response.answer_value == 3

    def test_unique_together(self):
        RiskQuizResponse.objects.create(user=self.user, question_key="risk_comfort", answer_value=3)
        RiskQuizResponse.objects.update_or_create(
            user=self.user,
            question_key="risk_comfort",
            defaults={"answer_value": 4},
        )
        assert RiskQuizResponse.objects.filter(user=self.user, question_key="risk_comfort").count() == 1
        assert RiskQuizResponse.objects.get(user=self.user, question_key="risk_comfort").answer_value == 4

    def test_str(self):
        response = RiskQuizResponse.objects.create(user=self.user, question_key="risk_comfort", answer_value=3)
        assert str(response) == "test@example.com — risk_comfort: 3"
