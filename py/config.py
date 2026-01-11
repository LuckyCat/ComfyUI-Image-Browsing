extension_tag = "ComfyUI Image Browsing"

extension_uri: str = None
output_uri: str = None
workflows_uri: str = None
prompts_uri: str = None
thumbnail_cache_uri: str = None

# FFmpeg configuration
ffmpeg_path: str = "ffmpeg"  # Default: use system PATH


from server import PromptServer

serverInstance = PromptServer.instance
routes = serverInstance.routes
