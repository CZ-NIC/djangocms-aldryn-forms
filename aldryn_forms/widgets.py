from typing import Optional

from django.conf import settings
from django.forms import MultiWidget, Select, URLInput
from django.utils.translation import gettext_lazy as _

from djangocms_link.fields import LinkAutoCompleteWidget, SiteAutocompleteSelect, TextInput


# Configure the LinkWidget
link_types = {
    "internal_link": _("Internal link"),
    "external_link": _("External link/anchor"),
}

allowed_link_types = tuple(link_types.keys())

# Show anchor sub-widget only for internal_link
_mapping = {key: key for key in link_types.keys()}
_mapping["anchor"] = "internal_link"


# Create the available widgets
_available_widgets = {
    "always": Select(
        choices=list(link_types.items()),
        attrs={
            "class": "js-link-widget-selector",
            "data-help": _("No destination selected. Use the dropdown to select a destination."),
        },
    ),  # Link type selector
    "external_link": URLInput(
        attrs={
            "widget": "external_link",
            "placeholder": _("https://example.com or #anchor"),
            "data-help": _(
                "Provide a link to an external URL, including the schema such as 'https://'. "
                "Optionally, add an #anchor (including the #) to scroll to."
            )
        },
    ),  # External link input
    "internal_link": LinkAutoCompleteWidget(
        attrs={
            "widget": "internal_link",
            "data-help": _("Select from available internal destinations. Optionally, add an anchor to scroll to."),
            "data-placeholder": _("Select internal destination"),
        },
    ),  # Internal link selector
    "anchor": TextInput(
        attrs={
            "widget": "anchor",
            "placeholder": _("#anchor"),
            "data-help": _("Provide an anchor to scroll to."),
        }
    ),
}


class LinkWidget(MultiWidget):
    template_name = "djangocms_link/admin/link_widget.html"
    data_pos = {}
    number_sites = None
    default_site_selector = getattr(settings, "DJANGOCMS_LINK_SITE_SELECTOR", False)

    class Media:
        js = ("djangocms_link/link-widget.js",)
        css = {"all": ("djangocms_link/link-widget.css",)}

    def __init__(self, site_selector: Optional[bool] = None):
        if site_selector is None:
            site_selector = LinkWidget.default_site_selector

        widgets = [
            widget
            for key, widget in _available_widgets.items()
            if key == "always" or _mapping[key] in link_types
        ]
        if site_selector and "internal_link" in allowed_link_types:
            index = next(
                i
                for i, widget in enumerate(widgets)
                if widget.attrs.get("widget") == "internal_link"
            )
            widgets.insert(
                index,
                SiteAutocompleteSelect(
                    attrs={
                        "class": "js-link-site-widget",
                        "widget": "site",
                        "data-placeholder": _("Select site"),
                    },
                ),
            )  # Site selector

        # Remember which widget expets its content at which position
        self.data_pos = {
            widget.attrs.get("widget"): i for i, widget in enumerate(widgets)
        }
        super().__init__(widgets)

    def get_context(self, name: str, value: Optional[str], attrs: dict) -> dict:
        if not self.is_required:
            self.widgets[0].choices = [("empty", "---------")] + self.widgets[0].choices
        context = super().get_context(name, value, attrs)
        context["widget"]["subwidgets"] = {
            widget["attrs"].get("widget", "link-type-selector"): widget
            for widget in context["widget"]["subwidgets"]
        }
        return context
