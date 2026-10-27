from mcp.server.mcpserver import MCPServer
from tool import search_gmail, get_calendar_events

mcp = MCPServer("company-tools")
mcp.tool()(search_gmail)
mcp.tool()(get_calendar_events)

if __name__ == "__main__":
    mcp.run()