# Notification System & CRUD Operations Plan

## Overview

Two interconnected features:
1. **In-app notification system** between co-owners of a property
2. **Full CRUD** (edit/delete) for Property Taxes, Expenses & Renovations, Valuation History, and co-owner removal

Notifications are triggered by CRUD actions on shared properties, keeping all co-owners informed of changes.

---

## Part A: Notification System

### A1. Model

**File:** `apps/real_estate/models.py`

```python
class PropertyNotification(models.Model):
    VERB_CHOICES = [
        ("invitation_sent", _("Invitation sent")),
        ("invitation_accepted", _("Invitation accepted")),
        ("co_owner_removed", _("Co-owner removed")),
        ("expense_added", _("Expense added")),
        ("expense_updated", _("Expense updated")),
        ("expense_deleted", _("Expense deleted")),
        ("tax_added", _("Tax added")),
        ("tax_updated", _("Tax updated")),
        ("tax_deleted", _("Tax deleted")),
        ("valuation_added", _("Valuation added")),
        ("valuation_updated", _("Valuation updated")),
        ("valuation_deleted", _("Valuation deleted")),
        ("property_updated", _("Property updated")),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_notifications",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    verb = models.CharField(_("action"), max_length=30, choices=VERB_CHOICES)
    description = models.CharField(_("description"), max_length=300)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.actor} → {self.recipient}: {self.verb}"
```

**Why this design:**
- `recipient` + `actor` pattern: "Vincent added an expense on Condo A" — actor=Vincent, recipients=all other co-owners
- `verb` as a choice field: allows filtering/grouping, easier i18n than free text
- `description` as human-readable summary (pre-rendered at creation time, avoids FK to deleted objects)
- `property` FK: notification stays tied to the property, allows "all notifications for this property" queries
- Index on `(recipient, is_read, -created_at)`: fast "unread count" and "notification list" queries

### A2. Notification Helper Service

**File:** `apps/real_estate/services.py` — add at bottom

```python
def notify_co_owners(prop, actor, verb, description):
    """Create a notification for all co-owners of a property except the actor."""
    co_owners = prop.ownerships.exclude(user=actor).select_related("user")
    notifications = [
        PropertyNotification(
            recipient=ownership.user,
            property=prop,
            actor=actor,
            verb=verb,
            description=description,
        )
        for ownership in co_owners
    ]
    PropertyNotification.objects.bulk_create(notifications)
```

This keeps notification creation out of views — one-liner calls from any view or future management command.

### A3. Context Processor for Unread Count

**File:** `config/context_processors.py` — add function

```python
def unread_notifications(request):
    if request.user.is_authenticated:
        from apps.real_estate.models import PropertyNotification

        count = PropertyNotification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return {"unread_notification_count": count}
    return {"unread_notification_count": 0}
```

**File:** `config/settings/base.py` — add to TEMPLATES context_processors list:

```python
"config.context_processors.unread_notifications",
```

### A4. Bell Icon in Navigation

**File:** `templates/components/nav.html` — add between nav links and language switcher

The bell goes in the sidebar (desktop) and bottom nav (mobile), showing the unread count badge.

**Desktop sidebar** — add after the last `<a>` in the `<nav>` block (after Impact link, before `</nav>`):

```html
{% if user.is_authenticated %}
<a href="{% url 'real_estate:notifications' %}"
   class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium
   {% if nav_current == 'notifications' %}bg-primary-50 text-primary-700
   {% else %}text-text-muted hover:bg-gray-100 hover:text-text{% endif %}">
  <span class="relative">
    <svg class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
    </svg>
    {% if unread_notification_count %}
    <span class="absolute -right-1.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger-500 text-[10px] font-bold text-white">
      {{ unread_notification_count }}
    </span>
    {% endif %}
  </span>
  {% trans "Notifications" %}
</a>
{% endif %}
```

**Mobile bottom nav** (`templates/components/bottom_nav.html`) — replace the Profile link with a notification bell (move Profile to sidebar only), or add a 6th item. Simpler approach: replace the Profile icon on mobile with a bell+badge that links to notifications:

```html
<a href="{% url 'real_estate:notifications' %}"
   class="flex flex-col items-center gap-1 px-2 py-1 text-xs font-medium
   {% if nav_current == 'notifications' %}text-primary-600{% else %}text-text-muted{% endif %}">
  <span class="relative">
    <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
    </svg>
    {% if unread_notification_count %}
    <span class="absolute -right-1 -top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-danger-500 text-[9px] font-bold text-white">
      {{ unread_notification_count }}
    </span>
    {% endif %}
  </span>
  {% trans "Alerts" %}
</a>
```

### A5. Notification List View

**File:** `apps/real_estate/views.py`

```python
@login_required
def notification_list(request):
    notifications = PropertyNotification.objects.filter(
        recipient=request.user
    ).select_related("property", "actor")[:50]
    return render(request, "real_estate/notifications.html", {
        "notifications": notifications,
    })


@login_required
def mark_notifications_read(request):
    PropertyNotification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return render(request, "real_estate/partials/notification_badge.html")
```

### A6. Notification List Template

**File:** `templates/real_estate/notifications.html`

```html
{% extends "base.html" %}
{% load i18n timesincefilter %}

{% block content %}
<div class="container-limpid py-6 space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold text-text">{% trans "Notifications" %}</h1>
    {% if notifications %}
    <button hx-post="{% url 'real_estate:mark_all_read' %}"
            hx-target="#notification-badge"
            hx-swap="outerHTML"
            class="text-sm text-primary-600 hover:text-primary-700">
      {% trans "Mark all as read" %}
    </button>
    {% endif %}
  </div>

  {% if notifications %}
  <div class="space-y-2">
    {% for notif in notifications %}
    <a href="{% url 'real_estate:detail' notif.property.pk %}"
       class="block rounded-lg border border-border p-4 transition hover:bg-gray-50
       {% if not notif.is_read %}bg-primary-50/50 border-primary-200{% else %}bg-bg-card{% endif %}">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-sm text-text">
            <span class="font-semibold">{{ notif.actor.get_full_name|default:notif.actor.email }}</span>
            {{ notif.description }}
          </p>
          <p class="mt-1 text-xs text-text-muted">
            {{ notif.property.name }} &middot; {{ notif.created_at|timesince }} {% trans "ago" %}
          </p>
        </div>
        {% if not notif.is_read %}
        <span class="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary-500"></span>
        {% endif %}
      </div>
    </a>
    {% endfor %}
  </div>
  {% else %}
  <div class="rounded-lg border border-border bg-bg-card p-8 text-center">
    <p class="text-text-muted">{% trans "No notifications yet." %}</p>
  </div>
  {% endif %}
</div>
{% endblock %}
```

### A7. Notification Badge Partial (for HTMX OOB updates)

**File:** `templates/real_estate/partials/notification_badge.html`

```html
<span id="notification-badge">
  {% if unread_notification_count %}
  <span class="absolute -right-1.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger-500 text-[10px] font-bold text-white">
    {{ unread_notification_count }}
  </span>
  {% endif %}
</span>
```

### A8. URLs

**File:** `apps/real_estate/urls.py` — add:

```python
path("notifications/", views.notification_list, name="notifications"),
path("notifications/mark-read/", views.mark_notifications_read, name="mark_all_read"),
```

---

## Part B: CRUD Operations (Edit/Delete)

### B1. Edit & Delete Expense

#### B1.1 URLs

```python
path("<int:pk>/expense/<int:expense_id>/edit/", views.edit_expense, name="edit_expense"),
path("<int:pk>/expense/<int:expense_id>/delete/", views.delete_expense, name="delete_expense"),
```

#### B1.2 Views

**File:** `apps/real_estate/views.py`

```python
@login_required
def edit_expense(request, pk, expense_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    expense = get_object_or_404(PropertyExpense, pk=expense_id, property=prop)
    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            notify_co_owners(
                prop, request.user, "expense_updated",
                _("updated expense \"%(desc)s\" (%(amount)s)")
                % {"desc": expense.description, "amount": expense.amount},
            )
            expenses = prop.expenses.all()[:20]
            return render(request, "real_estate/partials/expense_list.html", {
                "expenses": expenses, "property": prop,
            })
    else:
        form = ExpenseForm(instance=expense)
    return render(request, "real_estate/partials/expense_form.html", {
        "form": form, "property": prop, "editing": True, "expense": expense,
    })


@login_required
def delete_expense(request, pk, expense_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    expense = get_object_or_404(PropertyExpense, pk=expense_id, property=prop)
    if request.method == "DELETE":
        description = _("deleted expense \"%(desc)s\" (%(amount)s)") % {
            "desc": expense.description, "amount": expense.amount,
        }
        expense.delete()
        notify_co_owners(prop, request.user, "expense_deleted", description)
        expenses = prop.expenses.all()[:20]
        return render(request, "real_estate/partials/expense_list.html", {
            "expenses": expenses, "property": prop,
        })
    return HttpResponseNotAllowed(["DELETE"])
```

#### B1.3 Template Updates

**File:** `templates/real_estate/partials/expense_list.html` — add edit/delete buttons per row:

```html
{% load i18n real_estate_filters %}

{% if expenses %}
<div class="overflow-x-auto">
  <table class="min-w-full text-sm">
    <thead>
      <tr class="border-b border-border">
        <th class="px-3 py-2 text-left text-text-muted">{% trans "Date" %}</th>
        <th class="px-3 py-2 text-left text-text-muted">{% trans "Type" %}</th>
        <th class="px-3 py-2 text-left text-text-muted">{% trans "Description" %}</th>
        <th class="px-3 py-2 text-right text-text-muted">{% trans "Amount" %}</th>
        <th class="px-3 py-2 text-right text-text-muted"></th>
      </tr>
    </thead>
    <tbody>
      {% for expense in expenses %}
      <tr class="border-b border-gray-100 group">
        <td class="px-3 py-2 text-text-muted">{{ expense.date }}</td>
        <td class="px-3 py-2">
          {% include "components/badge.html" with label=expense.get_expense_type_display variant="neutral" %}
        </td>
        <td class="px-3 py-2 text-text">{{ expense.description }}</td>
        <td class="px-3 py-2 text-right text-text">{{ expense.amount|cad }}</td>
        <td class="px-3 py-2 text-right">
          <span class="opacity-0 group-hover:opacity-100 transition-opacity flex gap-2 justify-end">
            <button hx-get="{% url 'real_estate:edit_expense' property.pk expense.pk %}"
                    hx-target="#expense-form-container"
                    hx-swap="innerHTML"
                    class="text-xs text-primary-600 hover:text-primary-700">
              {% trans "Edit" %}
            </button>
            <button hx-delete="{% url 'real_estate:delete_expense' property.pk expense.pk %}"
                    hx-target="#expense-list"
                    hx-swap="innerHTML"
                    hx-confirm="{% trans 'Delete this expense?' %}"
                    class="text-xs text-danger-600 hover:text-danger-700">
              {% trans "Delete" %}
            </button>
          </span>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% else %}
<p class="text-sm text-text-muted py-2">{% trans "No expenses recorded." %}</p>
{% endif %}
```

**File:** `templates/real_estate/partials/expense_form.html` — update to handle edit mode:

```html
{% load i18n %}

<form hx-post="{% if editing %}{% url 'real_estate:edit_expense' property.pk expense.pk %}{% else %}{% url 'real_estate:add_expense' property.pk %}{% endif %}"
      hx-target="#expense-list"
      hx-swap="innerHTML"
      class="mt-4 space-y-3 rounded-lg border border-border p-4">
  {% csrf_token %}
  <div class="grid gap-3 sm:grid-cols-2">
    {% for field in form %}
    <div{% if field.name == "description" %} class="sm:col-span-2"{% endif %}>
      <label class="block text-sm text-text-muted mb-1">{{ field.label }}</label>
      {{ field }}
      {% if field.errors %}<p class="text-xs text-danger-600 mt-1">{{ field.errors.0 }}</p>{% endif %}
    </div>
    {% endfor %}
  </div>
  {% if form.non_field_errors %}
  <p class="text-sm text-danger-600">{{ form.non_field_errors.0 }}</p>
  {% endif %}
  <div class="flex gap-2">
    <button type="submit" class="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
      {% if editing %}{% trans "Save" %}{% else %}{% trans "Add" %}{% endif %}
    </button>
    <button type="button"
            hx-get="{% url 'real_estate:add_expense' property.pk %}"
            hx-target="#expense-form-container"
            hx-swap="innerHTML"
            class="rounded-lg border border-border px-4 py-2 text-sm text-text-muted hover:bg-gray-50">
      {% trans "Cancel" %}
    </button>
  </div>
</form>
```

### B2. Edit & Delete Tax

Same pattern as expenses. Mirror the approach exactly.

#### B2.1 URLs

```python
path("<int:pk>/tax/<int:tax_id>/edit/", views.edit_tax, name="edit_tax"),
path("<int:pk>/tax/<int:tax_id>/delete/", views.delete_tax, name="delete_tax"),
```

#### B2.2 Views

```python
@login_required
def edit_tax(request, pk, tax_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    tax = get_object_or_404(PropertyTax, pk=tax_id, property=prop)
    if request.method == "POST":
        form = PropertyTaxForm(request.POST, instance=tax)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.property = prop
            # Check uniqueness excluding current record
            if PropertyTax.objects.filter(
                property=prop, tax_type=updated.tax_type, year=updated.year
            ).exclude(pk=tax.pk).exists():
                form.add_error(None, _("A tax entry for this type and year already exists."))
                return render(request, "real_estate/partials/tax_form.html", {
                    "form": form, "property": prop, "editing": True, "tax": tax,
                })
            updated.save()
            notify_co_owners(
                prop, request.user, "tax_updated",
                _("updated %(type)s tax for %(year)s")
                % {"type": tax.get_tax_type_display(), "year": tax.year},
            )
            taxes = prop.taxes.all()
            return render(request, "real_estate/partials/tax_list.html", {
                "taxes": taxes, "property": prop,
            })
    else:
        form = PropertyTaxForm(instance=tax)
    return render(request, "real_estate/partials/tax_form.html", {
        "form": form, "property": prop, "editing": True, "tax": tax,
    })


@login_required
def delete_tax(request, pk, tax_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    tax = get_object_or_404(PropertyTax, pk=tax_id, property=prop)
    if request.method == "DELETE":
        description = _("deleted %(type)s tax for %(year)s (%(amount)s)") % {
            "type": tax.get_tax_type_display(), "year": tax.year, "amount": tax.amount,
        }
        tax.delete()
        notify_co_owners(prop, request.user, "tax_deleted", description)
        taxes = prop.taxes.all()
        return render(request, "real_estate/partials/tax_list.html", {
            "taxes": taxes, "property": prop,
        })
    return HttpResponseNotAllowed(["DELETE"])
```

#### B2.3 Templates

**File:** `templates/real_estate/partials/tax_list.html` — same pattern, add edit/delete actions:

```html
{% load i18n real_estate_filters %}

{% if taxes %}
<div class="overflow-x-auto">
  <table class="min-w-full text-sm">
    <thead>
      <tr class="border-b border-border">
        <th class="px-3 py-2 text-left text-text-muted">{% trans "Year" %}</th>
        <th class="px-3 py-2 text-left text-text-muted">{% trans "Type" %}</th>
        <th class="px-3 py-2 text-right text-text-muted">{% trans "Amount" %}</th>
        <th class="px-3 py-2 text-right text-text-muted"></th>
      </tr>
    </thead>
    <tbody>
      {% for tax in taxes %}
      <tr class="border-b border-gray-100 group">
        <td class="px-3 py-2 text-text-muted">{{ tax.year }}</td>
        <td class="px-3 py-2">
          {% include "components/badge.html" with label=tax.get_tax_type_display variant="neutral" %}
        </td>
        <td class="px-3 py-2 text-right text-text">{{ tax.amount|cad }}</td>
        <td class="px-3 py-2 text-right">
          <span class="opacity-0 group-hover:opacity-100 transition-opacity flex gap-2 justify-end">
            <button hx-get="{% url 'real_estate:edit_tax' property.pk tax.pk %}"
                    hx-target="#tax-form-container"
                    hx-swap="innerHTML"
                    class="text-xs text-primary-600 hover:text-primary-700">
              {% trans "Edit" %}
            </button>
            <button hx-delete="{% url 'real_estate:delete_tax' property.pk tax.pk %}"
                    hx-target="#tax-list"
                    hx-swap="innerHTML"
                    hx-confirm="{% trans 'Delete this tax entry?' %}"
                    class="text-xs text-danger-600 hover:text-danger-700">
              {% trans "Delete" %}
            </button>
          </span>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% else %}
<p class="text-sm text-text-muted py-2">{% trans "No taxes recorded." %}</p>
{% endif %}
```

### B3. Edit & Delete Valuation

#### B3.1 URLs

```python
path("<int:pk>/valuation/<int:valuation_id>/edit/", views.edit_valuation, name="edit_valuation"),
path("<int:pk>/valuation/<int:valuation_id>/delete/", views.delete_valuation, name="delete_valuation"),
```

#### B3.2 Views

```python
@login_required
def edit_valuation(request, pk, valuation_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    valuation = get_object_or_404(PropertyValuation, pk=valuation_id, property=prop)
    if request.method == "POST":
        form = ValuationForm(request.POST, instance=valuation)
        if form.is_valid():
            valuation = form.save()
            # If this is the most recent valuation, update property's current value
            latest = prop.valuations.first()  # ordered by -date
            if latest and latest.pk == valuation.pk:
                prop.current_valuation = valuation.value
                prop.valuation_date = valuation.date
                prop.save(update_fields=["current_valuation", "valuation_date"])
            notify_co_owners(
                prop, request.user, "valuation_updated",
                _("updated valuation to %(value)s on %(date)s")
                % {"value": valuation.value, "date": valuation.date},
            )
            valuations = prop.valuations.all()[:10]
            return render(request, "real_estate/partials/valuation_history.html", {
                "valuations": valuations, "oob_update": True, "property": prop,
            })
    else:
        form = ValuationForm(instance=valuation)
    return render(request, "real_estate/partials/valuation_form.html", {
        "form": form, "property": prop, "editing": True, "valuation": valuation,
    })


@login_required
def delete_valuation(request, pk, valuation_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    valuation = get_object_or_404(PropertyValuation, pk=valuation_id, property=prop)
    if request.method == "DELETE":
        description = _("deleted valuation of %(value)s on %(date)s") % {
            "value": valuation.value, "date": valuation.date,
        }
        valuation.delete()
        # Update property's current valuation to the new latest
        latest = prop.valuations.first()
        if latest:
            prop.current_valuation = latest.value
            prop.valuation_date = latest.date
        else:
            prop.current_valuation = prop.purchase_price
            prop.valuation_date = prop.purchase_date
        prop.save(update_fields=["current_valuation", "valuation_date"])
        notify_co_owners(prop, request.user, "valuation_deleted", description)
        valuations = prop.valuations.all()[:10]
        return render(request, "real_estate/partials/valuation_history.html", {
            "valuations": valuations, "oob_update": True, "property": prop,
        })
    return HttpResponseNotAllowed(["DELETE"])
```

#### B3.3 Template

**File:** `templates/real_estate/partials/valuation_history.html` — add edit/delete:

```html
{% load i18n real_estate_filters %}

{% if valuations %}
<div class="space-y-2">
  {% for val in valuations %}
  <div class="flex items-center justify-between py-1 group">
    <div>
      <span class="text-sm text-text">{{ val.date }}</span>
      {% include "components/badge.html" with label=val.get_source_display variant="neutral" %}
    </div>
    <div class="flex items-center gap-3">
      <span class="text-sm font-semibold text-text">{{ val.value|cad }}</span>
      <span class="opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
        <button hx-get="{% url 'real_estate:edit_valuation' property.pk val.pk %}"
                hx-target="#valuation-form-container"
                hx-swap="innerHTML"
                class="text-xs text-primary-600 hover:text-primary-700">
          {% trans "Edit" %}
        </button>
        <button hx-delete="{% url 'real_estate:delete_valuation' property.pk val.pk %}"
                hx-target="#valuation-list"
                hx-swap="innerHTML"
                hx-confirm="{% trans 'Delete this valuation?' %}"
                class="text-xs text-danger-600 hover:text-danger-700">
          {% trans "Delete" %}
        </button>
      </span>
    </div>
  </div>
  {% endfor %}
</div>
{% else %}
<p class="text-sm text-text-muted py-2">{% trans "No valuation history." %}</p>
{% endif %}

{% if oob_update %}
<span id="property-value-display" hx-swap-oob="innerHTML">{{ property.current_valuation|cad }}</span>
{% endif %}
```

### B4. Remove Co-owner

Admin-only action. Removes an owner and updates ownership period shares.

#### B4.1 URL

```python
path("<int:pk>/remove-owner/<int:ownership_id>/", views.remove_co_owner, name="remove_co_owner"),
```

#### B4.2 View

```python
@login_required
def remove_co_owner(request, pk, ownership_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    admin_ownership = get_object_or_404(
        PropertyOwnership, property=prop, user=request.user, is_admin=True
    )
    target_ownership = get_object_or_404(PropertyOwnership, pk=ownership_id, property=prop)

    # Cannot remove yourself
    if target_ownership.user == request.user:
        messages.error(request, _("You cannot remove yourself."))
        return redirect("real_estate:detail", pk=prop.pk)

    if request.method == "POST":
        removed_user = target_ownership.user
        removed_email = removed_user.email
        removed_name = removed_user.get_full_name() or removed_email

        # Close current ownership period and create new one with 100% for admin
        current_period = prop.ownership_periods.filter(
            end_date__isnull=True
        ).order_by("-start_date").first()
        today = date.today()

        if current_period:
            current_period.end_date = today
            current_period.save(update_fields=["end_date"])

        new_period = OwnershipPeriod.objects.create(
            property=prop,
            start_date=today,
            note=_("%(name)s removed") % {"name": removed_name},
        )

        # Remove the ownership (this cascades OwnershipPeriodShare entries)
        target_ownership.delete()

        # Redistribute shares equally among remaining owners
        remaining = prop.ownerships.all()
        if remaining.count() == 1:
            OwnershipPeriodShare.objects.create(
                period=new_period, owner=remaining.first(), share_pct=Decimal("100")
            )
        else:
            share = (Decimal("100") / remaining.count()).quantize(Decimal("0.01"))
            for own in remaining:
                OwnershipPeriodShare.objects.create(
                    period=new_period, owner=own, share_pct=share
                )

        # Notify the removed user
        PropertyNotification.objects.create(
            recipient=removed_user,
            property=prop,
            actor=request.user,
            verb="co_owner_removed",
            description=_("removed you from %(name)s") % {"name": prop.name},
        )

        # Notify remaining co-owners
        notify_co_owners(
            prop, request.user, "co_owner_removed",
            _("removed %(name)s from this property") % {"name": removed_name},
        )

        messages.success(
            request,
            _("%(name)s has been removed from %(property)s.")
            % {"name": removed_name, "property": prop.name},
        )
        return redirect("real_estate:detail", pk=prop.pk)

    return render(request, "real_estate/confirm_remove_owner.html", {
        "property": prop,
        "target_ownership": target_ownership,
    })
```

#### B4.3 Confirmation Template

**File:** `templates/real_estate/confirm_remove_owner.html`

```html
{% extends "base.html" %}
{% load i18n %}

{% block content %}
<div class="container-limpid py-6">
  <div class="mx-auto max-w-md">
    {% include "components/card_start.html" with title=_("Remove Co-owner") variant="warning" %}
      <p class="text-sm text-text mb-4">
        {% blocktrans with name=target_ownership.user.get_full_name|default:target_ownership.user.email property=property.name %}
        Are you sure you want to remove <strong>{{ name }}</strong> from <strong>{{ property }}</strong>?
        {% endblocktrans %}
      </p>
      <p class="text-sm text-text-muted mb-6">
        {% trans "Their ownership share will be redistributed among remaining owners. This action cannot be undone." %}
      </p>
      <form method="post">
        {% csrf_token %}
        <div class="flex gap-3">
          <button type="submit"
                  class="rounded-lg bg-danger-600 px-4 py-2 text-sm font-medium text-white hover:bg-danger-700">
            {% trans "Remove" %}
          </button>
          <a href="{% url 'real_estate:detail' property.pk %}"
             class="rounded-lg border border-border px-4 py-2 text-sm text-text-muted hover:bg-gray-50">
            {% trans "Cancel" %}
          </a>
        </div>
      </form>
    {% include "components/card_end.html" %}
  </div>
</div>
{% endblock %}
```

#### B4.4 Detail Page — Remove Button

In `templates/real_estate/detail.html`, update the Ownership card to show a remove button for each co-owner (admin only):

```html
{% for own, share in shares.items %}
<div class="flex items-center justify-between">
  <span class="text-text">{{ own.user.get_full_name|default:own.user.email }}</span>
  <div class="flex items-center gap-2">
    <span class="font-semibold text-primary-600">{{ share|floatformat:0 }}%</span>
    {% if ownership.is_admin and own.user != request.user %}
    <a href="{% url 'real_estate:remove_co_owner' property.pk own.pk %}"
       class="text-xs text-danger-500 hover:text-danger-700 opacity-0 group-hover:opacity-100 transition-opacity">
      {% trans "Remove" %}
    </a>
    {% endif %}
  </div>
</div>
{% endfor %}
```

Add `group` class to the parent div to enable hover reveal.

---

## Part C: Notification Triggers

Wire notification creation into existing and new views. Here are all the trigger points:

### C1. Existing views to update

| View | Verb | Description template |
|------|------|---------------------|
| `add_expense` (POST success) | `expense_added` | `added expense "%(desc)s" (%(amount)s)` |
| `add_tax` (POST success) | `tax_added` | `added %(type)s tax for %(year)s (%(amount)s)` |
| `add_valuation` (POST success) | `valuation_added` | `added valuation of %(value)s` |
| `invite_co_owner` (POST success) | `invitation_sent` | `invited %(email)s as co-owner` |
| `accept_invitation` (after save) | `invitation_accepted` | `accepted co-ownership invitation` |
| `property_edit` (POST success) | `property_updated` | `updated property details` |

### C2. Example: Wiring into `add_expense`

Current code:

```python
expense.save()
expenses = prop.expenses.all()[:20]
return render(request, "real_estate/partials/expense_list.html", {"expenses": expenses})
```

Updated:

```python
expense.save()
notify_co_owners(
    prop, request.user, "expense_added",
    _("added expense \"%(desc)s\" (%(amount)s)")
    % {"desc": expense.description, "amount": expense.amount},
)
expenses = prop.expenses.all()[:20]
return render(request, "real_estate/partials/expense_list.html", {
    "expenses": expenses, "property": prop,
})
```

Same one-liner pattern for all other views — just call `notify_co_owners()` after the successful save/delete.

---

## Part D: Complete URL Summary

All new URLs to add to `apps/real_estate/urls.py`:

```python
# Notifications
path("notifications/", views.notification_list, name="notifications"),
path("notifications/mark-read/", views.mark_notifications_read, name="mark_all_read"),

# Expense CRUD
path("<int:pk>/expense/<int:expense_id>/edit/", views.edit_expense, name="edit_expense"),
path("<int:pk>/expense/<int:expense_id>/delete/", views.delete_expense, name="delete_expense"),

# Tax CRUD
path("<int:pk>/tax/<int:tax_id>/edit/", views.edit_tax, name="edit_tax"),
path("<int:pk>/tax/<int:tax_id>/delete/", views.delete_tax, name="delete_tax"),

# Valuation CRUD
path("<int:pk>/valuation/<int:valuation_id>/edit/", views.edit_valuation, name="edit_valuation"),
path("<int:pk>/valuation/<int:valuation_id>/delete/", views.delete_valuation, name="delete_valuation"),

# Co-owner removal
path("<int:pk>/remove-owner/<int:ownership_id>/", views.remove_co_owner, name="remove_co_owner"),
```

---

## Part E: Migration

One migration for the new `PropertyNotification` model:

```bash
uv run python manage.py makemigrations real_estate
uv run python manage.py migrate
```

---

## Part F: FR Translations

New strings to add to `locale/fr/LC_MESSAGES/django.po`:

```po
msgid "Notifications"
msgstr "Notifications"

msgid "Alerts"
msgstr "Alertes"

msgid "Mark all as read"
msgstr "Tout marquer comme lu"

msgid "No notifications yet."
msgstr "Aucune notification."

msgid "ago"
msgstr ""

msgid "Edit"
msgstr "Modifier"

msgid "Delete"
msgstr "Supprimer"

msgid "Save"
msgstr "Enregistrer"

msgid "Add"
msgstr "Ajouter"

msgid "Cancel"
msgstr "Annuler"

msgid "Delete this expense?"
msgstr "Supprimer cette depense ?"

msgid "Delete this tax entry?"
msgstr "Supprimer cette taxe ?"

msgid "Delete this valuation?"
msgstr "Supprimer cette evaluation ?"

msgid "Remove Co-owner"
msgstr "Retirer le coproprietaire"

msgid "Remove"
msgstr "Retirer"

msgid "You cannot remove yourself."
msgstr "Vous ne pouvez pas vous retirer vous-meme."

msgid "Their ownership share will be redistributed among remaining owners. This action cannot be undone."
msgstr "Sa part de propriete sera redistribuee entre les proprietaires restants. Cette action est irreversible."

msgid "Invitation sent"
msgstr "Invitation envoyee"

msgid "Invitation accepted"
msgstr "Invitation acceptee"

msgid "Co-owner removed"
msgstr "Coproprietaire retire"

msgid "Expense added"
msgstr "Depense ajoutee"

msgid "Expense updated"
msgstr "Depense modifiee"

msgid "Expense deleted"
msgstr "Depense supprimee"

msgid "Tax added"
msgstr "Taxe ajoutee"

msgid "Tax updated"
msgstr "Taxe modifiee"

msgid "Tax deleted"
msgstr "Taxe supprimee"

msgid "Valuation added"
msgstr "Evaluation ajoutee"

msgid "Valuation updated"
msgstr "Evaluation modifiee"

msgid "Valuation deleted"
msgstr "Evaluation supprimee"

msgid "Property updated"
msgstr "Propriete mise a jour"

msgid "added expense \"%(desc)s\" (%(amount)s)"
msgstr "a ajoute la depense \"%(desc)s\" (%(amount)s)"

msgid "updated expense \"%(desc)s\" (%(amount)s)"
msgstr "a modifie la depense \"%(desc)s\" (%(amount)s)"

msgid "deleted expense \"%(desc)s\" (%(amount)s)"
msgstr "a supprime la depense \"%(desc)s\" (%(amount)s)"

msgid "added %(type)s tax for %(year)s (%(amount)s)"
msgstr "a ajoute la taxe %(type)s pour %(year)s (%(amount)s)"

msgid "updated %(type)s tax for %(year)s"
msgstr "a modifie la taxe %(type)s pour %(year)s"

msgid "deleted %(type)s tax for %(year)s (%(amount)s)"
msgstr "a supprime la taxe %(type)s pour %(year)s (%(amount)s)"

msgid "added valuation of %(value)s"
msgstr "a ajoute une evaluation de %(value)s"

msgid "updated valuation to %(value)s on %(date)s"
msgstr "a modifie l'evaluation a %(value)s le %(date)s"

msgid "deleted valuation of %(value)s on %(date)s"
msgstr "a supprime l'evaluation de %(value)s le %(date)s"

msgid "invited %(email)s as co-owner"
msgstr "a invite %(email)s comme coproprietaire"

msgid "accepted co-ownership invitation"
msgstr "a accepte l'invitation de copropriete"

msgid "removed you from %(name)s"
msgstr "vous a retire de %(name)s"

msgid "removed %(name)s from this property"
msgstr "a retire %(name)s de cette propriete"

msgid "updated property details"
msgstr "a mis a jour les details de la propriete"

msgid "%(name)s has been removed from %(property)s."
msgstr "%(name)s a ete retire de %(property)s."

msgid "%(name)s removed"
msgstr "%(name)s retire"
```

---

## Part G: Tests

### G1. Model Tests

```python
class TestPropertyNotification(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user("admin", "admin@test.com", "pass")
        self.user2 = User.objects.create_user("coowner", "co@test.com", "pass")
        self.prop = Property.objects.create(
            name="Test", purchase_price=500000, purchase_date="2024-01-01",
            current_valuation=500000, valuation_date="2024-01-01",
        )
        PropertyOwnership.objects.create(user=self.user1, property=self.prop, is_admin=True)
        PropertyOwnership.objects.create(user=self.user2, property=self.prop)

    def test_notify_co_owners_excludes_actor(self):
        notify_co_owners(self.prop, self.user1, "expense_added", "added expense")
        assert PropertyNotification.objects.filter(recipient=self.user2).count() == 1
        assert PropertyNotification.objects.filter(recipient=self.user1).count() == 0

    def test_notification_created_unread(self):
        notify_co_owners(self.prop, self.user1, "tax_added", "added tax")
        notif = PropertyNotification.objects.first()
        assert notif.is_read is False
        assert notif.actor == self.user1
        assert notif.recipient == self.user2
```

### G2. View Tests

```python
class TestExpenseCRUD(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@t.com", "pass")
        self.prop = Property.objects.create(
            name="Test", purchase_price=500000, purchase_date="2024-01-01",
            current_valuation=500000, valuation_date="2024-01-01",
        )
        self.ownership = PropertyOwnership.objects.create(
            user=self.user, property=self.prop, is_admin=True,
        )
        self.expense = PropertyExpense.objects.create(
            property=self.prop, expense_type="renovation",
            description="Paint", amount=500, date="2024-06-01",
            paid_by=self.ownership,
        )
        self.client.login(username="u", password="pass")

    def test_edit_expense(self):
        resp = self.client.post(
            reverse("real_estate:edit_expense", args=[self.prop.pk, self.expense.pk]),
            {"expense_type": "renovation", "description": "New paint", "amount": 600, "date": "2024-06-01"},
        )
        assert resp.status_code == 200
        self.expense.refresh_from_db()
        assert self.expense.description == "New paint"
        assert self.expense.amount == Decimal("600")

    def test_delete_expense(self):
        resp = self.client.delete(
            reverse("real_estate:delete_expense", args=[self.prop.pk, self.expense.pk]),
        )
        assert resp.status_code == 200
        assert not PropertyExpense.objects.filter(pk=self.expense.pk).exists()


class TestRemoveCoOwner(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", "admin@t.com", "pass")
        self.coowner = User.objects.create_user("co", "co@t.com", "pass")
        self.prop = Property.objects.create(
            name="Test", purchase_price=500000, purchase_date="2024-01-01",
            current_valuation=500000, valuation_date="2024-01-01",
        )
        self.admin_own = PropertyOwnership.objects.create(
            user=self.admin, property=self.prop, is_admin=True,
        )
        self.co_own = PropertyOwnership.objects.create(
            user=self.coowner, property=self.prop,
        )
        period = OwnershipPeriod.objects.create(property=self.prop, start_date="2024-01-01")
        OwnershipPeriodShare.objects.create(period=period, owner=self.admin_own, share_pct=50)
        OwnershipPeriodShare.objects.create(period=period, owner=self.co_own, share_pct=50)
        self.client.login(username="admin", password="pass")

    def test_remove_co_owner(self):
        resp = self.client.post(
            reverse("real_estate:remove_co_owner", args=[self.prop.pk, self.co_own.pk]),
        )
        assert resp.status_code == 302
        assert not PropertyOwnership.objects.filter(pk=self.co_own.pk).exists()
        # Admin now has 100%
        shares = get_current_ownership_shares(self.prop)
        assert list(shares.values()) == [Decimal("100")]

    def test_cannot_remove_self(self):
        resp = self.client.post(
            reverse("real_estate:remove_co_owner", args=[self.prop.pk, self.admin_own.pk]),
        )
        assert resp.status_code == 302  # redirects with error message
        assert PropertyOwnership.objects.filter(pk=self.admin_own.pk).exists()

    def test_removed_user_gets_notification(self):
        self.client.post(
            reverse("real_estate:remove_co_owner", args=[self.prop.pk, self.co_own.pk]),
        )
        assert PropertyNotification.objects.filter(
            recipient=self.coowner, verb="co_owner_removed"
        ).exists()
```

---

## Implementation Order

| Step | What | Files |
|------|------|-------|
| 1 | `PropertyNotification` model + migration | `models.py` |
| 2 | `notify_co_owners` helper | `services.py` |
| 3 | Context processor for unread count | `context_processors.py`, `settings/base.py` |
| 4 | Notification list + mark-read views | `views.py`, `urls.py` |
| 5 | Notification templates + bell icon | `notifications.html`, `nav.html`, `bottom_nav.html` |
| 6 | Edit/delete expense views + templates | `views.py`, `urls.py`, partials |
| 7 | Edit/delete tax views + templates | `views.py`, `urls.py`, partials |
| 8 | Edit/delete valuation views + templates | `views.py`, `urls.py`, partials |
| 9 | Remove co-owner view + template | `views.py`, `urls.py`, `confirm_remove_owner.html` |
| 10 | Wire `notify_co_owners()` into all existing add views | `views.py` |
| 11 | FR translations | `django.po` |
| 12 | Tests | `test_views.py`, `test_services.py` |

---

## Files Summary

| File | Action |
|------|--------|
| `apps/real_estate/models.py` | Add `PropertyNotification` |
| `apps/real_estate/services.py` | Add `notify_co_owners()` |
| `apps/real_estate/views.py` | Add 9 views, update 6 existing views |
| `apps/real_estate/urls.py` | Add 9 URL patterns |
| `apps/real_estate/forms.py` | No changes (reuse existing forms) |
| `config/context_processors.py` | Add `unread_notifications()` |
| `config/settings/base.py` | Add context processor |
| `templates/components/nav.html` | Add bell icon with badge |
| `templates/components/bottom_nav.html` | Add bell icon with badge |
| `templates/real_estate/notifications.html` | **New** — notification list page |
| `templates/real_estate/partials/notification_badge.html` | **New** — HTMX badge partial |
| `templates/real_estate/confirm_remove_owner.html` | **New** — remove co-owner confirmation |
| `templates/real_estate/detail.html` | Add remove button in Ownership card |
| `templates/real_estate/partials/expense_list.html` | Add edit/delete buttons |
| `templates/real_estate/partials/expense_form.html` | Support edit mode |
| `templates/real_estate/partials/tax_list.html` | Add edit/delete buttons |
| `templates/real_estate/partials/tax_form.html` | Support edit mode |
| `templates/real_estate/partials/valuation_history.html` | Add edit/delete buttons |
| `templates/real_estate/partials/valuation_form.html` | Support edit mode |
| `locale/fr/LC_MESSAGES/django.po` | ~40 new translation entries |
| `apps/real_estate/tests/test_views.py` | CRUD + remove co-owner tests |
| `apps/real_estate/tests/test_services.py` | `notify_co_owners` tests |

---

## Detailed TODO Checklist

### Phase 1: Notification Infrastructure (model + service + config)

- [x] **1.1** Add `PropertyNotification` model to `apps/real_estate/models.py`
  - 13 VERB_CHOICES, recipient FK, property FK, actor FK, verb, description, is_read, created_at
  - Meta: ordering `["-created_at"]`, index on `(recipient, is_read, -created_at)`
- [x] **1.\1** Add `PropertyNotification` to imports in `apps/real_estate/views.py`
- [x] **1.\1** Run `uv run python manage.py makemigrations real_estate` (creates `0004_propertynotification.py`)
- [x] **1.\1** Run `uv run python manage.py migrate` (apply to SQLite)
- [x] **1.\1** Run migrate against PostgreSQL dev DB (if applicable)
- [x] **1.\1** Add `notify_co_owners(prop, actor, verb, description)` helper to `apps/real_estate/services.py`
- [x] **1.\1** Add `notify_co_owners` to the import block in `apps/real_estate/views.py`
- [x] **1.\1** Add `unread_notifications(request)` function to `config/context_processors.py`
- [x] **1.\1** Register `"config.context_processors.unread_notifications"` in `config/settings/base.py` TEMPLATES context_processors list

### Phase 2: Notification UI (views + templates + nav)

- [x] **2.\1** Add `notification_list` view to `apps/real_estate/views.py`
  - Query `PropertyNotification` for `recipient=request.user`, select_related property+actor, limit 50
- [x] **2.\1** Add `mark_notifications_read` view to `apps/real_estate/views.py`
  - Bulk update `is_read=True` for recipient, return badge partial
- [x] **2.\1** Add 2 URL patterns to `apps/real_estate/urls.py`
  - `notifications/` → `notification_list` (name `notifications`)
  - `notifications/mark-read/` → `mark_notifications_read` (name `mark_all_read`)
- [x] **2.\1** Create `templates/real_estate/notifications.html`
  - Extends base.html, lists notifications as clickable cards linking to property detail
  - Unread: `bg-primary-50/50 border-primary-200` + blue dot indicator
  - "Mark all as read" button with `hx-post`
  - Empty state
- [x] **2.\1** Create `templates/real_estate/partials/notification_badge.html`
  - Renders count badge or empty span, used for HTMX OOB swap after mark-read
- [x] **2.\1** Add bell icon + unread badge to desktop sidebar (`templates/components/nav.html`)
  - After Impact link, before `</nav>` closing tag
  - Bell SVG with `relative` span wrapping the badge
  - Active state via `nav_current == 'notifications'`
- [x] **2.\1** Add bell icon + unread badge to mobile bottom nav (`templates/components/bottom_nav.html`)
  - Replace Profile link with bell icon linking to notifications
  - Smaller badge sizing for mobile (`h-3.5 w-3.5`, `text-[9px]`)
- [x] **2.\1** Update `config/context_processors.py` `nav_current` to return `"notifications"` for `/real-estate/notifications/` path (if not already handled)

### Phase 3: Expense Edit & Delete

- [x] **3.1** Add `edit_expense` view to `apps/real_estate/views.py`
  - GET: return expense_form.html with `editing=True`, `expense` in context
  - POST: validate, save, call `notify_co_owners`, return expense_list.html
- [x] **3.2** Add `delete_expense` view to `apps/real_estate/views.py`
  - DELETE only, capture description before delete, call `notify_co_owners`, return expense_list.html
  - Return `HttpResponseNotAllowed` for non-DELETE methods
- [x] **3.3** Add 2 URL patterns to `apps/real_estate/urls.py`
  - `<int:pk>/expense/<int:expense_id>/edit/` (name `edit_expense`)
  - `<int:pk>/expense/<int:expense_id>/delete/` (name `delete_expense`)
- [x] **3.4** Update `templates/real_estate/partials/expense_list.html`
  - Add empty `<th>` column header for actions
  - Add `group` class to each `<tr>`
  - Add `<td>` with hover-reveal Edit + Delete buttons per row
  - Edit: `hx-get` to `edit_expense`, targets `#expense-form-container`
  - Delete: `hx-delete` to `delete_expense`, targets `#expense-list`, `hx-confirm`
  - Pass `property` in context from all views returning this partial
- [x] **3.5** Update `templates/real_estate/partials/expense_form.html`
  - Conditional `hx-post` URL: `edit_expense` if `editing`, else `add_expense`
  - Conditional button label: "Save" if editing, "Add" if creating
  - Add Cancel button that clears the form container via `hx-get` to `add_expense`
- [x] **3.6** Update `add_expense` view to pass `property` in context when returning expense_list.html

### Phase 4: Tax Edit & Delete

- [x] **4.1** Add `edit_tax` view to `apps/real_estate/views.py`
  - Same pattern as edit_expense but with uniqueness check (exclude current pk)
  - GET: return tax_form.html with `editing=True`, `tax` in context
  - POST: validate, check unique constraint, save, call `notify_co_owners`, return tax_list.html
- [x] **4.2** Add `delete_tax` view to `apps/real_estate/views.py`
  - DELETE only, capture description before delete, call `notify_co_owners`, return tax_list.html
- [x] **4.3** Add 2 URL patterns to `apps/real_estate/urls.py`
  - `<int:pk>/tax/<int:tax_id>/edit/` (name `edit_tax`)
  - `<int:pk>/tax/<int:tax_id>/delete/` (name `delete_tax`)
- [x] **4.4** Update `templates/real_estate/partials/tax_list.html`
  - Add empty `<th>` column header for actions
  - Add `group` class to each `<tr>`
  - Add `<td>` with hover-reveal Edit + Delete buttons per row
  - Edit: `hx-get` to `edit_tax`, targets `#tax-form-container`
  - Delete: `hx-delete` to `delete_tax`, targets `#tax-list`, `hx-confirm`
  - Pass `property` in context from all views returning this partial
- [x] **4.5** Update `templates/real_estate/partials/tax_form.html`
  - Conditional `hx-post` URL: `edit_tax` if `editing`, else `add_tax`
  - Conditional button label: "Save" if editing, "Add" if creating
  - Add Cancel button
- [x] **4.6** Update `add_tax` view to pass `property` in context when returning tax_list.html

### Phase 5: Valuation Edit & Delete

- [x] **5.1** Add `edit_valuation` view to `apps/real_estate/views.py`
  - GET: return valuation_form.html with `editing=True`, `valuation` in context
  - POST: validate, save, update `property.current_valuation` if this is the latest, call `notify_co_owners`, return valuation_history.html with `oob_update=True`
- [x] **5.2** Add `delete_valuation` view to `apps/real_estate/views.py`
  - DELETE only, delete valuation, update `property.current_valuation` to new latest (or fallback to purchase_price), call `notify_co_owners`, return valuation_history.html with `oob_update=True`
- [x] **5.3** Add 2 URL patterns to `apps/real_estate/urls.py`
  - `<int:pk>/valuation/<int:valuation_id>/edit/` (name `edit_valuation`)
  - `<int:pk>/valuation/<int:valuation_id>/delete/` (name `delete_valuation`)
- [x] **5.4** Update `templates/real_estate/partials/valuation_history.html`
  - Add `group` class to each valuation row div
  - Add hover-reveal Edit + Delete buttons inline with value
  - Edit: `hx-get` to `edit_valuation`, targets `#valuation-form-container`
  - Delete: `hx-delete` to `delete_valuation`, targets `#valuation-list`, `hx-confirm`
  - Pass `property` in context from all views returning this partial
- [x] **5.5** Update `templates/real_estate/partials/valuation_form.html`
  - Conditional `hx-post` URL: `edit_valuation` if `editing`, else `add_valuation`
  - Conditional button label: "Save" if editing, "Add" if creating
  - Add Cancel button
- [x] **5.6** Update `add_valuation` view to pass `property` in context when returning valuation_history.html (already does)

### Phase 6: Remove Co-owner

- [x] **6.1** Add `remove_co_owner` view to `apps/real_estate/views.py`
  - GET: render confirmation page
  - POST: close current ownership period, create new period, delete ownership, redistribute shares, notify removed user directly, notify remaining co-owners via `notify_co_owners`, redirect with success message
  - Guard: cannot remove yourself, must be admin
- [x] **6.2** Add 1 URL pattern to `apps/real_estate/urls.py`
  - `<int:pk>/remove-owner/<int:ownership_id>/` (name `remove_co_owner`)
- [x] **6.3** Create `templates/real_estate/confirm_remove_owner.html`
  - Warning card, blocktrans confirmation message, POST form with Remove + Cancel buttons
- [x] **6.4** Update `templates/real_estate/detail.html` — Ownership card
  - Add `group` class to the owner list parent div
  - Add hover-reveal "Remove" link per co-owner row (admin only, not self)
  - Link to `remove_co_owner` URL

### Phase 7: Wire Notifications into Existing Views

- [x] **7.\1** Update `add_expense` view — add `notify_co_owners()` call after `expense.save()`
  - verb: `expense_added`, description: `added expense "%(desc)s" (%(amount)s)`
- [x] **7.\1** Update `add_tax` view — add `notify_co_owners()` call after `tax.save()`
  - verb: `tax_added`, description: `added %(type)s tax for %(year)s (%(amount)s)`
- [x] **7.\1** Update `add_valuation` view — add `notify_co_owners()` call after `valuation.save()`
  - verb: `valuation_added`, description: `added valuation of %(value)s`
- [x] **7.\1** Update `invite_co_owner` view — add `notify_co_owners()` call after `invitation.save()`
  - verb: `invitation_sent`, description: `invited %(email)s as co-owner`
- [x] **7.\1** Update `accept_invitation` view — add `notify_co_owners()` call after ownership created
  - verb: `invitation_accepted`, description: `accepted co-ownership invitation`
- [x] **7.\1** Update `property_edit` view — add `notify_co_owners()` call after `form.save()`
  - verb: `property_updated`, description: `updated property details`

### Phase 8: FR Translations

- [x] **8.1** Add ~40 new `msgid`/`msgstr` pairs to `locale/fr/LC_MESSAGES/django.po`
  - Notification UI strings (Notifications, Alerts, Mark all as read, No notifications yet, ago)
  - CRUD action strings (Edit, Delete, Save, Add, Cancel)
  - Confirmation strings (Delete this expense?, Delete this tax entry?, Delete this valuation?)
  - Co-owner removal strings (Remove Co-owner, Remove, You cannot remove yourself, redistribution warning)
  - All 13 VERB_CHOICES display labels
  - All notification description templates (added/updated/deleted expense/tax/valuation, invited, accepted, removed)
  - Success messages (%(name)s has been removed, %(name)s removed)
- [x] **8.2** Run `uv run python manage.py compilemessages` to compile `.mo` file

### Phase 9: Tests

- [x] **9.1** Add `TestNotifyCoOwners` to `apps/real_estate/tests/test_services.py`
  - `test_excludes_actor` — actor does not receive notification
  - `test_notification_created_unread` — notifications start as unread, correct actor/recipient
  - `test_no_co_owners` — no error when property has single owner
- [x] **9.2** Add `TestExpenseCRUD` to `apps/real_estate/tests/test_views.py`
  - `test_edit_expense_get` — returns form with instance data
  - `test_edit_expense_post` — updates expense, returns list
  - `test_delete_expense` — deletes via DELETE method, returns list
  - `test_edit_expense_creates_notification` — notification created for co-owners
- [x] **9.3** Add `TestTaxCRUD` to `apps/real_estate/tests/test_views.py`
  - `test_edit_tax_post` — updates tax, returns list
  - `test_edit_tax_unique_constraint` — cannot change to duplicate type+year
  - `test_delete_tax` — deletes via DELETE method, returns list
- [x] **9.4** Add `TestValuationCRUD` to `apps/real_estate/tests/test_views.py`
  - `test_edit_valuation_post` — updates valuation, returns list with OOB
  - `test_edit_valuation_updates_current` — property.current_valuation updated if latest
  - `test_delete_valuation` — deletes, updates property.current_valuation to new latest
  - `test_delete_valuation_keeps_latest` — falls back to next latest
- [x] **9.5** Add `TestRemoveCoOwner` to `apps/real_estate/tests/test_views.py`
  - `test_remove_co_owner` — ownership deleted, shares redistributed to 100%
  - `test_cannot_remove_self` — redirects with error, ownership preserved
  - `test_non_admin_cannot_remove` — returns 404
  - `test_removed_user_gets_notification` — notification with verb `co_owner_removed`
  - `test_confirmation_page_renders` — GET shows confirmation page
- [x] **9.6** Add `TestNotificationViews` to `apps/real_estate/tests/test_views.py`
  - `test_notification_list` — renders notifications page
  - `test_mark_all_read` — bulk updates is_read=True
  - `test_notification_list_empty` — shows empty state
- [x] **9.7** Run full test suite: `uv run pytest apps/real_estate/` — 96 passed
- [x] **9.8** Run linter: `uv run ruff check apps/real_estate/ config/` — all checks passed
- [x] **9.9** Run formatter: `uv run ruff format apps/real_estate/ config/` — 25 files already formatted

### Phase 10: Final Verification

- [ ] **10.1** Manual test: create property with co-owner, verify invitation notification appears for co-owner
- [ ] **10.2** Manual test: add expense → co-owner sees notification in bell icon
- [ ] **10.3** Manual test: edit expense → co-owner notified, list updates inline
- [ ] **10.4** Manual test: delete expense → co-owner notified, row removed
- [ ] **10.5** Manual test: add/edit/delete tax → same notification flow
- [ ] **10.6** Manual test: add/edit/delete valuation → same notification flow + OOB property value update
- [ ] **10.7** Manual test: remove co-owner → confirmation page, shares redistributed, removed user notified
- [ ] **10.8** Manual test: notification list page → click notification links to property detail
- [ ] **10.9** Manual test: "Mark all as read" → badge disappears, blue dots removed
- [ ] **10.10** Manual test: mobile bottom nav → bell icon shows badge count
- [ ] **10.11** Verify FR translations render correctly when language set to French
- [ ] **10.12** Run PostgreSQL migration on dev DB if applicable
