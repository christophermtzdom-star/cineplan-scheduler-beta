"""Central Material Symbols catalog for CinePlan Scheduler."""


# Core project entities
PROJECT = "folder"
SCENE = "movie"
LOCATION = "location_on"
CHARACTER = "groups"
OCTAVOS = "menu_book"

# Breakdown departments
BREAKDOWN = "fact_check"
CAST = "groups"
PROPS = "inventory_2"
WARDROBE = "checkroom"
VFX = "graphic_eq"
EXTRAS = "group_add"
PRODUCTION = "assignment"
EXPORT = "download"

# Production workflow
STRIPBOARD = "view_agenda"
SHOOTING = "videocam"
CALLSHEET = "event_note"

# File formats
PDF = "picture_as_pdf"
EXCEL = "table_view"
JSON = "data_object"

# Information and status
INFO = "info"
DESCRIPTION = "description"
NOTE = "note_alt"
STATUS = "flag"
ANALYTICS = "analytics"
TASK = "task_alt"
PENDING = "pending_actions"

# Navigation and common actions
HOME = "home"
REVIEW = "fact_check"
CALENDAR = "calendar_month"
EVENT = "event"
GRID = "grid_view"
UPLOAD = "upload"
UPLOAD_FILE = "upload_file"
SAVE = "save"
OPEN_FOLDER = "folder_open"
SETTINGS = "settings"
ACCOUNT = "account_circle"
ADD = "add"
ADD_CHARACTER = "person_add"
ADD_LOCATION = "add_location_alt"
DELETE = "delete"
REMOVE_LOCATION = "location_off"
SYNC = "sync"
ARROW_FORWARD = "arrow_forward"
HISTORY = "history"
QUICK_ACTION = "bolt"
TIP = "lightbulb"


ICONS = {
    name: value
    for name, value in globals().copy().items()
    if name.isupper() and isinstance(value, str)
}


def cine_icon(name, size=32, color="currentColor"):
    """Render a Material Symbol while preserving the original helper API."""
    return (
        f'<span class="material-symbols-rounded cine-material-icon" '
        f'style="font-size:{size}px; color:{color};">'
        f'{name}'
        f'</span>'
    )
