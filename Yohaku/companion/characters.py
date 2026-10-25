"""Stable character IDs; appearance and selected personality stay independent."""

CHARACTERS = {
    'A': 'つづり', 'B': 'ビット', 'E': 'ペギー', 'F': 'きなこ',
    'N': 'なぎ', 'S': 'しずく', 'H': 'すみ',
}
LEGACY_CHARACTERS = 'ABEF'
ATLAS_CHARACTERS = 'NSH'

NEW_PROFILES = {
    'N': {'voice': '馴れ馴れしい関西弁',
          'description': '丸い鼻のカピバラ。気さくな関西弁で話す、世話焼きな相棒。',
          'tagline': '呼んだ？ なんでも聞いてや。'},
    'S': {'voice': '寡黙な先輩',
          'description': '落ち着いた目のふくろう。言葉は少なく、心の声は少しお茶目。',
          'tagline': '…\n（呼ばれると、少しうれしい。）'},
    'H': {'voice': '孤高のギャンブラー',
          'description': 'ベスト姿のサギ。一人で盤面を読み、勝ち筋と引き際を見定める。',
          'tagline': '聞こう……次の一手。\n空けてある、あんたの席。'},
}


def profile_for(profiles, character):
    # A previously valid document close to 2 MiB can use new characters without
    # inserting extra bytes or losing any of the user's edited conversation.
    return profiles[character] if character in profiles else NEW_PROFILES[character]
