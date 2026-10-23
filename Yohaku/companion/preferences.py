"""Small, explicit behavior presets and taskbar snapping in logical pixels."""
PRESETS = {
    'standard': ('標準', {'chatter': True, 'animation': True, 'walking': True}, 10),
    'restrained': ('控えめ', {'chatter': True, 'animation': True, 'walking': False}, 30),
    'notifications': ('通知だけ', {'chatter': False, 'animation': False, 'walking': False}, None),
}


def snapped_y(y, floor_y, enabled, distance):
    return floor_y if enabled and 0 <= floor_y - y <= distance else y
