from django.forms.widgets import ClearableFileInput


class DragAndDropFilesInput(ClearableFileInput):
    """Drag and drop Multiple Files Input."""

    allow_multiple_selected = True
    template_name = "aldryn_forms/widgets/drag_and_drop_files.html"
