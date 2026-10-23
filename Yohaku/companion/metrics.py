"""Stable aggregate-context names for JSON conditions and the editor."""
METRICS = {
    'idle_minutes': '操作がない時間（分）', 'active_streak_minutes': '操作が続いた推定時間（分）',
    'daily_active_minutes': '今日の操作あり累計（分）', 'daily_idle_minutes': '今日の操作なし累計（分）',
    'observed_minutes': '今日の計測時間（分）', 'open_office_files': '開いているOffice文書数',
    'desktop_files': 'デスクトップのファイル数', 'until_work_start_minutes': '始業まで（分）',
    'until_work_end_minutes': '定時まで（分）', 'after_work_end_minutes': '定時を過ぎて（分）',
    'file_open_count': '今日いちばん開き直したファイルの回数',
    'missed_yesterday': '昨日アプリを使っていない（1=はい）',
    'days_since_last_use': '前回アプリ使用日からの日数', 'weekly_events': '今週の時間指定の予定数',
    'daily_events': '今日の時間指定の予定数', 'next_event_minutes': '次の予定まで（分）',
    'unread_mail_count': 'Outlook受信トレイの未読メール数',
}
