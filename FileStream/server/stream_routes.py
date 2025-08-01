from aiohttp import web
# ... tus importaciones ya existentes ...

@routes.get("/dl/{path}", allow_head=True)
async def download_stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        response = await media_streamer(request, path)

        # Añadir cabecera CORS para evitar problemas con navegador
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        traceback.print_exc()
        logging.critical(e.with_traceback(None))
        logging.debug(traceback.format_exc())
        raise web.HTTPInternalServerError(text=str(e))


async def media_streamer(request: web.Request, db_id: str):
    range_header = request.headers.get("Range", None)
    
    # Selección cliente más rápido y reutilización objeto ByteStreamer (igual que tienes)
    # ...

    # Rango bytes y validación
    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes >= file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    # resto código igual ...

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",  # <-- Importante CORS
        },
    )
