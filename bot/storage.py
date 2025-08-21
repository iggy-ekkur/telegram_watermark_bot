from collections import defaultdict

user_channels = defaultdict(lambda: "@testplaygroundwatermark")
user_watermarks = defaultdict(lambda: "FLP STONE")

post_cache = {}
album_buffer = defaultdict(lambda: {"messages": [], "shown": False, "status_msg_id": None})
album_timers = defaultdict(lambda: None)

user_messages = defaultdict(list)
bot_messages = defaultdict(list)
preview_messages = defaultdict(list)
protected_messages = defaultdict(set)

publishing_in_progress = defaultdict(lambda: False)

last_menu_message = defaultdict(lambda: None)
processing_status_msg = defaultdict(lambda: None)
