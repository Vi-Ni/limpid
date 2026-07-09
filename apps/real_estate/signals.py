from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils.translation import gettext as _


@receiver(user_logged_in)
def create_notifications_for_pending_invitations(sender, request, user, **kwargs):
    from .models import PropertyInvitation, PropertyNotification

    pending = PropertyInvitation.objects.filter(email=user.email, accepted=False).select_related(
        "property", "invited_by"
    )

    for invitation in pending:
        already_notified = PropertyNotification.objects.filter(
            recipient=user,
            invitation=invitation,
            verb="invitation_received",
        ).exists()
        if not already_notified:
            PropertyNotification.objects.create(
                recipient=user,
                property=invitation.property,
                actor=invitation.invited_by,
                verb="invitation_received",
                description=_("invited you to co-own %(name)s (%(share)s%%)")
                % {
                    "name": invitation.property.name,
                    "share": invitation.share_pct,
                },
                invitation=invitation,
            )
