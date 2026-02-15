from django import forms

from .models import UserProfile

TAILWIND_SELECT_CLASS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
    " shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["province", "preferred_language"]
        widgets = {
            "province": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "preferred_language": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
        }
