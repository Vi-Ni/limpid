from django import forms

from .models import UserProfile

TAILWIND_SELECT_CLASS = (
    "w-full rounded-lg border border-border px-3 py-2 text-sm"
    " shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
)


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
