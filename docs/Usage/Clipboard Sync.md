# Clipboard Sync

ScreenConnect supports bidirectional clipboard sync between the agent and viewer.

## Copying from the agent to your machine

1. On the agent's screen, copy something (`Cmd+C` / `Ctrl+C`)
2. In the viewer toolbar, click **Pull Clipboard**
3. The agent's clipboard content is now on your clipboard — paste normally

## Copying from your machine to the agent

1. On your machine, copy something
2. In the viewer toolbar, click **Push Clipboard**
3. The content is now in the agent's clipboard — paste on the agent with `Ctrl+V` or `Cmd+V`

## What gets synced

- Plain text (always supported)
- The clipboard is transferred as UTF-8 text

Images and rich content are not currently synced — only text.

## Technical detail

Clipboard sync uses two protocol messages:

| Message | Direction | Effect |
|---------|-----------|--------|
| `clipboard_request` | viewer → agent | Agent reads its clipboard and sends it back |
| `clipboard_data` | either direction | Receiver writes the payload to its clipboard |

The viewer sends a `clipboard_request` when you click Pull, and sends `clipboard_data` when you click Push.
