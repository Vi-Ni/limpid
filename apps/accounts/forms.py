from django import forms

from .models import UserProfile

TAILWIND_SELECT_CLASS = "input"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["province", "preferred_language"]
        widgets = {
            "province": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "preferred_language": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
        }


class OnboardingStep1Form(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["province"]
        widgets = {
            "province": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
        }


class OnboardingStep2Form(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["preferred_language"]
        widgets = {
            "preferred_language": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
        }
