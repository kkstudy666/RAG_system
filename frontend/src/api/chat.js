import { useAuthStore } from '../stores/auth'

/**
 * 流式问答（SSE）：用原生 fetch 读取 ReadableStream，
 * 按事件类型回调 onToken / onSources / onDone / onError。
 */
export async function streamChat(data, handlers) {
  const auth = useAuthStore()
  const { onToken, onSources, onDone, onError } = handlers

  let resp
  try {
    resp = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify(data),
    })
  } catch (e) {
    onError?.('网络连接失败，请检查网络')
    return
  }

  if (!resp.ok || !resp.body) {
    let detail = '请求失败'
    try {
      detail = (await resp.json()).detail || detail
    } catch (e) {
      /* ignore */
    }
    onError?.(detail)
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE 以空行分隔多帧 data
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''

    for (const frame of frames) {
      const line = frame.trim()
      if (!line.startsWith('data:')) continue
      let payload
      try {
        payload = JSON.parse(line.slice(5).trim())
      } catch (e) {
        continue
      }
      if (payload.type === 'token') onToken?.(payload.content)
      else if (payload.type === 'sources') onSources?.(payload)
      else if (payload.type === 'done') onDone?.(payload)
      else if (payload.type === 'error') onError?.(payload.content)
    }
  }
}
