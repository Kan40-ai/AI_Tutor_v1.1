# youtube_MCP.py
import re
# from mcp.server.fastmcp import FastMCP
from fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch
import yt_dlp

# 1. Initialize the MCP Server
mcp = FastMCP("YouTube Transcript Server")

def extract_video_id(url: str) -> str:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else url

# 2. TOOLS -- SCENARIO 1
@mcp.tool()
def get_youtube_transcript(video_url: str) -> str:
    """Fetches the full transcript of a YouTube video given its URL."""
    try:
        video_id = extract_video_id(video_url)
        transcript_list = YouTubeTranscriptApi().fetch(video_id).to_raw_data()
        return " ".join([segment['text'] for segment in transcript_list])
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"



# SCENARIO 2 (incl. yt_dlp)
@mcp.tool()
def search_and_summarize_youtube(topic: str) -> str:
    """Searches YouTube using the 2026 yt-dlp build."""
    try:
        print(f"[SEARCH] YouTube for: {topic}")
        
        # Configure yt-dlp for a fast search (1 result, no download)
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # The 'ytsearch1:' prefix tells it to search and grab the first result
            search_result = ydl.extract_info(f"ytsearch1:{topic}", download=False)
            
            if not search_result['entries']:
                return "No videos found for that topic."
            
            top_video = search_result['entries'][0]
            video_url = top_video['url']
            video_title = top_video['title']
            
            print(f"[SUCCESS] Found: {video_title}")
            
            # Now call your fixed transcript function
            transcript = get_youtube_transcript(video_url)
            
            return f"VIDEO_TITLE: {video_title}\nVIDEO_URL: {video_url}\n\nTRANSCRIPT: {transcript}"

    except Exception as e:
        return f"Error during search: {str(e)}"


# 3. Run the server
if __name__ == "__main__":
    mcp.run(transport="stdio")