import os
import folder_paths
import asyncio
import hashlib
from .py import config


config.extension_uri = os.path.dirname(__file__)
config.output_uri = folder_paths.get_output_directory()

# Get ComfyUI base directory for workflows
comfyui_base = os.path.dirname(folder_paths.get_output_directory())
config.workflows_uri = os.path.join(comfyui_base, "user", "default", "workflows")
config.prompts_uri = os.path.join(comfyui_base, "user", "default", "prompts")

# Create prompts directory if it doesn't exist
if not os.path.exists(config.prompts_uri):
    os.makedirs(config.prompts_uri)


from .py import utils

version = utils.get_current_version()
utils.download_web_distribution(version)


from aiohttp import web
from .py import services


routes = config.routes


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

        if os.path.isfile(filepath):

            preview_type = request.query.get("preview", None)
            if not preview_type:
                return web.FileResponse(filepath)

            if services.assert_file_type(filepath, ["image"]):
                # Get max_size from query params, default to 128
                max_size_str = request.query.get("max_size", "128")
                try:
                    max_size = int(max_size_str)
                except ValueError:
                    max_size = 128
                
                image_data = services.get_image_data(filepath, max_size)
                # Add cache headers - cache for 1 hour in browser
                return web.Response(
                    body=image_data.getvalue(), 
                    content_type="image/webp",
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "ETag": f'"{services.get_cache_key(filepath, max_size)}"'
                    }
                )
            
            if services.assert_file_type(filepath, ["video"]):
                # Get max_size from query params, default to 128
                max_size_str = request.query.get("max_size", "128")
                try:
                    max_size = int(max_size_str)
                except ValueError:
                    max_size = 128
                
                image_data = services.get_image_data(filepath, max_size)
                return web.Response(
                    body=image_data.getvalue(), 
                    content_type="image/webp",
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "ETag": f'"{services.get_cache_key(filepath, max_size)}"'
                    }
                )

        elif os.path.isdir(filepath):
            # Check ETag for conditional request (304 Not Modified)
            etag = get_folder_etag(filepath)
            if check_etag_match(request, etag):
                return web.Response(status=304)
            
            items = await asyncio.to_thread(services.scan_directory_items, filepath)
            return web.json_response(
                {"success": True, "data": items},
                headers={"ETag": etag, "Cache-Control": "private, no-cache"}
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
            return web.FileResponse(filepath)

        elif os.path.isdir(filepath):
            # Check ETag for conditional request (304 Not Modified)
            etag = get_folder_etag(filepath)
            if check_etag_match(request, etag):
                return web.Response(status=304)
            
            items = await asyncio.to_thread(services.scan_workflows_directory, filepath)
            return web.json_response(
                {"success": True, "data": items},
                headers={"ETag": etag, "Cache-Control": "private, no-cache"}
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
            return web.json_response(
                {"success": True, "data": items},
                headers={"ETag": etag, "Cache-Control": "private, no-cache"}
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
        
        return web.json_response({"success": True, "data": results})
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



@routes.post("/image-browsing/cache-all")
async def cache_all_thumbnails(request):
    """Start caching all thumbnails in background"""
    try:
        data = await request.json()
        max_size = data.get("max_size", 128)
        priority_folder = data.get("priority_folder", None)
        
        # Start caching in background
        asyncio.create_task(asyncio.to_thread(services.cache_all_images, max_size, 4, priority_folder))
        
        return web.json_response({"success": True, "message": "Caching started"})
    except Exception as e:
        error_msg = f"Cache failed: {str(e)}"
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


WEB_DIRECTORY = "web"
NODE_CLASS_MAPPINGS = {}
__all__ = ["NODE_CLASS_MAPPINGS"]
