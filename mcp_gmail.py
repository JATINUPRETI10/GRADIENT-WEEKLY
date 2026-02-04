import asyncio
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from googleapiclient.discovery import build
from pypdf import PdfReader
import io
import os
import pickle

# ---------------- CONFIG ----------------
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TOKEN_FILE = r"C:\Users\jatin\OneDrive\Desktop\Gradient Weekly\token.pkl"


server = Server("drive-mcp-server")

_drive = None  # lazy-loaded singleton


def get_drive_service():
    global _drive
    if _drive:
        return _drive

    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("token.pkl not found. Run authorize_drive_once.py first.")

    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)

    _drive = build("drive", "v3", credentials=creds)
    return _drive


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_drive_files",
            description="List files from Google Drive",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="read_drive_file",
            description="Read content of a Drive file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The ID of the file to read",
                    },
                },
                "required": ["file_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "list_drive_files":
        drive = get_drive_service()
        res = drive.files().list(
            pageSize=20,
            fields="files(id, name, mimeType)"
        ).execute()
        
        files = res.get("files", [])
        return [types.TextContent(type="text", text=str(files))]
    
    elif name == "read_drive_file":
        if not arguments or "file_id" not in arguments:
            raise ValueError("file_id is required")
        
        file_id = arguments["file_id"]
        drive = get_drive_service()

        file = drive.files().get(
            fileId=file_id,
            fields="mimeType, name"
        ).execute()

        mime = file["mimeType"]

        # Google Docs
        if mime == "application/vnd.google-apps.document":
            content = drive.files().export(
                fileId=file_id,
                mimeType="text/plain"
            ).execute()
            return [types.TextContent(type="text", text=content.decode("utf-8"))]

        # PDFs
        if mime == "application/pdf":
            pdf_bytes = drive.files().get_media(fileId=file_id).execute()
            reader = PdfReader(io.BytesIO(pdf_bytes))

            text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
            return [types.TextContent(type="text", text=text.strip())]

        # Plain text / JSON
        content = drive.files().get_media(fileId=file_id).execute()
        return [types.TextContent(type="text", text=content.decode("utf-8"))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="drive-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())