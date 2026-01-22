import os
import folder_paths
import asyncio
import hashlib
from .py import config


config.extension_uri = os.path.dirname(__file__)

# Import paths_config early to load configuration
from .py import paths_config

# Load paths from configuration
paths = paths_config.load_paths_config()
config.output_uri = paths['output']
config.workflows_uri = paths['workflows']
config.prompts_uri = paths['prompts']
config.thumbnail_cache_uri = paths['thumbnail_cache']

# Create directories if they don't exist
for path_name, path_value in paths.items():
    if path_value and not os.path.exists(path_value):
        try:
            os.makedirs(path_value, exist_ok=True)
        except Exception as e:
            print(f"Warning: Failed to create {path_name} directory at {path_value}: {e}")


from .py import utils

version = utils.get_current_version()
utils.download_web_distribution(version)


from aiohttp import web
from .py import services, ffmpeg_config


routes = config.routes


# ============================================================================
# Compression helper for JSON responses
# ============================================================================

def json_response_compressed(data, **kwargs):
    """Create compressed JSON response for large payloads"""
    response = web.json_response(data, **kwargs)
    # Enable gzip compression for responses > 1KB
    response.enable_compression()
    return response


def get_folder_etag(directory: str) -> str:
    """Generate ETag based on folder mtime"""
    try:
        mtime = os.path.getmtime(directory)
        return f'"{hashlib.md5(f"{directory}:{mtime}".encode()).hexdigest()}"'
    except OSError:
        return '""'


def check_etag_match(request, etag: str) -> bool:
    """Check if client's If-None-Match header matches our ETag"""
    if_none_match = request.headers.get('If-None-Match', '')
    return if_none_match == etag


# ============================================================================
# Output folder routes (media files)
# ============================================================================

@routes.get("/image-browsing/output{pathname:.*}")
async def scan_output_folder(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_output_pathname(pathname)
        filepath = utils.get_real_output_filepath(pathname)

        # Signal user activity - this auto-pauses background caching
        services.signal_user_activity()

        if os.path.isfile(filepath):

            preview_type = request.query.get("preview", None)
            if not preview_type:
                # Full size file - HIGHEST PRIORITY
                # Signal preview mode to pause ALL background work
                services.signal_preview_mode()

                stat = os.stat(filepath)
                etag = f'"{stat.st_mtime}-{stat.st_size}"'

                # Check if client has cached version
                if_none_match = request.headers.get('If-None-Match', '')
                if if_none_match == etag:
                    return web.Response(status=304)

                return web.FileResponse(
                    filepath,
                    headers={
                        "Cache-Control": "public, max-age=31536000, immutable",  # 1 year (effectively forever)
                        "ETag": etag
                    }
                )

            if services.assert_file_type(filepath, ["image"]):
                # Get max_size from query params, default to 128
                max_size_str = request.query.get("max_size", "128")
                try:
                    max_size = int(max_size_str)
                except ValueError:
                    max_size = 128

                cache_key = services.get_cache_key(filepath, max_size)
                etag = f'"{cache_key}"'

                # Check if client has cached version
                if_none_match = request.headers.get('If-None-Match', '')
                if if_none_match == etag:
                    return web.Response(status=304)

                image_data = services.get_image_data(filepath, max_size)
                # Cache forever - only invalidate on manual recache
                return web.Response(
                    body=image_data.getvalue(),
                    content_type="image/webp",
                    headers={
                        "Cache-Control": "public, max-age=31536000, immutable",  # 1 year (effectively forever)
                        "ETag": etag
                    }
                )

            if services.assert_file_type(filepath, ["video"]):
                # Get max_size from query params, default to 128
                max_size_str = request.query.get("max_size", "128")
                try:
                    max_size = int(max_size_str)
                except ValueError:
                    max_size = 128

                cache_key = services.get_cache_key(filepath, max_size)
                etag = f'"{cache_key}"'

                # Check if client has cached version
                if_none_match = request.headers.get('If-None-Match', '')
                if if_none_match == etag:
                    return web.Response(status=304)

                image_data = services.get_image_data(filepath, max_size)
                # Cache forever - only invalidate on manual recache
                return web.Response(
                    body=image_data.getvalue(),
                    content_type="image/webp",
                    headers={
                        "Cache-Control": "public, max-age=31536000, immutable",  # 1 year (effectively forever)
                        "ETag": etag
                    }
                )

        elif os.path.isdir(filepath):
            # Signal browsing mode - pauses cache-all to prioritize current folder
            services.signal_browsing_mode()

            # Check ETag for conditional request (304 Not Modified)
            etag = get_folder_etag(filepath)
            if check_etag_match(request, etag):
                return web.Response(status=304)

            items = await asyncio.to_thread(services.scan_directory_items, filepath)
            return json_response_compressed(
                {"success": True, "data": items},
                headers={
                    "ETag": etag,
                    "Cache-Control": "private, max-age=300, must-revalidate"  # 5 minutes with revalidation
                }
            )

        return web.Response(status=404)
    except Exception as e:
        error_msg = f"Obtain failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


# ============================================================================
# Workflows folder routes
# ============================================================================

@routes.get("/image-browsing/workflows{pathname:.*}")
async def scan_workflows_folder(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_workflows_pathname(pathname)
        filepath = utils.get_real_workflows_filepath(pathname)

        if os.path.isfile(filepath):
            # Cache workflow files forever with ETag validation
            stat = os.stat(filepath)
            etag = f'"{stat.st_mtime}-{stat.st_size}"'

            # Check if client has cached version
            if_none_match = request.headers.get('If-None-Match', '')
            if if_none_match == etag:
                return web.Response(status=304)

            return web.FileResponse(
                filepath,
                headers={
                    "Cache-Control": "public, max-age=31536000, immutable",  # 1 year
                    "ETag": etag
                }
            )

        elif os.path.isdir(filepath):
            # Check ETag for conditional request (304 Not Modified)
            etag = get_folder_etag(filepath)
            if check_etag_match(request, etag):
                return web.Response(status=304)

            items = await asyncio.to_thread(services.scan_workflows_directory, filepath)
            return json_response_compressed(
                {"success": True, "data": items},
                headers={
                    "ETag": etag,
                    "Cache-Control": "private, max-age=300, must-revalidate"  # 5 minutes
                }
            )

        return web.Response(status=404)
    except Exception as e:
        error_msg = f"Obtain workflows failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/workflows{pathname:.*}")
async def create_workflow_folder(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_workflows_pathname(pathname)
        reader = await request.multipart()
        await services.create_file_or_folder_generic(pathname, reader, "workflows")
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Create workflow folder failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.put("/image-browsing/workflows{pathname:.*}")
async def update_workflow_file(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_workflows_pathname(pathname)
        data = await request.json()
        filename = data.get("filename", None)
        services.rename_file_generic(pathname, filename, "workflows")
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Update workflow failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/duplicate-workflow")
async def duplicate_workflow(request):
    try:
        data = await request.json()
        file_path = data.get("file_path", None)
        if not file_path:
            return web.json_response({"success": False, "error": "Missing file_path"}, status=400)
        
        new_path = await asyncio.to_thread(services.duplicate_workflow, file_path)
        return web.json_response({"success": True, "data": {"new_path": new_path}})
    except Exception as e:
        error_msg = f"Duplicate workflow failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


# ============================================================================
# Prompts folder routes
# ============================================================================

@routes.get("/image-browsing/prompts{pathname:.*}")
async def scan_prompts_folder(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_prompts_pathname(pathname)
        filepath = utils.get_real_prompts_filepath(pathname)

        if os.path.isfile(filepath):
            # Return file content for text files
            if filepath.endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return web.json_response({"success": True, "data": {"content": content}})
            return web.FileResponse(filepath)

        elif os.path.isdir(filepath):
            # Check ETag for conditional request (304 Not Modified)
            etag = get_folder_etag(filepath)
            if check_etag_match(request, etag):
                return web.Response(status=304)

            items = await asyncio.to_thread(services.scan_prompts_directory, filepath)
            return json_response_compressed(
                {"success": True, "data": items},
                headers={
                    "ETag": etag,
                    "Cache-Control": "private, max-age=300, must-revalidate"  # 5 minutes
                }
            )

        return web.Response(status=404)
    except Exception as e:
        error_msg = f"Obtain prompts failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/prompts{pathname:.*}")
async def create_prompt_folder(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_prompts_pathname(pathname)
        reader = await request.multipart()
        await services.create_file_or_folder_generic(pathname, reader, "prompts")
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Create prompt folder failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.put("/image-browsing/prompts{pathname:.*}")
async def update_prompt_file(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_prompts_pathname(pathname)
        data = await request.json()
        
        # Check if this is content update or rename
        if "content" in data:
            # Save file content
            filepath = utils.get_real_prompts_filepath(pathname.replace("/content", ""))
            content = data.get("content", "")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return web.json_response({"success": True})
        else:
            # Rename file
            filename = data.get("filename", None)
            services.rename_file_generic(pathname, filename, "prompts")
            return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Update prompt failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/create-prompt")
async def create_new_prompt(request):
    try:
        data = await request.json()
        folder_path = data.get("folder_path", "/prompts")
        filename = data.get("filename", "New Prompt.txt")
        
        filepath = utils.get_real_prompts_filepath(folder_path)
        full_path = os.path.join(filepath, filename)
        
        # Handle name conflicts
        base, ext = os.path.splitext(full_path)
        counter = 1
        while os.path.exists(full_path):
            full_path = f"{base}({counter}){ext}"
            counter += 1
        
        # Create empty file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write("")
        
        return web.json_response({"success": True, "data": {"path": full_path}})
    except Exception as e:
        error_msg = f"Create prompt failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


# ============================================================================
# Batch requests - fetch multiple folders in one request
# ============================================================================

@routes.post("/image-browsing/batch")
async def batch_folder_request(request):
    """Fetch multiple folder contents in a single request"""
    try:
        # Signal user activity - this auto-pauses background caching
        services.signal_user_activity()

        data = await request.json()
        paths = data.get("paths", [])
        
        if not paths or len(paths) > 50:  # Limit batch size
            return web.json_response({
                "success": False, 
                "error": "Invalid paths (0 < len <= 50)"
            }, status=400)
        
        results = {}
        
        async def fetch_folder(path: str):
            try:
                # Determine folder type and get real path
                if path.startswith('/output'):
                    pathname = utils.get_output_pathname(path)
                    filepath = utils.get_real_output_filepath(pathname)
                    items = await asyncio.to_thread(services.scan_directory_items, filepath)
                elif path.startswith('/workflows'):
                    pathname = utils.get_workflows_pathname(path)
                    filepath = utils.get_real_workflows_filepath(pathname)
                    items = await asyncio.to_thread(services.scan_workflows_directory, filepath)
                elif path.startswith('/prompts'):
                    pathname = utils.get_prompts_pathname(path)
                    filepath = utils.get_real_prompts_filepath(pathname)
                    items = await asyncio.to_thread(services.scan_prompts_directory, filepath)
                else:
                    return path, {"error": "Invalid path type"}
                
                etag = get_folder_etag(filepath)
                return path, {"data": items, "etag": etag}
            except Exception as e:
                return path, {"error": str(e)}
        
        # Fetch all folders concurrently
        tasks = [fetch_folder(path) for path in paths]
        folder_results = await asyncio.gather(*tasks)
        
        for path, result in folder_results:
            results[path] = result

        return json_response_compressed({"success": True, "data": results})
    except Exception as e:
        error_msg = f"Batch request failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


# ============================================================================
# Output folder mutation routes
# ============================================================================

@routes.post("/image-browsing/output{pathname:.*}")
async def create_file_or_folder(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_output_pathname(pathname)
        reader = await request.multipart()
        await services.create_file_or_folder(pathname, reader)
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Create failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.put("/image-browsing/output{pathname:.*}")
async def update_output_file(request):
    try:
        pathname = request.match_info.get("pathname", None)
        pathname = utils.get_output_pathname(pathname)
        data = await request.json()
        filename = data.get("filename", None)
        services.rename_file(pathname, filename)
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Update failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.delete("/image-browsing/delete")
async def delete_files(request):
    try:
        data = await request.json()
        file_list = data.get("file_list", [])
        services.recursive_delete_files_generic(file_list)
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Delete failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/move")
async def move_files(request):
    try:
        data = await request.json()
        file_list = data.get("file_list", [])
        target_folder = data.get("target_folder", None)
        
        if not file_list or not target_folder:
            return web.json_response({"success": False, "error": "Missing file_list or target_folder"}, status=400)
        
        # Validate that files and target are in the same root
        services.move_files_generic(file_list, target_folder)
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Move failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})



@routes.post("/image-browsing/merge-videos")
async def merge_videos(request):
    """Merge selected videos sequentially into a new file (ffmpeg concat)."""
    try:
        data = await request.json()
        file_list = data.get("file_list", [])
        output_name = data.get("output_name", None)

        if not file_list or len(file_list) < 2:
            return web.json_response({"success": False, "error": "Need at least 2 videos"}, status=400)

        if not output_name:
            return web.json_response({"success": False, "error": "Missing output_name"}, status=400)

        new_fullname = await asyncio.to_thread(services.merge_videos, file_list, output_name)
        return web.json_response({"success": True, "data": {"output": new_fullname}})
    except Exception as e:
        error_msg = f"Merge failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})



@routes.post("/image-browsing/cache-folders")
async def cache_folder_structure(request):
    """
    Phase 1: Cache folder structure only (fast).
    This enables instant navigation while thumbnails load in background.
    """
    try:
        result = await asyncio.to_thread(services.cache_folder_structure)

        if "error" in result:
            return web.json_response({"success": False, "error": result["error"]})

        return json_response_compressed({
            "success": True,
            "data": {
                "folders": result.get("folders", 0),
                "files": result.get("files", 0),
                "folder_data": result.get("folder_data", {})
            }
        })
    except Exception as e:
        error_msg = f"Folder cache failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/cache-all")
async def cache_all_thumbnails(request):
    """
    Two-phase caching:
    Phase 1: Cache folder structure (fast, enables navigation)
    Phase 2: Generate thumbnails (slow, background)
    """
    try:
        data = await request.json()
        max_size = data.get("max_size", 128)
        priority_folder = data.get("priority_folder", None)

        # Start two-phase caching in background
        asyncio.create_task(asyncio.to_thread(
            services.cache_all_images, max_size, 4, priority_folder
        ))

        return web.json_response({"success": True, "message": "Two-phase caching started"})
    except Exception as e:
        error_msg = f"Cache failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.get("/image-browsing/folder-metadata")
async def get_folder_metadata(request):
    """Get pre-cached folder metadata for client-side caching"""
    try:
        metadata = await asyncio.to_thread(services.precache_all_folders)
        return json_response_compressed({"success": True, "data": metadata})
    except Exception as e:
        error_msg = f"Failed to get folder metadata: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.get("/image-browsing/cache-status")
async def get_cache_status(request):
    """Get current cache status"""
    try:
        status = services.get_cache_status()
        return web.json_response({"success": True, "data": status})
    except Exception as e:
        error_msg = f"Status failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/cache-pause")
async def pause_caching(request):
    """Pause caching process"""
    try:
        status = services.pause_caching()
        return web.json_response({"success": True, "data": status})
    except Exception as e:
        error_msg = f"Pause failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/cache-resume")
async def resume_caching(request):
    """Resume caching process"""
    try:
        status = services.resume_caching()
        return web.json_response({"success": True, "data": status})
    except Exception as e:
        error_msg = f"Resume failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/cache-stop")
async def stop_caching(request):
    """Stop caching process"""
    try:
        status = services.stop_caching()
        return web.json_response({"success": True, "data": status})
    except Exception as e:
        error_msg = f"Stop failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/signal-activity")
async def signal_user_activity_endpoint(request):
    """Signal user activity to pause background caching"""
    try:
        services.signal_user_activity()
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)})


@routes.post("/image-browsing/cache-config")
async def set_cache_config(request):
    """Set cache configuration"""
    try:
        data = await request.json()
        max_size_gb = data.get("max_size_gb", 1.0)
        
        result = services.set_cache_max_size(max_size_gb)
        return web.json_response({"success": True, "data": result})
    except Exception as e:
        error_msg = f"Config failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.delete("/image-browsing/cache")
async def clear_cache(request):
    """Clear all cached thumbnails"""
    try:
        services.clear_cache()
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Clear cache failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.get("/image-browsing/folder-counts{pathname:.*}")
async def get_folder_counts(request):
    """Get file counts for folder and subfolders"""
    try:
        pathname = request.match_info.get("pathname", "")
        pathname = utils.get_output_pathname(pathname)
        
        counts = await asyncio.to_thread(services.get_folder_counts, pathname)
        return web.json_response({"success": True, "data": counts})
    except Exception as e:
        error_msg = f"Folder counts failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/archive")
async def archive_specific_files(request):
    try:
        data = await request.json()
        file_list = data.get("file_list", [])
        if not file_list or len(file_list) == 0:
            return web.json_response({"success": False, "error": "No files provided"}, status=400)

        root_dir = data.get("uri", "/output/")
        zip_filename = await services.package_file(root_dir, file_list)
        return web.json_response({"success": True, "data": zip_filename})
    except Exception as e:
        error_msg = f"Archive failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.get("/image-browsing/archive/{tmp_name}")
async def download_tmp_file(request):
    try:
        tmp_name = request.match_info.get("tmp_name", None)
        if not tmp_name:
            return web.Response(status=404)

        temp_file_path = await services.get_temp_file_path(tmp_name)
        if not os.path.isfile(temp_file_path):
            return web.Response(status=404)

        async with services.open_tmp_file(temp_file_path) as f:
            response = web.StreamResponse()
            response.headers["Content-Disposition"] = f'attachment; filename="{tmp_name}"'
            response.headers["Content-Type"] = "application/x-zip-compressed"

            await response.prepare(request)

            chunk_size = 256 * 1024

            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                await response.write(chunk)
            await response.write_eof()
            return response
    except Exception as e:
        error_msg = f"Read archive failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/extract-frame")
async def extract_video_frame(request):
    """Extract first, last, or current frame from a video file"""
    try:
        data = await request.json()
        video_path = data.get("video_path", None)
        frame_type = data.get("frame_type", "first")  # "first", "last", or "current"
        timestamp = data.get("timestamp", 0)  # For "current" frame type
        
        if not video_path:
            return web.json_response({"success": False, "error": "Missing video_path"}, status=400)
        
        output_path = await asyncio.to_thread(services.extract_video_frame, video_path, frame_type, timestamp)
        return web.json_response({"success": True, "data": {"output": output_path}})
    except Exception as e:
        error_msg = f"Extract frame failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/refresh-thumbnail")
async def refresh_thumbnail(request):
    """Regenerate thumbnail for a file"""
    try:
        data = await request.json()
        file_path = data.get("file_path", None)

        if not file_path:
            return web.json_response({"success": False, "error": "Missing file_path"}, status=400)

        await asyncio.to_thread(services.regenerate_thumbnail, file_path)
        return web.json_response({"success": True})
    except Exception as e:
        error_msg = f"Refresh thumbnail failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/recache-folder")
async def recache_folder(request):
    """Force recache all files in a folder (regenerate all thumbnails)"""
    try:
        data = await request.json()
        folder_path = data.get("folder_path", None)

        if not folder_path:
            return web.json_response({"success": False, "error": "Missing folder_path"}, status=400)

        result = await asyncio.to_thread(services.recache_folder, folder_path)
        return web.json_response({"success": True, "data": result})
    except Exception as e:
        error_msg = f"Recache folder failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/copy-to-input")
async def copy_to_input(request):
    """Copy file to input folder and return LoadImage/LoadVideo node data"""
    try:
        data = await request.json()
        file_path = data.get("file_path", None)
        node_type = data.get("type", "image")  # "image" or "video"
        
        if not file_path:
            return web.json_response({"success": False, "error": "Missing file_path"}, status=400)
        
        result = await asyncio.to_thread(services.copy_to_input_and_get_node, file_path, node_type)
        return web.json_response({"success": True, "data": result})
    except Exception as e:
        error_msg = f"Copy to input failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/split-video")
async def split_video(request):
    """Split video at specified timestamp"""
    try:
        data = await request.json()
        video_path = data.get("video_path", None)
        timestamp = data.get("timestamp", 0)
        
        if not video_path:
            return web.json_response({"success": False, "error": "Missing video_path"}, status=400)
        
        result = await asyncio.to_thread(services.split_video_at_timestamp, video_path, timestamp)
        return web.json_response({"success": True, "data": result})
    except Exception as e:
        error_msg = f"Split video failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/reverse-video")
async def reverse_video(request):
    """Create a reversed copy of a video"""
    try:
        data = await request.json()
        video_path = data.get("video_path", None)
        
        if not video_path:
            return web.json_response({"success": False, "error": "Missing video_path"}, status=400)
        
        result = await asyncio.to_thread(services.reverse_video, video_path)
        return web.json_response({"success": True, "data": result})
    except Exception as e:
        error_msg = f"Reverse video failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


# ============================================================================
# FFmpeg configuration routes
# ============================================================================

@routes.get("/image-browsing/ffmpeg/status")
async def get_ffmpeg_status(request):
    """Get FFmpeg configuration and status"""
    try:
        current_path = ffmpeg_config.get_ffmpeg_path()
        test_result = await asyncio.to_thread(ffmpeg_config.test_ffmpeg, current_path)
        detected = await asyncio.to_thread(ffmpeg_config.detect_ffmpeg)

        return web.json_response({
            "success": True,
            "data": {
                "current_path": current_path,
                "test": test_result,
                "detected_paths": detected
            }
        })
    except Exception as e:
        error_msg = f"FFmpeg status failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/ffmpeg/set-path")
async def set_ffmpeg_path(request):
    """Set FFmpeg path"""
    try:
        data = await request.json()
        ffmpeg_path = data.get("path", None)

        if not ffmpeg_path:
            return web.json_response({"success": False, "error": "Missing path"}, status=400)

        # Test the path first
        test_result = await asyncio.to_thread(ffmpeg_config.test_ffmpeg, ffmpeg_path)

        if not test_result['available']:
            return web.json_response({
                "success": False,
                "error": f"FFmpeg not working: {test_result['error']}"
            })

        # Save if test passed
        success = await asyncio.to_thread(ffmpeg_config.set_ffmpeg_path, ffmpeg_path)

        if success:
            return web.json_response({
                "success": True,
                "message": "FFmpeg path saved",
                "data": test_result
            })
        else:
            return web.json_response({
                "success": False,
                "error": "Failed to save FFmpeg path"
            })

    except Exception as e:
        error_msg = f"Set FFmpeg path failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/ffmpeg/auto-detect")
async def auto_detect_ffmpeg(request):
    """Auto-detect FFmpeg and set the best path"""
    try:
        detected = await asyncio.to_thread(ffmpeg_config.detect_ffmpeg)

        if not detected:
            return web.json_response({
                "success": False,
                "error": "No FFmpeg installation found"
            })

        # Use first detected (usually system PATH)
        best_path = detected[0]['path']
        success = await asyncio.to_thread(ffmpeg_config.set_ffmpeg_path, best_path)

        if success:
            test_result = await asyncio.to_thread(ffmpeg_config.test_ffmpeg, best_path)
            return web.json_response({
                "success": True,
                "message": f"FFmpeg auto-detected: {detected[0]['location']}",
                "data": {
                    "path": best_path,
                    "test": test_result
                }
            })
        else:
            return web.json_response({
                "success": False,
                "error": "Failed to save auto-detected path"
            })

    except Exception as e:
        error_msg = f"Auto-detect failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


# ============================================================================
# Paths Configuration Routes
# ============================================================================

@routes.get("/image-browsing/paths/status")
async def get_paths_status(request):
    """Get all configured paths with their status"""
    try:
        paths_info = await asyncio.to_thread(paths_config.get_all_paths)

        return web.json_response({
            "success": True,
            "data": paths_info
        })
    except Exception as e:
        error_msg = f"Get paths status failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/paths/set")
async def set_path_config(request):
    """Set a specific path configuration"""
    try:
        data = await request.json()
        path_type = data.get("type", None)
        path_value = data.get("path", None)

        if not path_type:
            return web.json_response({"success": False, "error": "Missing path type"}, status=400)

        if not path_value:
            return web.json_response({"success": False, "error": "Missing path value"}, status=400)

        # Validate the path
        validation = await asyncio.to_thread(
            paths_config.validate_path,
            path_value,
            should_exist=False,
            create_if_missing=True
        )

        if not validation.get('valid'):
            return web.json_response({
                "success": False,
                "error": f"Invalid path: {validation.get('error')}"
            })

        # Save the path
        success = await asyncio.to_thread(paths_config.set_path, path_type, path_value)

        if success:
            # Update in-memory config immediately
            if path_type == 'thumbnail_cache':
                config.thumbnail_cache_uri = path_value
                # Note: Cache will need to be reinitialized to use new path
            elif path_type == 'output':
                config.output_uri = path_value
            elif path_type == 'workflows':
                config.workflows_uri = path_value
            elif path_type == 'prompts':
                config.prompts_uri = path_value

            return web.json_response({
                "success": True,
                "message": f"{path_type} path updated successfully",
                "data": {
                    "type": path_type,
                    "path": path_value,
                    "validation": validation
                }
            })
        else:
            return web.json_response({
                "success": False,
                "error": "Failed to save path configuration"
            })

    except ValueError as e:
        return web.json_response({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        error_msg = f"Set path failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/paths/reset")
async def reset_paths_config(request):
    """Reset all paths to default values"""
    try:
        success = await asyncio.to_thread(paths_config.reset_to_defaults)

        if success:
            # Reload paths into config
            paths = await asyncio.to_thread(paths_config.load_paths_config)
            config.output_uri = paths['output']
            config.workflows_uri = paths['workflows']
            config.prompts_uri = paths['prompts']
            config.thumbnail_cache_uri = paths['thumbnail_cache']

            return web.json_response({
                "success": True,
                "message": "All paths reset to defaults",
                "data": paths
            })
        else:
            return web.json_response({
                "success": False,
                "error": "Failed to reset paths"
            })

    except Exception as e:
        error_msg = f"Reset paths failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


@routes.post("/image-browsing/paths/validate")
async def validate_path_endpoint(request):
    """Validate a path without saving it"""
    try:
        data = await request.json()
        path_value = data.get("path", None)
        create_if_missing = data.get("create_if_missing", False)

        if not path_value:
            return web.json_response({"success": False, "error": "Missing path value"}, status=400)

        validation = await asyncio.to_thread(
            paths_config.validate_path,
            path_value,
            should_exist=False,
            create_if_missing=create_if_missing
        )

        return web.json_response({
            "success": validation.get('valid', False),
            "data": validation
        })

    except Exception as e:
        error_msg = f"Validate path failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


WEB_DIRECTORY = "web"
NODE_CLASS_MAPPINGS = {}
__all__ = ["NODE_CLASS_MAPPINGS"]
