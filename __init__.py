import os
import folder_paths
import asyncio
from .py import config


config.extension_uri = os.path.dirname(__file__)
config.output_uri = folder_paths.get_output_directory()


from .py import utils

version = utils.get_current_version()
utils.download_web_distribution(version)


from aiohttp import web
from .py import services


routes = config.routes


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
            items = await asyncio.to_thread(services.scan_directory_items, filepath)
            return web.json_response({"success": True, "data": items})

        return web.Response(status=404)
    except Exception as e:
        error_msg = f"Obtain failed: {str(e)}"
        utils.print_error(error_msg)
        return web.json_response({"success": False, "error": error_msg})


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
        services.recursive_delete_files(file_list)
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
        
        services.move_files(file_list, target_folder)
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


WEB_DIRECTORY = "web"
NODE_CLASS_MAPPINGS = {}
__all__ = ["NODE_CLASS_MAPPINGS"]
