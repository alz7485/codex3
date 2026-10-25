"""Stable character IDs; appearance and selected personality stay independent."""

CHARACTERS = {
    'A': 'つづり', 'B': 'ビット', 'E': 'ペンギー',
}
# Keep retired profile metadata readable without shipping their artwork or
# showing them in selectors. Existing custom conversations remain intact.
RECOGNIZED_PROFILE_KEYS = 'ABEFNSH'


def profile_for(profiles, character):
    return profiles[character]
